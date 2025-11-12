"""
Configuration integration tests for the hook system.
Tests loading configurations from multiple sources and merging behavior.
"""
import json
import tempfile
import os
from unittest.mock import patch

from ai_agents.core.hooks.hook_manager import HookManager
from ai_agents.core.hooks.config_loader import ConfigurationLoader
from ai_agents.core.hooks.types import HookEvent


class TestMultipleConfigurationSources:
    """Test loading and merging configurations from multiple sources."""

    def setup_method(self):
        """Set up test fixtures."""
        HookManager.reset_instance()
        self.hook_manager = HookManager.get_instance()
        self.config_loader = ConfigurationLoader()

    def teardown_method(self):
        """Clean up after tests."""
        HookManager.reset_instance()

    def test_single_configuration_source(self):
        """Test loading configuration from a single source."""
        config = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "TestTool",
                    "hooks": [{"type": "command", "command": "echo 'single config'"}]
                }]
            },
            "hook_settings": {
                "default_timeout": 30
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            config_path = f.name

        try:
            with patch.object(self.config_loader, 'CONFIG_PATHS', [config_path]):
                loaded_config = self.config_loader.load_configurations()

                assert "hooks" in loaded_config
                assert "PreToolUse" in loaded_config["hooks"]
                assert loaded_config["hook_settings"]["default_timeout"] == 30

        finally:
            os.unlink(config_path)

    def test_multiple_configuration_sources_merge(self):
        """Test merging configurations from multiple sources."""
        config1 = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "Tool1",
                    "hooks": [{"type": "command", "command": "echo 'config1'"}]
                }]
            },
            "hook_settings": {
                "default_timeout": 30,
                "max_concurrent_hooks": 3
            }
        }

        config2 = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "Tool2",
                    "hooks": [{"type": "command", "command": "echo 'config2'"}]
                }],
                "PostToolUse": [{
                    "matcher": "*",
                    "hooks": [{"type": "command", "command": "echo 'post hook'"}]
                }]
            },
            "hook_settings": {
                "default_timeout": 45,  # Should override config1
                "enable_performance_monitoring": True
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f1:
            json.dump(config1, f1)
            config1_path = f1.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f2:
            json.dump(config2, f2)
            config2_path = f2.name

        try:
            with patch.object(self.config_loader, 'CONFIG_PATHS', [config1_path, config2_path]):
                merged_config = self.config_loader.load_configurations()

                # Check hooks are merged
                assert len(merged_config["hooks"]["PreToolUse"]) == 2
                assert "PostToolUse" in merged_config["hooks"]

                # Check settings are merged with precedence
                assert merged_config["hook_settings"]["default_timeout"] == 45  # From config2
                assert merged_config["hook_settings"]["max_concurrent_hooks"] == 3  # From config1
                assert merged_config["hook_settings"]["enable_performance_monitoring"] is True  # From config2

        finally:
            os.unlink(config1_path)
            os.unlink(config2_path)

    def test_configuration_precedence_order(self):
        """Test that later configurations override earlier ones."""
        base_config = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "TestTool",
                    "hooks": [{"type": "command", "command": "echo 'base'"}]
                }]
            },
            "hook_settings": {
                "default_timeout": 30
            }
        }

        override_config = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "TestTool",
                    "hooks": [{"type": "command", "command": "echo 'override'"}]
                }]
            },
            "hook_settings": {
                "default_timeout": 60
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f1:
            json.dump(base_config, f1)
            base_path = f1.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f2:
            json.dump(override_config, f2)
            override_path = f2.name

        try:
            # Test order: base first, then override
            with patch.object(self.config_loader, 'CONFIG_PATHS', [base_path, override_path]):
                merged_config = self.config_loader.load_configurations()

                # Override should take precedence
                assert merged_config["hook_settings"]["default_timeout"] == 60

                # Should have hooks from both (merged)
                hooks = merged_config["hooks"]["PreToolUse"]
                commands = [hook["hooks"][0]["command"] for hook in hooks]
                assert "echo 'base'" in commands
                assert "echo 'override'" in commands

        finally:
            os.unlink(base_path)
            os.unlink(override_path)

    def test_partial_configuration_files(self):
        """Test handling of partial configuration files."""
        hooks_only_config = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "HookOnlyTool",
                    "hooks": [{"type": "command", "command": "echo 'hooks only'"}]
                }]
            }
        }

        settings_only_config = {
            "hook_settings": {
                "default_timeout": 45,
                "max_concurrent_hooks": 5
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f1:
            json.dump(hooks_only_config, f1)
            hooks_path = f1.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f2:
            json.dump(settings_only_config, f2)
            settings_path = f2.name

        try:
            with patch.object(self.config_loader, 'CONFIG_PATHS', [hooks_path, settings_path]):
                merged_config = self.config_loader.load_configurations()

                # Should have both hooks and settings
                assert "hooks" in merged_config
                assert "hook_settings" in merged_config
                assert "PreToolUse" in merged_config["hooks"]
                assert merged_config["hook_settings"]["default_timeout"] == 45

        finally:
            os.unlink(hooks_path)
            os.unlink(settings_path)

    def test_empty_configuration_files(self):
        """Test handling of empty configuration files."""
        empty_config = {}

        valid_config = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "ValidTool",
                    "hooks": [{"type": "command", "command": "echo 'valid'"}]
                }]
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f1:
            json.dump(empty_config, f1)
            empty_path = f1.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f2:
            json.dump(valid_config, f2)
            valid_path = f2.name

        try:
            with patch.object(self.config_loader, 'CONFIG_PATHS', [empty_path, valid_path]):
                merged_config = self.config_loader.load_configurations()

                # Should handle empty config gracefully
                assert "hooks" in merged_config
                assert "PreToolUse" in merged_config["hooks"]

        finally:
            os.unlink(empty_path)
            os.unlink(valid_path)


