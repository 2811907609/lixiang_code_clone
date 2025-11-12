# Unified execution environment tools

from .host.host_executor import HostExecutor
from .docker.docker_sandbox import DockerSandbox


def create_execution_environment(env_type: str, **kwargs):
    """
    Factory function to create execution environments.

    Args:
        env_type: Type of environment ("host", "docker")
        **kwargs: Environment-specific configuration

    Returns:
        ExecutionEnvironment instance

    Raises:
        ValueError: If env_type is not supported
    """
    if env_type == "host":
        return HostExecutor(**kwargs)
    elif env_type == "docker":
        return DockerSandbox(**kwargs)
    else:
        available = ["host", "docker"]
        raise ValueError(f"Unknown environment type: {env_type}. Available: {available}")


__all__ = [
    'create_execution_environment',
    'HostExecutor',
    'DockerSandbox'
]
