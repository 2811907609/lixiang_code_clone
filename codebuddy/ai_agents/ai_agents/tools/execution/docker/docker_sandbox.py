"""Docker sandbox with simple tool interface for AI agents."""

import logging
from typing import List, Optional, Dict, Any

from ..base.sandbox_environment import SandboxEnvironment
from .docker_config import DockerConfig, get_predefined_config, default_image
from .persistent_container import PersistentDockerContainer
from .security_policies import get_security_policy


class DockerSandbox(SandboxEnvironment):
    """
    Docker sandbox that provides simple tools for AI agents.

    Initialize once with configuration, then use tools() to get tools.
    """

    def __init__(
        self,
        session_id: str,
        docker_image: str = default_image,
        predefined_config: Optional[str] = None,
        config_file: Optional[str] = None,
        memory_limit: str = "512m",
        cpu_limit: str = "1.0",
        allow_network: bool = False,
        mount_volumes: Optional[Dict[str, str]] = None,
        environment_vars: Optional[Dict[str, str]] = None,
        working_directory: str = "/workspace",
        security_policy: str = "strict",
        auto_start: bool = True,
        auto_pull_image: bool = True
    ):
        """
        Initialize Docker sandbox.

        Args:
            session_id: Unique identifier for this sandbox session
            docker_image: Docker image to use (default: "ubuntu:22.04")
            predefined_config: Use predefined config ("ubuntu", "python", "node", "alpine")
            config_file: Path to YAML configuration file
            memory_limit: Memory limit (e.g., "512m", "1g")
            cpu_limit: CPU limit (e.g., "1.0", "0.5")
            allow_network: Enable network access in container
            mount_volumes: Dictionary of host_path:container_path mappings
            environment_vars: Environment variables to set in container
            working_directory: Working directory in container
            security_policy: Security policy ("strict", "development", "permissive", "readonly")
            auto_start: Automatically start container on initialization
            auto_pull_image: Automatically pull image if not available
        """
        self._session_id = session_id
        self.logger = logging.getLogger(__name__)
        self._is_started = False

        # Build configuration
        self.config = self._build_config(
            docker_image=docker_image,
            config_file=config_file,
            predefined_config=predefined_config,
            memory_limit=memory_limit,
            cpu_limit=cpu_limit,
            allow_network=allow_network,
            mount_volumes=mount_volumes or {},
            environment_vars=environment_vars or {},
            working_directory=working_directory
        )

        # Create security policy
        self.security_policy = get_security_policy(security_policy)

        # Create container manager
        self.container = PersistentDockerContainer(
            self.config,
            container_name=f"sandbox-{session_id}"
        )

        # Auto-pull image if needed
        if auto_pull_image:
            if not self.container.pull_image():
                raise RuntimeError(f"Failed to pull Docker image: {self.config.image}")

        # Auto-start if requested
        if auto_start:
            self.start()

    def _build_config(
        self,
        docker_image: str,
        config_file: Optional[str],
        predefined_config: Optional[str],
        memory_limit: str,
        cpu_limit: str,
        allow_network: bool,
        mount_volumes: Dict[str, str],
        environment_vars: Dict[str, str],
        working_directory: str
    ) -> DockerConfig:
        """Build Docker configuration from various sources."""

        # Priority: config_file > predefined_config > individual parameters
        if config_file:
            config = DockerConfig.from_yaml(config_file)
        elif predefined_config:
            config = get_predefined_config(predefined_config)
        else:
            config = DockerConfig(image=docker_image)

        # Override with individual parameters
        config.memory_limit = memory_limit
        config.cpu_limit = cpu_limit
        config.working_dir = working_directory

        # Network settings
        if allow_network:
            config.network_mode = "bridge"

        # Merge volumes and environment
        config.volumes.update(mount_volumes)
        config.environment.update(environment_vars)

        return config

    def start(self) -> None:
        """Start the sandbox container."""
        if self._is_started:
            return

        self.container.start()
        self._is_started = True
        self.logger.info(f"Sandbox '{self._session_id}' started")

    def stop(self) -> None:
        """Stop and clean up the sandbox container."""
        if not self._is_started:
            return

        self.container.stop()
        self._is_started = False
        self.logger.info(f"Sandbox '{self._session_id}' stopped")

    def tools(self) -> List[Any]:
        """
        Get list of tools for AI agents.

        Returns:
            List of tool functions that can be used by AI agents
        """
        def execute_command(command: str) -> str:
            """
            Execute a shell command in the sandbox.

            Args:
                command: The shell command to execute

            Returns:
                Command output and execution status
            """
            if not self._is_started:
                return "Error: Sandbox is not started"

            try:
                # Validate command
                self.security_policy.validate_command(command)

                # Execute command
                exit_code, stdout, stderr = self.container.execute_command(command)

                # Format result
                result_lines = [
                    f"Command: {command}",
                    f"Exit Code: {exit_code}",
                    f"Status: {'SUCCESS' if exit_code == 0 else 'FAILED'}"
                ]

                if stdout:
                    result_lines.extend(["", "=== OUTPUT ===", stdout.rstrip()])

                if stderr:
                    result_lines.extend(["", "=== ERRORS ===", stderr.rstrip()])

                if not stdout and not stderr:
                    result_lines.append("(No output)")

                return "\n".join(result_lines)

            except ValueError as e:
                return f"Command blocked by security policy: {e}"
            except Exception as e:
                return f"Execution error: {e}"

        return [execute_command]

    @property
    def session_id(self) -> str:
        """Get the session ID."""
        return self._session_id

    @property
    def is_started(self) -> bool:
        """Check if the sandbox is started."""
        return self._is_started

    def get_security_info(self) -> dict:
        """Get security configuration information."""
        return {
            "security_policy": type(self.security_policy).__name__,
            "allow_dangerous": getattr(self.security_policy, 'allow_dangerous', False),
            "enable_network_commands": getattr(self.security_policy, 'enable_network_commands', False),
            "network_mode": self.config.network_mode,
            "read_only": self.config.read_only,
            "user": self.config.user,
            "security_opts": self.config.security_opts,
            "cap_drop": self.config.cap_drop,
            "cap_add": self.config.cap_add
        }

    def get_resource_info(self) -> dict:
        """Get resource configuration and usage information."""
        return {
            "memory_limit": self.config.memory_limit,
            "cpu_limit": self.config.cpu_limit,
            "timeout_seconds": self.config.timeout_seconds,
            "working_dir": self.config.working_dir,
            "docker_image": self.config.image,
            "container_id": self.container.container_id[:12] if self.container.container_id else None,
            "container_name": self.container.container_name,
            "volumes": self.config.volumes,
            "environment": self.config.environment
        }

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.stop()
        except Exception as _:
            pass