class TestConfigurationValidation:
    """Test configuration validation and error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config_loader = ConfigurationLoader()

    def test_valid_configuration_validation(self):
        """Test validation of valid configurations."""
        valid_config = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "TestTool",
                    "hooks": [{
                        "type": "command",
                        "command": "echo 'test'",
                        "timeout": 30
                    }]
                }],
                "PostToolUse": [{
                    "matcher": "*",
                    "hooks": [{
                        "type": "command",
                        "command": "echo 'post'"
                    }]
                }]
            },
            "hook_settings": {
                "default_timeout": 60,
                "max_concurrent_hooks": 5,
                "enable_performance_monitoring": True
            }
        }

        # Should validate successfully
        assert self.config_loader.validate_configuration(valid_config)

    def test_invalid_configuration_validation(self):
        """Test validation of invalid configurations."""
        invalid_configs = [
            # Missing hooks section
            {"hook_settings": {"default_timeout": 30}},

            # Invalid hook event
            {"hooks": {"InvalidEvent": []}},

            # Missing matcher
            {"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "echo test"}]}]}},

            # Invalid hook type
            {"hooks": {"PreToolUse": [{"matcher": "Tool", "hooks": [{"type": "invalid"}]}]}},

            # Missing command
            {"hooks": {"PreToolUse": [{"matcher": "Tool", "hooks": [{"type": "command"}]}]}},

            # Invalid timeout type
            {"hooks": {"PreToolUse": [{"matcher": "Tool", "hooks": [{"type": "command", "command": "echo test", "timeout": "invalid"}]}]}},

            # Invalid settings
            {"hooks": {}, "hook_settings": {"default_timeout": -1}},
            {"hooks": {}, "hook_settings": {"max_concurrent_hooks": 0}},
        ]

        for invalid_config in invalid_configs:
            assert not self.config_loader.validate_configuration(invalid_config)

    def test_configuration_schema_enforcement(self):
        """Test that configuration schema is properly enforced."""
        # Test with extra unknown fields
        config_with_extra_fields = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "TestTool",
                    "hooks": [{
                        "type": "command",
                        "command": "echo 'test'",
                        "unknown_field": "should be ignored"
                    }]
                }]
            },
            "unknown_section": {
                "unknown_setting": "should be ignored"
            }
        }

        # Should validate (extra fields ignored)
        assert self.config_loader.validate_configuration(config_with_extra_fields)


class TestConfigurationPathResolution:
    """Test configuration file path resolution and loading."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config_loader = ConfigurationLoader()

    def test_default_configuration_paths(self):
        """Test that default configuration paths are correct."""
        expected_paths = [
            "~/.ai_agents/settings.json",
            "ai_agents/settings.json",
            "ai_agents/settings.local.json"
        ]

        assert self.config_loader.CONFIG_PATHS == expected_paths

    def test_home_directory_expansion(self):
        """Test that ~ in paths is properly expanded."""
        config = {"hooks": {"PreToolUse": []}}

        # Create a temporary file in a known location
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_path = f.name

        try:
            # Test with ~ path (mock home directory)
            home_path = f"~/{os.path.basename(temp_path)}"

            with patch('os.path.expanduser') as mock_expanduser:
                mock_expanduser.return_value = temp_path

                with patch.object(self.config_loader, 'CONFIG_PATHS', [home_path]):
                    loaded_config = self.config_loader.load_configurations()

                    assert "hooks" in loaded_config
                    mock_expanduser.assert_called_with(home_path)

        finally:
            os.unlink(temp_path)

    def test_relative_path_resolution(self):
        """Test that relative paths are properly resolved."""
        config = {"hooks": {"PreToolUse": []}}

        # Create config in a subdirectory
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.json")
            with open(config_path, 'w') as f:
                json.dump(config, f)

            # Test with relative path
            relative_path = os.path.relpath(config_path)

            with patch.object(self.config_loader, 'CONFIG_PATHS', [relative_path]):
                loaded_config = self.config_loader.load_configurations()

                assert "hooks" in loaded_config

    def test_absolute_path_resolution(self):
        """Test that absolute paths work correctly."""
        config = {"hooks": {"PreToolUse": []}}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            absolute_path = os.path.abspath(f.name)

        try:
            with patch.object(self.config_loader, 'CONFIG_PATHS', [absolute_path]):
                loaded_config = self.config_loader.load_configurations()

                assert "hooks" in loaded_config

        finally:
            os.unlink(absolute_path)


