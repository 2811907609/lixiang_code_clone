"""Persistent Docker container management for sandboxed execution."""

import logging
import subprocess
import json
import time
import uuid
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from .docker_config import DockerConfig


class PersistentDockerContainer:
    """Manages a long-running Docker container for persistent sandboxed execution."""

    def __init__(self, config: DockerConfig, container_name: Optional[str] = None):
        self.config = config
        self.container_name = container_name or f"sandbox-{uuid.uuid4().hex[:8]}"
        self.container_id: Optional[str] = None
        self.is_running = False
        self.logger = logging.getLogger(__name__)

        # Validate Docker is available
        self._check_docker_available()

        # Validate configuration
        self.config.validate()

    def _check_docker_available(self) -> None:
        """Check if Docker is available and running."""
        try:
            result = subprocess.run(
                ["docker", "version", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError("Docker is not running or not accessible")
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            raise RuntimeError(f"Docker is not available: {e}") from e

    def _build_docker_run_command(self) -> List[str]:
        """Build the Docker run command for starting the persistent container."""
        docker_cmd = ["docker", "run", "-d"]  # Detached mode

        # Container name
        docker_cmd.extend(["--name", self.container_name])

        # Basic settings
        docker_cmd.extend(["-i", "--init"])  # Interactive, with init process

        # Resource limits
        if self.config.memory_limit:
            docker_cmd.extend(["-m", self.config.memory_limit])

        if self.config.cpu_limit:
            docker_cmd.extend(["--cpus", self.config.cpu_limit])

        # Security settings
        docker_cmd.extend(["--network", self.config.network_mode])

        if self.config.read_only:
            docker_cmd.append("--read-only")

        if self.config.user:
            docker_cmd.extend(["-u", self.config.user])

        # Security options
        for opt in self.config.security_opts:
            docker_cmd.extend(["--security-opt", opt])

        # Capabilities
        for cap in self.config.cap_drop:
            docker_cmd.extend(["--cap-drop", cap])

        for cap in self.config.cap_add:
            docker_cmd.extend(["--cap-add", cap])

        # Tmpfs mounts
        for mount_point, options in self.config.tmpfs.items():
            docker_cmd.extend(["--tmpfs", f"{mount_point}:{options}"])

        # Volumes
        for host_path, container_path in self.config.volumes.items():
            # Ensure host path exists
            Path(host_path).mkdir(parents=True, exist_ok=True)
            docker_cmd.extend(["-v", f"{host_path}:{container_path}:ro"])

        # Environment variables
        for key, value in self.config.environment.items():
            docker_cmd.extend(["-e", f"{key}={value}"])

        # Working directory
        docker_cmd.extend(["-w", self.config.working_dir])

        # Image
        docker_cmd.append(self.config.image)

        # Keep container running with a long-running process
        docker_cmd.extend(["sleep", "infinity"])

        return docker_cmd

    def start(self) -> None:
        """Start the persistent container."""
        if self.is_running:
            self.logger.warning(f"Container {self.container_name} is already running")
            return

        self.logger.info(f"Starting persistent container: {self.container_name}")

        # Clean up any existing container with the same name
        self._cleanup_existing_container()

        # Build and execute Docker run command
        docker_cmd = self._build_docker_run_command()

        self.logger.debug(f"Docker command: {' '.join(docker_cmd)}")

        try:
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=60  # Container startup timeout
            )

            if result.returncode != 0:
                raise RuntimeError(f"Failed to start container: {result.stderr}")

            self.container_id = result.stdout.strip()
            self.is_running = True

            # Wait a moment for container to be fully ready
            time.sleep(1)

            # Verify container is running
            if not self._is_container_running():
                raise RuntimeError("Container started but is not running")

            self.logger.info(f"Container started successfully: {self.container_id[:12]}")

        except subprocess.TimeoutExpired as e:
            self.logger.error("Container startup timed out")
            self._cleanup_existing_container()
            raise RuntimeError("Container startup timed out") from e

        except Exception as e:
            self.logger.error(f"Error starting container: {e}")
            self._cleanup_existing_container()
            raise RuntimeError(f"Failed to start container: {e}") from e

    def execute_command(self, command: str) -> Tuple[int, str, str]:
        """
        Execute a command in the running container.

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        if not self.is_running or not self.container_id:
            raise RuntimeError("Container is not running. Call start() first.")

        # Verify container is still running
        if not self._is_container_running():
            self.is_running = False
            raise RuntimeError("Container has stopped unexpectedly")

        self.logger.info(f"Executing command in container {self.container_id[:12]}: {command}")

        # Build docker exec command
        exec_cmd = [
            "docker", "exec", "-i",
            "-w", self.config.working_dir,
            self.container_id,
            "sh", "-c", command
        ]

        self.logger.debug(f"Exec command: {' '.join(exec_cmd)}")

        try:
            result = subprocess.run(
                exec_cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds
            )

            stdout = result.stdout or ""
            stderr = result.stderr or ""
            exit_code = result.returncode

            self.logger.info(f"Command completed with exit code: {exit_code}")

            return exit_code, stdout, stderr

        except subprocess.TimeoutExpired as e:
            self.logger.error(f"Command timed out after {self.config.timeout_seconds} seconds")
            raise TimeoutError(f"Command timed out after {self.config.timeout_seconds} seconds") from e

        except Exception as e:
            self.logger.error(f"Error executing command: {e}")
            raise RuntimeError(f"Failed to execute command: {e}") from e

    def stop(self) -> None:
        """Stop and remove the container."""
        if not self.is_running:
            self.logger.warning("Container is not running")
            return

        self.logger.info(f"Stopping container: {self.container_name}")

        try:
            # Stop the container
            subprocess.run(
                ["docker", "stop", self.container_name],
                capture_output=True,
                text=True,
                timeout=30
            )

            # Remove the container
            subprocess.run(
                ["docker", "rm", self.container_name],
                capture_output=True,
                text=True,
                timeout=10
            )

            self.container_id = None
            self.is_running = False

            self.logger.info(f"Container stopped and removed: {self.container_name}")

        except Exception as e:
            self.logger.error(f"Error stopping container: {e}")
            # Force cleanup
            self._cleanup_existing_container()

    def _is_container_running(self) -> bool:
        """Check if the container is currently running."""
        if not self.container_id:
            return False

        try:
            result = subprocess.run(
                ["docker", "inspect", self.container_id, "--format", "{{.State.Running}}"],
                capture_output=True,
                text=True,
                timeout=10
            )

            return result.returncode == 0 and result.stdout.strip() == "true"

        except Exception:
            return False

    def _cleanup_existing_container(self) -> None:
        """Clean up any existing container with the same name."""
        try:
            # Stop container if running
            subprocess.run(
                ["docker", "stop", self.container_name],
                capture_output=True,
                timeout=10
            )

            # Remove container
            subprocess.run(
                ["docker", "rm", self.container_name],
                capture_output=True,
                timeout=10
            )

        except Exception:
            # Ignore errors during cleanup
            pass

    def get_container_info(self) -> Dict:
        """Get information about the running container."""
        if not self.container_id:
            return {}

        try:
            result = subprocess.run(
                ["docker", "inspect", self.container_id],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return json.loads(result.stdout)[0]
            else:
                return {}

        except Exception as e:
            self.logger.warning(f"Error getting container info: {e}")
            return {}

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

    def pull_image(self) -> bool:
        """
        Pull the Docker image if it doesn't exist locally.

        Returns:
            True if image is available, False otherwise
        """
        try:
            # Check if image exists locally
            result = subprocess.run(
                ["docker", "image", "inspect", self.config.image],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                self.logger.debug(f"Image {self.config.image} already exists locally")
                return True

            # Pull the image
            self.logger.info(f"Pulling Docker image: {self.config.image}")
            result = subprocess.run(
                ["docker", "pull", self.config.image],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes for image pull
            )

            if result.returncode == 0:
                self.logger.info(f"Successfully pulled image: {self.config.image}")
                return True
            else:
                self.logger.error(f"Failed to pull image {self.config.image}: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout pulling image: {self.config.image}")
            return False
        except Exception as e:
            self.logger.error(f"Error pulling image {self.config.image}: {e}")
            return False
