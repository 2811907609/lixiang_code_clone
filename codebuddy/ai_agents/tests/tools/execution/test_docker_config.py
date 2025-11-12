"""Tests for Docker configuration."""

import pytest
import tempfile
import yaml
from pathlib import Path

from ai_agents.tools.execution.docker.docker_config import (
    DockerConfig,
    get_predefined_config,
    PREDEFINED_CONFIGS
)


class TestDockerConfig:
    """Test DockerConfig functionality."""

    def test_default_initialization(self):
        """Test default initialization."""
        config = DockerConfig(image="ubuntu:22.04")

        assert config.image == "ubuntu:22.04"
        assert config.timeout_seconds == 30.0
        assert config.working_dir == "/workspace"
        assert config.auto_remove is True
        assert config.memory_limit == "512m"
        assert config.cpu_limit == "1.0"
        assert config.network_mode == "none"
        assert config.read_only is True
        assert config.user == "1000:1000"
        assert isinstance(config.volumes, dict)
        assert isinstance(config.environment, dict)
        assert isinstance(config.security_opts, list)
        assert "no-new-privileges:true" in config.security_opts

    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        volumes = {"./code": "/workspace/code"}
        environment = {"DEBUG": "1"}
        security_opts = ["seccomp=unconfined"]

        config = DockerConfig(
            image="python:3.11",
            timeout_seconds=60.0,
            memory_limit="1g",
            cpu_limit="2.0",
            network_mode="bridge",
            read_only=False,
            user="root",
            volumes=volumes,
            environment=environment,
            security_opts=security_opts
        )

        assert config.image == "python:3.11"
        assert config.timeout_seconds == 60.0
        assert config.memory_limit == "1g"
        assert config.cpu_limit == "2.0"
        assert config.network_mode == "bridge"
        assert config.read_only is False
        assert config.user == "root"
        assert config.volumes == volumes
        assert config.environment == environment
        assert config.security_opts == security_opts

    def test_from_yaml(self):
        """Test loading configuration from YAML file."""
        config_data = {
            "image": "python:3.11-slim",
            "timeout_seconds": 120.0,
            "memory_limit": "1g",
            "cpu_limit": "2.0",
            "network_mode": "bridge",
            "volumes": {"./code": "/workspace/code"},
            "environment": {"PYTHONPATH": "/workspace", "DEBUG": "1"}
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            yaml_file = f.name

        try:
            config = DockerConfig.from_yaml(yaml_file)

            assert config.image == "python:3.11-slim"
            assert config.timeout_seconds == 120.0
            assert config.memory_limit == "1g"
            assert config.cpu_limit == "2.0"
            assert config.network_mode == "bridge"
            assert config.volumes == {"./code": "/workspace/code"}
            assert config.environment == {"PYTHONPATH": "/workspace", "DEBUG": "1"}
        finally:
            Path(yaml_file).unlink()

    def test_from_yaml_nonexistent_file(self):
        """Test loading from nonexistent YAML file."""
        with pytest.raises(FileNotFoundError):
            DockerConfig.from_yaml("/nonexistent/file.yaml")

    def test_from_dict(self):
        """Test creating configuration from dictionary."""
        config_dict = {
            "image": "node:18-alpine",
            "memory_limit": "512m",
            "environment": {"NODE_ENV": "development"}
        }

        config = DockerConfig.from_dict(config_dict)

        assert config.image == "node:18-alpine"
        assert config.memory_limit == "512m"
        assert config.environment == {"NODE_ENV": "development"}

    def test_to_dict(self):
        """Test converting configuration to dictionary."""
        config = DockerConfig(
            image="ubuntu:22.04",
            memory_limit="1g",
            environment={"TEST": "value"}
        )

        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert config_dict["image"] == "ubuntu:22.04"
        assert config_dict["memory_limit"] == "1g"
        assert config_dict["environment"] == {"TEST": "value"}
        assert "timeout_seconds" in config_dict
        assert "working_dir" in config_dict

    def test_validate_success(self):
        """Test successful validation."""
        config = DockerConfig(image="ubuntu:22.04")
        config.validate()  # Should not raise

    def test_validate_missing_image(self):
        """Test validation with missing image."""
        config = DockerConfig(image="")
        with pytest.raises(ValueError, match="Docker image is required"):
            config.validate()

    def test_validate_invalid_timeout(self):
        """Test validation with invalid timeout."""
        config = DockerConfig(image="ubuntu:22.04", timeout_seconds=-1)
        with pytest.raises(ValueError, match="timeout_seconds must be positive"):
            config.validate()

    def test_validate_invalid_memory_limit(self):
        """Test validation with invalid memory limit."""
        config = DockerConfig(image="ubuntu:22.04", memory_limit="invalid")
        with pytest.raises(ValueError, match="Invalid memory limit format"):
            config.validate()

    def test_validate_invalid_cpu_limit(self):
        """Test validation with invalid CPU limit."""
        config = DockerConfig(image="ubuntu:22.04", cpu_limit="invalid")
        with pytest.raises(ValueError, match="Invalid CPU limit format"):
            config.validate()

    def test_memory_limit_validation(self):
        """Test memory limit format validation."""
        config = DockerConfig(image="ubuntu:22.04")

        # Valid formats
        assert config._is_valid_memory_limit("512m")
        assert config._is_valid_memory_limit("1g")
        assert config._is_valid_memory_limit("1024k")
        assert config._is_valid_memory_limit("2G")
        assert config._is_valid_memory_limit("100")

        # Invalid formats
        assert not config._is_valid_memory_limit("invalid")
        assert not config._is_valid_memory_limit("1.5g")
        assert not config._is_valid_memory_limit("")

    def test_cpu_limit_validation(self):
        """Test CPU limit format validation."""
        config = DockerConfig(image="ubuntu:22.04")

        # Valid formats
        assert config._is_valid_cpu_limit("1.0")
        assert config._is_valid_cpu_limit("0.5")
        assert config._is_valid_cpu_limit("2")

        # Invalid formats
        assert not config._is_valid_cpu_limit("invalid")
        assert not config._is_valid_cpu_limit("")


class TestPredefinedConfigs:
    """Test predefined configurations."""

    def test_predefined_configs_exist(self):
        """Test that predefined configurations exist."""
        assert "ubuntu" in PREDEFINED_CONFIGS
        assert "python" in PREDEFINED_CONFIGS
        assert "node" in PREDEFINED_CONFIGS
        assert "alpine" in PREDEFINED_CONFIGS

    def test_get_predefined_config_ubuntu(self):
        """Test getting Ubuntu predefined config."""
        config = get_predefined_config("ubuntu")
        expected = PREDEFINED_CONFIGS["ubuntu"]

        assert isinstance(config, DockerConfig)
        assert config.image == expected.image
        assert config.memory_limit == expected.memory_limit

    def test_get_predefined_config_python(self):
        """Test getting Python predefined config."""
        config = get_predefined_config("python")
        expected = PREDEFINED_CONFIGS["python"]

        assert isinstance(config, DockerConfig)
        assert config.image == expected.image
        assert config.memory_limit == expected.memory_limit
        assert config.environment == expected.environment

    def test_get_predefined_config_node(self):
        """Test getting Node.js predefined config."""
        config = get_predefined_config("node")
        expected = PREDEFINED_CONFIGS["node"]

        assert isinstance(config, DockerConfig)
        assert config.image == expected.image
        assert config.memory_limit == expected.memory_limit
        assert config.environment == expected.environment

    def test_get_predefined_config_alpine(self):
        """Test getting Alpine predefined config."""
        config = get_predefined_config("alpine")
        expected = PREDEFINED_CONFIGS["alpine"]

        assert isinstance(config, DockerConfig)
        assert config.image == expected.image
        assert config.memory_limit == expected.memory_limit

    def test_get_predefined_config_invalid(self):
        """Test getting invalid predefined config."""
        with pytest.raises(ValueError, match="Unknown predefined config"):
            get_predefined_config("nonexistent")

    def test_all_predefined_configs_valid(self):
        """Test that all predefined configs are valid."""
        for _, config in PREDEFINED_CONFIGS.items():
            assert isinstance(config, DockerConfig)
            config.validate()  # Should not raise
