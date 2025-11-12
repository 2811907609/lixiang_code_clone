"""Tests for the configuration loader."""

import json
import os
import tempfile
import pytest
from unittest.mock import patch, mock_open

from ai_agents.core.hooks.config_loader import ConfigurationLoader, ConfigurationError
from ai_agents.core.hooks.types import HookEvent


class TestConfigurationLoader:
    """Test cases for ConfigurationLoader."""

    def setup_method(self):
        """Set up test fixtures."""
        self.loader = ConfigurationLoader()

    def test_init(self):
        """Test ConfigurationLoader initialization."""
        assert self.loader is not None

    def test_load_configurations_no_files(self):
        """Test loading configurations when no files exist."""
        with patch('os.path.exists', return_value=False):
            config = self.loader.load_configurations()

        assert config == {"hooks": {}, "hook_settings": {}}

    def test_load_configurations_single_file(self):
        """Test loading configuration from a single file."""
        test_config = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "FileWriter",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "echo 'test'",
                                "timeout": 30
                            }
                        ]
                    }
                ]
            },
            "hook_settings": {
                "default_timeout": 60
            }
        }

        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(test_config))):
            config = self.loader.load_configurations()

        assert config["hooks"]["PreToolUse"][0]["matcher"] == "FileWriter"
        assert config["hook_settings"]["default_timeout"] == 60

    def test_load_configurations_multiple_files(self):
        """Test loading and merging configurations from multiple files."""
        config1 = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "FileWriter",
                        "hooks": [{"type": "command", "command": "echo 'config1'"}]
                    }
                ]
            },
            "hook_settings": {"default_timeout": 30}
        }

        config2 = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "CodeEditor",
                        "hooks": [{"type": "command", "command": "echo 'config2'"}]
                    }
                ]
            },
            "hook_settings": {"default_timeout": 60}
        }

        # Test merge_configurations directly instead of the full load process
        config = self.loader.merge_configurations([config1, config2])

        # Should have hooks from both configs
        assert len(config["hooks"]["PreToolUse"]) == 2
        # Later config should override settings
        assert config["hook_settings"]["default_timeout"] == 60

    def test_load_configurations_malformed_json(self):
        """Test handling of malformed JSON files."""
        # Create a temporary file with malformed JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"invalid": json}')  # Missing quotes around json
            malformed_file = f.name

        try:
            # Temporarily replace the config paths
            original_paths = self.loader.CONFIG_PATHS
            self.loader.CONFIG_PATHS = [malformed_file]

            # Should raise ConfigurationError for malformed JSON
            with pytest.raises(ConfigurationError):
                self.loader.load_configurations()
        finally:
            # Restore original paths and clean up
            self.loader.CONFIG_PATHS = original_paths
            os.unlink(malformed_file)

    def test_validate_configuration_valid(self):
        """Test validation of valid configuration."""
        valid_config = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "FileWriter",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "echo 'test'",
                                "timeout": 30,
                                "working_directory": "/tmp"
                            }
                        ]
                    }
                ]
            },
            "hook_settings": {
                "default_timeout": 60,
                "max_concurrent_hooks": 5,
                "enable_performance_monitoring": True
            }
        }

        assert self.loader.validate_configuration(valid_config) is True

    def test_validate_configuration_invalid_structure(self):
        """Test validation of invalid configuration structure."""
        # Not a dict
        assert self.loader.validate_configuration("invalid") is False

        # Invalid hooks section
        invalid_config = {"hooks": "not a dict"}
        assert self.loader.validate_configuration(invalid_config) is False

        # Invalid hook event name
        invalid_config = {"hooks": {"InvalidEvent": []}}
        assert self.loader.validate_configuration(invalid_config) is False

    def test_validate_configuration_invalid_hook_group(self):
        """Test validation of invalid hook group."""
        # Missing matcher
        invalid_config = {
            "hooks": {
                "PreToolUse": [
                    {
                        "hooks": [{"type": "command", "command": "echo 'test'"}]
                    }
                ]
            }
        }
        assert self.loader.validate_configuration(invalid_config) is False

        # Missing hooks
        invalid_config = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "FileWriter"
                    }
                ]
            }
        }
        assert self.loader.validate_configuration(invalid_config) is False

        # Empty matcher
        invalid_config = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "",
                        "hooks": [{"type": "command", "command": "echo 'test'"}]
                    }
                ]
            }
        }
        assert self.loader.validate_configuration(invalid_config) is False

    def test_validate_configuration_invalid_hook(self):
        """Test validation of invalid individual hook."""
        # Missing type
        invalid_config = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "FileWriter",
                        "hooks": [{"command": "echo 'test'"}]
                    }
                ]
            }
        }
        assert self.loader.validate_configuration(invalid_config) is False

        # Invalid type
        invalid_config = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "FileWriter",
                        "hooks": [{"type": "invalid", "command": "echo 'test'"}]
                    }
                ]
            }
        }
        assert self.loader.validate_configuration(invalid_config) is False

        # Command hook missing command
        invalid_config = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "FileWriter",
                        "hooks": [{"type": "command"}]
                    }
                ]
            }
        }
        assert self.loader.validate_configuration(invalid_config) is False

        # Invalid timeout
        invalid_config = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "FileWriter",
                        "hooks": [{"type": "command", "command": "echo 'test'", "timeout": -1}]
                    }
                ]
            }
        }
        assert self.loader.validate_configuration(invalid_config) is False

    def test_validate_configuration_invalid_settings(self):
        """Test validation of invalid hook settings."""
        # Invalid default_timeout
        invalid_config = {
            "hook_settings": {"default_timeout": -1}
        }
        assert self.loader.validate_configuration(invalid_config) is False

        # Invalid max_concurrent_hooks
        invalid_config = {
            "hook_settings": {"max_concurrent_hooks": 0}
        }
        assert self.loader.validate_configuration(invalid_config) is False

        # Invalid enable_performance_monitoring
        invalid_config = {
            "hook_settings": {"enable_performance_monitoring": "yes"}
        }
        assert self.loader.validate_configuration(invalid_config) is False

    def test_merge_configurations_empty(self):
        """Test merging empty configurations."""
        result = self.loader.merge_configurations([])
        assert result == {"hooks": {}, "hook_settings": {}}

    def test_merge_configurations_single(self):
        """Test merging single configuration."""
        config = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "FileWriter",
                        "hooks": [{"type": "command", "command": "echo 'test'"}]
                    }
                ]
            },
            "hook_settings": {"default_timeout": 60}
        }

        result = self.loader.merge_configurations([config])
        assert result == config

    def test_merge_configurations_multiple(self):
        """Test merging multiple configurations."""
        config1 = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "FileWriter",
                        "hooks": [{"type": "command", "command": "echo 'config1'"}]
                    }
                ]
            },
            "hook_settings": {"default_timeout": 30, "max_concurrent_hooks": 3}
        }

        config2 = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "CodeEditor",
                        "hooks": [{"type": "command", "command": "echo 'config2'"}]
                    }
                ],
                "PostToolUse": [
                    {
                        "matcher": "*",
                        "hooks": [{"type": "command", "command": "echo 'post'"}]
                    }
                ]
            },
            "hook_settings": {"default_timeout": 60}
        }

        result = self.loader.merge_configurations([config1, config2])

        # Should have hooks from both configs
        assert len(result["hooks"]["PreToolUse"]) == 2
        assert len(result["hooks"]["PostToolUse"]) == 1

        # Later config should override settings
        assert result["hook_settings"]["default_timeout"] == 60
        assert result["hook_settings"]["max_concurrent_hooks"] == 3

    def test_parse_script_hooks_from_config(self):
        """Test parsing script hooks from configuration."""
        config = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "FileWriter",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "echo 'test'",
                                "timeout": 30,
                                "working_directory": "/tmp"
                            }
                        ]
                    }
                ],
                "PostToolUse": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "logger 'tool executed'"
                            }
                        ]
                    }
                ]
            },
            "hook_settings": {
                "default_timeout": 45
            }
        }

        script_hooks = self.loader.parse_script_hooks_from_config(config)

        # Should have hooks for both events
        assert HookEvent.PRE_TOOL_USE in script_hooks
        assert HookEvent.POST_TOOL_USE in script_hooks

        # Check PreToolUse hook
        pre_hooks = script_hooks[HookEvent.PRE_TOOL_USE]
        assert len(pre_hooks) == 1
        assert pre_hooks[0].matcher == "FileWriter"
        assert pre_hooks[0].command == "echo 'test'"
        assert pre_hooks[0].timeout == 30
        assert pre_hooks[0].working_directory == "/tmp"

        # Check PostToolUse hook (should use default timeout)
        post_hooks = script_hooks[HookEvent.POST_TOOL_USE]
        assert len(post_hooks) == 1
        assert post_hooks[0].matcher == "*"
        assert post_hooks[0].command == "logger 'tool executed'"
        assert post_hooks[0].timeout == 45  # default timeout
        assert post_hooks[0].working_directory is None

    def test_parse_script_hooks_empty_config(self):
        """Test parsing script hooks from empty configuration."""
        config = {}
        script_hooks = self.loader.parse_script_hooks_from_config(config)
        assert script_hooks == {}

    def test_parse_script_hooks_skip_python_hooks(self):
        """Test that Python hooks are skipped during script hook parsing."""
        config = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "FileWriter",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "echo 'test'"
                            },
                            {
                                "type": "python",
                                "function": "some_function"
                            }
                        ]
                    }
                ]
            }
        }

        script_hooks = self.loader.parse_script_hooks_from_config(config)

        # Should only have the command hook, not the python hook
        pre_hooks = script_hooks[HookEvent.PRE_TOOL_USE]
        assert len(pre_hooks) == 1
        assert pre_hooks[0].command == "echo 'test'"

    def test_parse_script_hooks_invalid_event(self):
        """Test handling of invalid hook events during parsing."""
        config = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "FileWriter",
                        "hooks": [{"type": "command", "command": "echo 'valid'"}]
                    }
                ],
                "InvalidEvent": [
                    {
                        "matcher": "*",
                        "hooks": [{"type": "command", "command": "echo 'invalid'"}]
                    }
                ]
            }
        }

        script_hooks = self.loader.parse_script_hooks_from_config(config)

        # Should only have the valid event
        assert HookEvent.PRE_TOOL_USE in script_hooks
        assert len(script_hooks) == 1

    def test_configuration_paths(self):
        """Test that configuration paths are correctly defined."""
        expected_paths = [
            "~/.ai_agents/settings.json",
            "ai_agents/settings.json",
            "ai_agents/settings.local.json"
        ]

        assert self.loader.CONFIG_PATHS == expected_paths

    def test_load_single_config_file_not_found(self):
        """Test loading single config when file doesn't exist."""
        result = self.loader._load_single_config("/nonexistent/path.json")
        assert result is None

    def test_load_single_config_permission_error(self):
        """Test loading single config with permission error."""
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            with pytest.raises(ConfigurationError, match="Error reading"):
                self.loader._load_single_config("/some/path.json")

    def test_load_single_config_validation_failure(self):
        """Test loading single config that fails validation."""
        invalid_config = {"hooks": "invalid"}

        with patch('builtins.open', mock_open(read_data=json.dumps(invalid_config))):
            with pytest.raises(ConfigurationError, match="Invalid configuration"):
                self.loader._load_single_config("/some/path.json")


