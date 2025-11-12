"""Docker container management for sandboxed execution."""

import logging
import subprocess
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from .docker_config import DockerConfig


class DockerContainer:
    """Manages Docker container lifecycle and command execution."""

    def __init__(self, config: DockerConfig):
        self.config = config
        self.container_id: Optional[str] = None
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

    def _build_docker_command(self, command: str) -> List[str]:
        """Build the complete Docker run command."""
        docker_cmd = ["docker", "run"]

        # Basic settings
        if self.config.auto_remove:
            docker_cmd.append("--rm")

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

        # Command to execute
        docker_cmd.extend(["sh", "-c", command])

        return docker_cmd

    def execute_command(self, command: str) -> Tuple[int, str, str]:
        """
        Execute a command in the Docker container.

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        self.logger.info(f"Executing command in container: {command}")

        # Build Docker command
        docker_cmd = self._build_docker_command(command)

        self.logger.debug(f"Docker command: {' '.join(docker_cmd)}")

        try:
            # Execute the command
            result = subprocess.run(
                docker_cmd,
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
            # Try to clean up any running containers
            self._cleanup_containers()
            raise TimeoutError(f"Command timed out after {self.config.timeout_seconds} seconds") from e

        except Exception as e:
            self.logger.error(f"Error executing command: {e}")
            self._cleanup_containers()
            raise RuntimeError(f"Failed to execute command: {e}") from e

    def _cleanup_containers(self) -> None:
        """Clean up any running containers from this image."""
        try:
            # Find containers running our image
            result = subprocess.run(
                ["docker", "ps", "-q", "--filter", f"ancestor={self.config.image}"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                container_ids = result.stdout.strip().split('\n')
                for container_id in container_ids:
                    if container_id:
                        subprocess.run(
                            ["docker", "kill", container_id],
                            capture_output=True,
                            timeout=10
                        )
                        self.logger.info(f"Killed container: {container_id}")

        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")

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

    def get_image_info(self) -> Dict:
        """Get information about the Docker image."""
        try:
            result = subprocess.run(
                ["docker", "image", "inspect", self.config.image],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return json.loads(result.stdout)[0]
            else:
                return {}

        except Exception as e:
            self.logger.warning(f"Error getting image info: {e}")
            return {}