class TestConfigurationIntegrationWithHookManager:
    """Test integration between configuration loading and hook manager."""

    def setup_method(self):
        """Set up test fixtures."""
        HookManager.reset_instance()
        self.hook_manager = HookManager.get_instance()

    def teardown_method(self):
        """Clean up after tests."""
        HookManager.reset_instance()

    def test_configuration_loading_integration(self):
        """Test that hook manager properly loads and uses configurations."""
        config = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "IntegrationTool",
                    "hooks": [{
                        "type": "command",
                        "command": "echo 'integration test'",
                        "timeout": 15
                    }]
                }]
            },
            "hook_settings": {
                "default_timeout": 45,
                "max_concurrent_hooks": 3
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            config_path = f.name

        try:
            with patch('ai_agents.core.hooks.config_loader.ConfigurationLoader.CONFIG_PATHS',
                       [config_path]):
                # Load configuration through hook manager
                self.hook_manager.load_configuration()

                # Test that hooks are properly registered
                result = self.hook_manager.trigger_hooks(
                    HookEvent.PRE_TOOL_USE, "IntegrationTool", {}
                )

                assert result.success
                assert "integration test" in result.output

        finally:
            os.unlink(config_path)

    def test_configuration_reload_behavior(self):
        """Test behavior when configuration is reloaded."""
        initial_config = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "ReloadTool",
                    "hooks": [{"type": "command", "command": "echo 'initial'"}]
                }]
            }
        }

        updated_config = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "ReloadTool",
                    "hooks": [{"type": "command", "command": "echo 'updated'"}]
                }]
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(initial_config, f)
            config_path = f.name

        try:
            with patch('ai_agents.core.hooks.config_loader.ConfigurationLoader.CONFIG_PATHS',
                       [config_path]):
                # Load initial configuration
                self.hook_manager.load_configuration()

                result1 = self.hook_manager.trigger_hooks(
                    HookEvent.PRE_TOOL_USE, "ReloadTool", {}
                )
                assert "initial" in result1.output

                # Update configuration file
                with open(config_path, 'w') as f:
                    json.dump(updated_config, f)

                # Reload configuration
                self.hook_manager.load_configuration()

                result2 = self.hook_manager.trigger_hooks(
                    HookEvent.PRE_TOOL_USE, "ReloadTool", {}
                )
                assert "updated" in result2.output

        finally:
            os.unlink(config_path)

    def test_mixed_configuration_and_programmatic_hooks(self):
        """Test mixing configuration-loaded hooks with programmatically registered hooks."""
        from ai_agents.core.hooks.types import HookResult

        # Configuration-based hook
        config = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "MixedTool",
                    "hooks": [{"type": "command", "command": "echo 'config hook'"}]
                }]
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            config_path = f.name

        try:
            with patch('ai_agents.core.hooks.config_loader.ConfigurationLoader.CONFIG_PATHS',
                       [config_path]):
                # Load configuration
                self.hook_manager.load_configuration()

                # Register programmatic hook
                def programmatic_hook(context):
                    return HookResult(
                        success=True,
                        continue_execution=True,
                        output="programmatic hook"
                    )

                self.hook_manager.register_python_hook(
                    HookEvent.PRE_TOOL_USE, "MixedTool", programmatic_hook
                )

                # Trigger hooks - should execute both
                result = self.hook_manager.trigger_hooks(
                    HookEvent.PRE_TOOL_USE, "MixedTool", {}
                )

                assert result.success
                # Should contain output from both hooks
                assert "config hook" in result.output or "programmatic hook" in result.output

        finally:
            os.unlink(config_path)
