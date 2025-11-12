"""Abstract base class for sandbox execution environments."""

from abc import abstractmethod
from .execution_environment import ExecutionEnvironment


class SandboxEnvironment(ExecutionEnvironment):
    """
    Abstract base class for sandboxed execution environments.

    This extends ExecutionEnvironment with sandbox-specific functionality
    like security policies, resource limits, and isolation features.
    """

    @property
    @abstractmethod
    def session_id(self) -> str:
        """
        Get the unique session identifier for this sandbox.

        Returns:
            Session ID string
        """
        pass

    @abstractmethod
    def get_security_info(self) -> dict:
        """
        Get information about the security configuration.

        Returns:
            Dictionary containing security policy information
        """
        pass

    @abstractmethod
    def get_resource_info(self) -> dict:
        """
        Get information about resource limits and usage.

        Returns:
            Dictionary containing resource information
        """
        pass
