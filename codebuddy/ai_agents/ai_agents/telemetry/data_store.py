"""
TelemetryDataStore implementation for persistent storage of telemetry data.

This module provides memory buffering and file-based storage with concurrent
access safety, automatic directory creation, and file rotation capabilities.
"""

import os
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Any, Union
import fcntl
import tempfile
import shutil
import logging

from ai_agents.core.runtime import runtime
from .types import TelemetrySession
from .error_handler import (
    safe_storage_operation,
    safe_telemetry_call,
    with_fallback_data,
    get_error_handler,
)
from .remote_sender import send_session_to_remote


logger = logging.getLogger(__name__)


class TelemetryDataStore:
    """
    Handles telemetry data persistence with file-based storage.

    Features:
    - Simple file-based storage for single session
    - Concurrent access safety with file locking
    - Automatic directory creation
    - File cleanup
    - Graceful error handling
    """

    def __init__(
        self,
        storage_dir: Optional[Union[str, Path]] = None,
        max_file_age_days: int = 30,
    ):
        """
        Initialize the telemetry data store.

        Args:
            storage_dir: Directory for storing telemetry files. Defaults to ~/.cache/ept/sop_agents/
            max_file_age_days: Maximum age of files before cleanup
        """
        self.storage_dir = self._get_storage_dir(storage_dir)
        self.max_file_age_days = max_file_age_days

        # Current session data (in-memory for performance)
        self._current_session: Optional[TelemetrySession] = None
        self._session_lock = threading.RLock()

        # Auto-flush mechanism
        self._auto_flush_timer: Optional[threading.Timer] = None
        self._auto_flush_interval = 60  # Flush every 60 seconds
        self._shutdown_requested = False

        # Initialize storage directory
        self._ensure_storage_directory()

        # Start auto-flush timer
        self._start_auto_flush()

        logger.debug(f"TelemetryDataStore initialized with storage_dir: {self.storage_dir}")

    def _get_storage_dir(self, storage_dir: Optional[Union[str, Path]]) -> Path:
        """Get the storage directory, using default if not provided."""
        if storage_dir:
            return Path(storage_dir)

        # Default to ~/.cache/ept/sop_agents/${runtime.app}
        home = Path.home()
        base_path = home / ".cache" / "ept" / "sop_agents"

        # Add runtime app if available
        if runtime.app:
            return base_path / runtime.app
        else:
            return base_path

    @safe_storage_operation("directory_creation")
    def _ensure_storage_directory(self) -> None:
        """Ensure the storage directory exists with proper permissions."""
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            # Set restrictive permissions (owner read/write/execute only)
            os.chmod(self.storage_dir, 0o700)
            logger.debug(f"Storage directory ensured: {self.storage_dir}")
        except (PermissionError, OSError) as e:
            # Fall back to temp directory
            get_error_handler().handle_storage_error(e, "directory_creation")
            try:
                self.storage_dir = Path(tempfile.gettempdir()) / "ept_telemetry"
                self.storage_dir.mkdir(parents=True, exist_ok=True)
                logger.warning(f"Using fallback storage directory: {self.storage_dir}")
            except Exception as fallback_error:
                get_error_handler().handle_storage_error(fallback_error, "fallback_directory")
                # Use a minimal temp directory as last resort
                self.storage_dir = Path(tempfile.mkdtemp(prefix="ept_telemetry_"))

    @safe_telemetry_call("store_session_data")
    def store_session_data(self, session_id: str, session: TelemetrySession) -> None:
        """
        Store session data in memory.

        Args:
            session_id: Unique identifier for the session
            session: TelemetrySession object to store
        """
        # Validate input
        if session is None:
            logger.warning(f"Attempted to store None session for {session_id}")
            return

        with self._session_lock:
            self._current_session = session

        logger.debug(f"Session {session_id} stored in memory")

    @with_fallback_data(None)
    def get_session_data(self, session_id: str) -> Optional[TelemetrySession]:
        """
        Retrieve session data from memory or disk.

        Args:
            session_id: Unique identifier for the session

        Returns:
            TelemetrySession object if found, None otherwise
        """
        # First check current session in memory
        with self._session_lock:
            if self._current_session and self._current_session.session_id == session_id:
                return self._current_session

        # Then check disk
        return self._load_session_from_disk(session_id)

    def flush_to_disk(self) -> None:
        """Manually flush current session data to disk."""
        try:
            with self._session_lock:
                if self._current_session:
                    self._save_session_to_disk(self._current_session.session_id, self._current_session)
                    logger.debug("Manual flush to disk completed")

                    # Send to remote service if requested and session is complete
                    if self._current_session.end_time:
                        self._send_to_remote_service(self._current_session)
        except Exception as e:
            logger.error(f"Failed to flush data to disk: {e}")

    def _start_auto_flush(self) -> None:
        """Start the auto-flush timer."""
        if self._shutdown_requested:
            return

        try:
            self._auto_flush_timer = threading.Timer(self._auto_flush_interval, self._auto_flush_callback)
            self._auto_flush_timer.daemon = True
            self._auto_flush_timer.start()
            logger.debug(f"Auto-flush timer started (interval: {self._auto_flush_interval}s)")
        except Exception as e:
            logger.error(f"Failed to start auto-flush timer: {e}")

    def _auto_flush_callback(self) -> None:
        """Callback for auto-flush timer."""
        try:
            if not self._shutdown_requested:
                self.flush_to_disk()
                # Schedule next flush
                self._start_auto_flush()
        except Exception as e:
            logger.error(f"Auto-flush callback failed: {e}")
            # Try to restart the timer even if flush failed
            if not self._shutdown_requested:
                self._start_auto_flush()

    def _stop_auto_flush(self) -> None:
        """Stop the auto-flush timer."""
        self._shutdown_requested = True
        if self._auto_flush_timer:
            try:
                self._auto_flush_timer.cancel()
                logger.debug("Auto-flush timer stopped")
            except Exception as e:
                logger.error(f"Failed to stop auto-flush timer: {e}")

    def _save_session_to_disk(self, session_id: str, session: TelemetrySession) -> None:
        """Save a session to disk with file locking."""
        file_path = self._get_session_file_path(session_id)
        temp_path = file_path.with_suffix('.tmp')

        try:
            # Write to temporary file first
            with open(temp_path, 'w', encoding='utf-8') as f:
                # Acquire exclusive lock
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                f.write(session.to_json())
                f.flush()
                os.fsync(f.fileno())

            # Atomically move to final location
            shutil.move(str(temp_path), str(file_path))

            # Set restrictive permissions
            os.chmod(file_path, 0o600)

            logger.debug(f"Session {session_id} saved to {file_path}")
        except Exception as e:
            # Clean up temp file if it exists
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except (OSError, PermissionError):
                    pass
            raise e

    def _load_session_from_disk(self, session_id: str) -> Optional[TelemetrySession]:
        """Load a session from disk with file locking."""
        file_path = self._get_session_file_path(session_id)

        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Acquire shared lock
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                content = f.read()

            return TelemetrySession.from_json(content)
        except Exception as e:
            logger.error(f"Failed to load session {session_id} from disk: {e}")
            return None

    def _get_session_file_path(self, session_id: str) -> Path:
        """Get the file path for a session."""
        # Add date prefix (yyyy_mm_dd) to filename
        date_prefix = datetime.now().strftime("%Y_%m_%d")
        filename = f"{date_prefix}_{session_id}.json"
        return self.storage_dir / filename

    def get_storage_path(self) -> Path:
        """Get the storage directory path."""
        return self.storage_dir

    def cleanup_old_files(self, max_age_days: Optional[int] = None) -> int:
        """
        Clean up old telemetry files.

        Args:
            max_age_days: Maximum age of files in days. Uses instance default if None.

        Returns:
            Number of files cleaned up
        """
        if max_age_days is None:
            max_age_days = self.max_file_age_days

        cutoff_time = datetime.now() - timedelta(days=max_age_days)
        cleaned_count = 0

        try:
            for file_path in self.storage_dir.glob("*.json"):
                try:
                    # Check file modification time
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime < cutoff_time:
                        file_path.unlink()
                        cleaned_count += 1
                        logger.debug(f"Cleaned up old file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to clean up file {file_path}: {e}")

            logger.info(f"Cleaned up {cleaned_count} old telemetry files")
        except Exception as e:
            logger.error(f"Failed to cleanup old files: {e}")

        return cleaned_count

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get statistics about the storage system."""
        try:
            stats = {
                "storage_dir": str(self.storage_dir),
                "has_current_session": self._current_session is not None,
                "disk_files": 0,
                "total_disk_size_mb": 0.0,
                "oldest_file": None,
                "newest_file": None,
            }

            # Analyze disk files
            disk_files = list(self.storage_dir.glob("*.json"))
            stats["disk_files"] = len(disk_files)

            if disk_files:
                total_size = sum(f.stat().st_size for f in disk_files)
                stats["total_disk_size_mb"] = total_size / (1024 * 1024)

                # Find oldest and newest files
                oldest = min(disk_files, key=lambda f: f.stat().st_mtime)
                newest = max(disk_files, key=lambda f: f.stat().st_mtime)

                stats["oldest_file"] = {
                    "name": oldest.name,
                    "mtime": datetime.fromtimestamp(oldest.stat().st_mtime).isoformat(),
                }
                stats["newest_file"] = {
                    "name": newest.name,
                    "mtime": datetime.fromtimestamp(newest.stat().st_mtime).isoformat(),
                }

            return stats
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {"error": str(e)}

    def shutdown(self) -> None:
        """Gracefully shutdown the data store, flushing all data."""
        try:
            logger.info("Shutting down TelemetryDataStore...")

            # Stop auto-flush timer first
            self._stop_auto_flush()

            # Flush current session data
            self.flush_to_disk()

            # Clean up old files
            self.cleanup_old_files()

            logger.info("TelemetryDataStore shutdown complete")
        except Exception as e:
            logger.error(f"Error during TelemetryDataStore shutdown: {e}")
            # Ensure auto-flush is stopped even if other operations fail
            self._stop_auto_flush()

    @safe_telemetry_call("send_to_remote")
    def _send_to_remote_service(self, session: TelemetrySession) -> None:
        """
        Send session data to remote telemetry service.

        Args:
            session: TelemetrySession to send
        """
        try:
            success = send_session_to_remote(session)
            if success:
                logger.info(f"Initiated remote sending for session {session.session_id}")
            else:
                logger.debug(f"Remote sending not available for session {session.session_id}")
        except Exception as e:
            logger.error(f"Error sending session to remote service: {e}")
            get_error_handler().handle_collection_error(e, "send_to_remote")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic shutdown."""
        self.shutdown()
