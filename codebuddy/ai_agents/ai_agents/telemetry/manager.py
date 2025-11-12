"""
TelemetryManager implementation for system orchestration.

This module provides the TelemetryManager class that coordinates telemetry
collection across the entire SOP Agents system. It implements zero-configuration
initialization, session lifecycle management, and graceful shutdown.
"""

import atexit
import logging
import signal
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Any

from .types import TelemetrySession, TaskStatus
from .collector import TelemetryCollector
from .data_store import TelemetryDataStore


logger = logging.getLogger(__name__)


class TelemetryManager:
    """
    Simple telemetry manager for single-session agent execution.

    Features:
    - Zero-configuration initialization with sensible defaults
    - Single session lifecycle management
    - Graceful shutdown with data persistence
    - Thread-safe operations
    """

    _instance: Optional['TelemetryManager'] = None
    _lock = threading.Lock()

    def __new__(cls) -> 'TelemetryManager':
        """Ensure singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the telemetry manager (only called once due to singleton)."""
        # Prevent re-initialization
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        self._initialization_lock = threading.RLock()
        self._shutdown_lock = threading.Lock()
        self._is_shutdown = False

        # Core components - simplified for single session
        self._data_store: Optional[TelemetryDataStore] = None
        self._collector: Optional[TelemetryCollector] = None

        # Configuration
        self._config = self._get_default_config()

        # Single session management
        self._session_id: Optional[str] = None
        self._session_start_time: Optional[datetime] = None

        # Register shutdown handlers
        atexit.register(self.shutdown)
        self._register_signal_handlers()

        logger.debug("TelemetryManager singleton created")

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for the telemetry system."""
        return {
            "enabled": True,
            "storage_dir": None,  # Will use default ~/.cache/ept/sop_agents/
            "max_file_age_days": 30,
            "auto_cleanup": True,
        }

    def _register_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown on interrupts."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.shutdown()
            # Re-raise the signal to allow normal termination
            signal.signal(signum, signal.SIG_DFL)
            signal.raise_signal(signum)

        try:
            # Handle SIGINT (Ctrl+C) and SIGTERM
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            # On Unix systems, also handle SIGHUP
            if hasattr(signal, 'SIGHUP'):
                signal.signal(signal.SIGHUP, signal_handler)

            logger.debug("Signal handlers registered for graceful shutdown")
        except (ValueError, OSError) as e:
            # Signal handling might not be available in all contexts (e.g., threads)
            logger.debug(f"Could not register signal handlers: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error registering signal handlers: {e}")

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the telemetry system with zero-configuration defaults.

        Args:
            config: Optional configuration dictionary to override defaults
        """
        with self._initialization_lock:
            if self._is_shutdown:
                logger.warning("Cannot initialize TelemetryManager after shutdown")
                return

            try:
                # Update configuration if provided
                if config:
                    self._config.update(config)

                # Check if telemetry is disabled
                if not self._config.get("enabled", True):
                    logger.info("Telemetry is disabled by configuration")
                    return

                # Initialize data store
                if self._data_store is None:
                    self._data_store = TelemetryDataStore(
                        storage_dir=self._config.get("storage_dir"),
                        max_file_age_days=self._config.get("max_file_age_days", 30),
                    )
                    logger.debug("TelemetryDataStore initialized")

                # Initialize single session
                if self._session_id is None:
                    self._session_id = str(uuid.uuid4())
                    self._session_start_time = datetime.now(timezone.utc)
                    logger.info(f"Telemetry session started: {self._session_id}")

                # Perform initial cleanup if enabled
                if self._config.get("auto_cleanup", True) and self._data_store:
                    try:
                        cleaned_count = self._data_store.cleanup_old_files()
                        if cleaned_count > 0:
                            logger.info(f"Cleaned up {cleaned_count} old telemetry files")
                    except Exception as e:
                        logger.error(f"Failed to perform initial cleanup: {e}")

                logger.info("TelemetryManager initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize TelemetryManager: {e}")
                # Continue without telemetry rather than failing



    def get_collector(self, session_id: Optional[str] = None) -> TelemetryCollector:
        """
        Get the telemetry collector for data collection.

        Args:
            session_id: Optional session ID (ignored in single-session mode)

        Returns:
            TelemetryCollector instance
        """
        # Ensure initialization
        if self._data_store is None:
            self.initialize()

        # Check if telemetry is disabled
        if not self._config.get("enabled", True):
            # Return a no-op collector that doesn't actually collect data
            return self._create_noop_collector()

        # Thread-safe collector creation
        with self._initialization_lock:
            # Return existing collector or create new one
            if self._collector is None:
                try:
                    self._collector = TelemetryCollector(session_id=self._session_id)
                    logger.debug(f"Created TelemetryCollector for session: {self._session_id}")
                except Exception as e:
                    logger.error(f"Failed to create TelemetryCollector: {e}")
                    return self._create_noop_collector()

            return self._collector

    def _create_noop_collector(self) -> TelemetryCollector:
        """Create a no-op collector that doesn't actually collect data."""
        # For now, return a regular collector but we could implement a NoOpCollector
        # that overrides all methods to do nothing
        try:
            return TelemetryCollector(session_id="noop")
        except Exception:
            # If even creating a basic collector fails, we need a true no-op
            # This would require implementing a NoOpTelemetryCollector class
            # For now, we'll return None and handle it gracefully in calling code
            logger.error("Failed to create even a basic collector")
            raise

    def flush_data(self) -> None:
        """Manually flush telemetry data to persistent storage."""
        try:
            if not self._config.get("enabled", True) or self._data_store is None or self._collector is None:
                return

            # Get session data from collector
            session_data = self._collector.get_session_data()
            if session_data and session_data.tasks:  # Only flush if there's actual data
                self._data_store.store_session_data(session_data.session_id, session_data)
                self._data_store.flush_to_disk()
                logger.debug(f"Flushed session {session_data.session_id} to disk")
        except Exception as e:
            logger.error(f"Failed to flush telemetry data: {e}")

    def force_flush_all_data(self) -> None:
        """Force flush all telemetry data immediately, even incomplete sessions."""
        try:
            if not self._config.get("enabled", True):
                return

            logger.info("Force flushing all telemetry data...")

            # Flush current collector data if available
            if self._collector:
                try:
                    session_data = self._collector.get_session_data()
                    if session_data:
                        # Mark session as interrupted if it has active tasks
                        if session_data.tasks:
                            for task in session_data.tasks:
                                if task.status == TaskStatus.IN_PROGRESS:
                                    task.status = TaskStatus.INTERRUPTED
                                    task.end_time = datetime.now(timezone.utc)
                                    task.error_message = "Session interrupted"

                        # Store the session data
                        if self._data_store:
                            self._data_store.store_session_data(session_data.session_id, session_data)
                            logger.info(f"Force flushed session {session_data.session_id}")
                except Exception as e:
                    logger.error(f"Failed to force flush collector data: {e}")

            # Force flush data store
            if self._data_store:
                try:
                    self._data_store.flush_to_disk()
                    logger.info("Force flushed data store to disk")
                except Exception as e:
                    logger.error(f"Failed to force flush data store: {e}")

        except Exception as e:
            logger.error(f"Failed to force flush all data: {e}")

    def get_session_data(self, session_id: Optional[str] = None) -> Optional[TelemetrySession]:
        """
        Get session data for the current session.

        Args:
            session_id: Session ID to retrieve (ignored in single-session mode)

        Returns:
            TelemetrySession object if found, None otherwise
        """
        try:
            if not self._config.get("enabled", True):
                return None

            # Get from active collector if available
            if self._collector:
                return self._collector.get_session_data()

            # Try data store if collector not available
            if self._data_store and self._session_id:
                return self._data_store.get_session_data(self._session_id)

            return None
        except Exception as e:
            logger.error(f"Failed to get session data: {e}")
            return None

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get statistics about the telemetry storage system."""
        try:
            if not self._config.get("enabled", True) or self._data_store is None:
                return {"enabled": False}

            stats = self._data_store.get_storage_stats()
            stats.update({
                "enabled": True,
                "current_session_id": self._session_id,
                "has_active_collector": self._collector is not None,
                "config": self._config.copy(),
            })

            return stats
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {"error": str(e)}

    def cleanup_old_data(self, max_age_days: Optional[int] = None) -> int:
        """
        Clean up old telemetry data.

        Args:
            max_age_days: Maximum age of data in days. Uses config default if None.

        Returns:
            Number of files cleaned up
        """
        try:
            if not self._config.get("enabled", True) or self._data_store is None:
                return 0

            return self._data_store.cleanup_old_files(max_age_days)
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return 0

    def finalize_current_session(self) -> Optional[TelemetrySession]:
        """
        Finalize the current session and return the complete data.

        Returns:
            Complete TelemetrySession object for the current session
        """
        try:
            if self._collector is None:
                return None

            session = self._collector.finalize_session()

            # Store the finalized session
            if self._data_store:
                self._data_store.store_session_data(session.session_id, session)
                self._data_store.flush_to_disk()

            logger.info(f"Finalized session: {self._session_id}")
            return session
        except Exception as e:
            logger.error(f"Failed to finalize current session: {e}")
            return None

    def start_new_session(self) -> str:
        """
        Start a new telemetry session (resets current session).

        Returns:
            New session ID
        """
        try:
            # Finalize current session if exists
            if self._collector:
                self.finalize_current_session()

            # Start new session
            self._session_id = str(uuid.uuid4())
            self._session_start_time = datetime.now(timezone.utc)
            self._collector = None  # Will be created on first get_collector() call

            logger.info(f"Started new telemetry session: {self._session_id}")
            return self._session_id
        except Exception as e:
            logger.error(f"Failed to start new session: {e}")
            # Return a fallback session ID
            return str(uuid.uuid4())

    def is_enabled(self) -> bool:
        """Check if telemetry is enabled."""
        return self._config.get("enabled", True)

    def has_unsaved_data(self) -> bool:
        """Check if there's unsaved telemetry data that needs flushing."""
        try:
            if not self._config.get("enabled", True) or self._collector is None:
                return False

            session_data = self._collector.get_session_data()
            return session_data is not None and len(session_data.tasks) > 0
        except Exception as e:
            logger.error(f"Failed to check for unsaved data: {e}")
            return False

    def disable_telemetry(self) -> None:
        """Disable telemetry collection."""
        self._config["enabled"] = False
        logger.info("Telemetry disabled")

    def enable_telemetry(self) -> None:
        """Enable telemetry collection."""
        self._config["enabled"] = True
        # Re-initialize if needed
        if self._data_store is None:
            self.initialize()
        logger.info("Telemetry enabled")

    def shutdown(self) -> None:
        """Gracefully shutdown the telemetry manager with data persistence."""
        with self._shutdown_lock:
            if self._is_shutdown:
                return

            self._is_shutdown = True

            try:
                logger.info("Shutting down TelemetryManager...")

                # Force flush all data first (handles interrupted sessions)
                self.force_flush_all_data()

                # Try to finalize current session normally if possible
                try:
                    self.finalize_current_session()
                except Exception as e:
                    logger.warning(f"Could not finalize session normally during shutdown: {e}")

                # Final data store shutdown and cleanup
                if self._data_store:
                    self._data_store.shutdown()

                logger.info("TelemetryManager shutdown complete")
            except Exception as e:
                logger.error(f"Error during TelemetryManager shutdown: {e}")
                # Even if shutdown fails, try to flush critical data
                try:
                    if self._data_store:
                        self._data_store.flush_to_disk()
                except Exception as flush_error:
                    logger.error(f"Failed final emergency flush: {flush_error}")

    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic shutdown."""
        # If we're exiting due to an exception (like KeyboardInterrupt),
        # make sure to force flush data
        if exc_type is not None:
            logger.info(f"Exiting context manager due to {exc_type.__name__}")
            self.force_flush_all_data()

        self.shutdown()

    @classmethod
    def get_instance(cls) -> 'TelemetryManager':
        """Get the singleton instance of TelemetryManager."""
        return cls()

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (primarily for testing)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.shutdown()
                cls._instance = None
