"""Docker configuration for sandboxed execution."""

from dataclasses import dataclass, field
from typing import Dict, List
import yaml
from pathlib import Path


default_image = 'artifactory.ep.chehejia.com/docker-remote/ubuntu:22.04'


@dataclass
class DockerConfig:
    """Configuration for Docker-based sandbox execution."""

    # Required fields
    image: str

    # Execution settings
    timeout_seconds: float = 30.0
    working_dir: str = "/workspace"
    auto_remove: bool = True

    # Resource limits
    memory_limit: str = "512m"
    cpu_limit: str = "1.0"

    # Security settings
    network_mode: str = "none"
    read_only: bool = True
    user: str = "1000:1000"  # Non-root user

    # Volumes and environment
    volumes: Dict[str, str] = field(default_factory=dict)
    environment: Dict[str, str] = field(default_factory=dict)

    # Security options
    security_opts: List[str] = field(default_factory=lambda: [
        "no-new-privileges:true",
        # TODO 目前有些环境的docker还不支持这个，这个先不开启
        # "seccomp=default"
    ])

    # Advanced settings
    cap_drop: List[str] = field(default_factory=lambda: ["ALL"])
    cap_add: List[str] = field(default_factory=list)
    tmpfs: Dict[str, str] = field(default_factory=lambda: {
        "/tmp": "rw,noexec,nosuid,size=100m"
    })

    @classmethod
    def from_yaml(cls, config_path: str) -> "DockerConfig":
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)

        return cls(**config_data)

    @classmethod
    def from_dict(cls, config_dict: Dict) -> "DockerConfig":
        """Create configuration from dictionary."""
        return cls(**config_dict)

    def to_dict(self) -> Dict:
        """Convert configuration to dictionary."""
        return {
            'image': self.image,
            'timeout_seconds': self.timeout_seconds,
            'working_dir': self.working_dir,
            'auto_remove': self.auto_remove,
            'memory_limit': self.memory_limit,
            'cpu_limit': self.cpu_limit,
            'network_mode': self.network_mode,
            'read_only': self.read_only,
            'user': self.user,
            'volumes': self.volumes,
            'environment': self.environment,
            'security_opts': self.security_opts,
            'cap_drop': self.cap_drop,
            'cap_add': self.cap_add,
            'tmpfs': self.tmpfs
        }

    def validate(self) -> None:
        """Validate configuration settings."""
        if not self.image:
            raise ValueError("Docker image is required")

        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        if self.memory_limit and not self._is_valid_memory_limit(self.memory_limit):
            raise ValueError(f"Invalid memory limit format: {self.memory_limit}")

        if self.cpu_limit and not self._is_valid_cpu_limit(self.cpu_limit):
            raise ValueError(f"Invalid CPU limit format: {self.cpu_limit}")

    def _is_valid_memory_limit(self, memory: str) -> bool:
        """Validate memory limit format (e.g., '512m', '1g')."""
        import re
        pattern = r'^\d+[kmgKMG]?$'
        return bool(re.match(pattern, memory))

    def _is_valid_cpu_limit(self, cpu: str) -> bool:
        """Validate CPU limit format (e.g., '1.0', '0.5')."""
        try:
            float(cpu)
            return True
        except ValueError:
            return False


# Predefined configurations for common environments
PREDEFINED_CONFIGS = {
    "ubuntu": DockerConfig(
        image="artifactory.ep.chehejia.com/docker-remote/ubuntu:22.04",
        timeout_seconds=30.0,
        memory_limit="512m"
    ),

    "python": DockerConfig(
        image="artifactory.ep.chehejia.com/docker-remote/python:3.12.11-bookworm",
        timeout_seconds=60.0,
        memory_limit="1g",
        environment={"PYTHONPATH": "/workspace"}
    ),

    "node": DockerConfig(
        image="artifactory.ep.chehejia.com/docker-remote/node:22.16.0-bookworm",
        timeout_seconds=60.0,
        memory_limit="1g",
        environment={"NODE_ENV": "sandbox"}
    ),

    "alpine": DockerConfig(
        image="artifactory.ep.chehejia.com/docker-remote/alpine:3.22.0",
        timeout_seconds=30.0,
        memory_limit="256m"
    )
}


def get_predefined_config(name: str) -> DockerConfig:
    """Get a predefined configuration by name."""
    if name not in PREDEFINED_CONFIGS:
        available = ", ".join(PREDEFINED_CONFIGS.keys())
        raise ValueError(f"Unknown predefined config '{name}'. Available: {available}")

    return PREDEFINED_CONFIGS[name]