class TestConfigurationLoaderIntegration:
    """Integration tests for ConfigurationLoader with real files."""

    def test_load_configurations_real_files(self):
        """Test loading configurations from real temporary files."""
        config1 = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "FileWriter",
                        "hooks": [{"type": "command", "command": "echo 'test1'"}]
                    }
                ]
            },
            "hook_settings": {"default_timeout": 30}
        }

        config2 = {
            "hooks": {
                "PostToolUse": [
                    {
                        "matcher": "*",
                        "hooks": [{"type": "command", "command": "echo 'test2'"}]
                    }
                ]
            },
            "hook_settings": {"default_timeout": 60}
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create temporary config files
            config1_path = os.path.join(temp_dir, "config1.json")
            config2_path = os.path.join(temp_dir, "config2.json")

            with open(config1_path, 'w') as f:
                json.dump(config1, f)

            with open(config2_path, 'w') as f:
                json.dump(config2, f)

            # Mock the CONFIG_PATHS to use our temporary files
            loader = ConfigurationLoader()
            loader.CONFIG_PATHS = [config1_path, config2_path]

            result = loader.load_configurations()

            # Should have hooks from both files
            assert "PreToolUse" in result["hooks"]
            assert "PostToolUse" in result["hooks"]
            assert result["hook_settings"]["default_timeout"] == 60  # from config2
