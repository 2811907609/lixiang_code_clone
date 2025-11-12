"""Abstract base class for execution environments."""

from abc import ABC, abstractmethod
from typing import List, Any


class ExecutionEnvironment(ABC):
    """
    Abstract base class for all execution environments.

    This defines the common interface that all execution environments
    (host, docker, vm, wasm, etc.) must implement.
    """

    @abstractmethod
    def tools(self) -> List[Any]:
        """
        Get list of tools for AI agents.

        Returns:
            List of tool functions that can be used by AI agents
        """
        pass

    @abstractmethod
    def start(self) -> None:
        """
        Start the execution environment.

        For some environments (like host), this might be a no-op.
        For others (like containers), this starts the environment.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Stop and clean up the execution environment.

        Should properly clean up any resources used by the environment.
        """
        pass

    @property
    @abstractmethod
    def is_started(self) -> bool:
        """
        Check if the execution environment is started and ready.

        Returns:
            True if environment is ready for command execution
        """
        pass

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
