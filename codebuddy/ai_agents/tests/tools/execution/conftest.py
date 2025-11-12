"""Pytest configuration for execution environment tests."""

import pytest
import logging


@pytest.fixture(autouse=True)
def setup_logging():
    """Setup logging for tests."""
    logging.basicConfig(level=logging.WARNING)


@pytest.fixture
def mock_docker_unavailable(monkeypatch):
    """Mock Docker as unavailable for testing."""
    def mock_check_docker():
        raise RuntimeError("Docker is not available")

    monkeypatch.setattr(
        "ai_agents.tools.execution.docker.persistent_container.PersistentDockerContainer._check_docker_available",
        mock_check_docker
    )


@pytest.fixture
def sample_docker_config():
    """Sample Docker configuration for testing."""
    return {
        "image": "ubuntu:22.04",
        "timeout_seconds": 30.0,
        "memory_limit": "512m",
        "cpu_limit": "1.0",
        "network_mode": "none",
        "working_dir": "/workspace",
        "environment": {"TEST": "value"},
        "volumes": {"./test": "/workspace/test"}
    }
