"""Configuration loader for JSON hook configurations."""

import json
import os
from typing import Any, Dict, List, Optional
import logging

from .types import HookEvent, ScriptHook

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Exception raised for configuration-related errors."""
    pass


class ConfigurationLoader:
    """Loads and validates hook configurations from JSON files."""

    CONFIG_PATHS = [
        "~/.ai_agents/settings.json",
        "ai_agents/settings.json",
        "ai_agents/settings.local.json"
    ]

    def load_configurations(self) -> Dict[str, Any]:
        """
        Load configurations from all available sources.

        Returns:
            Dict containing merged configuration data.

        Raises:
            ConfigurationError: If configuration loading fails critically.
        """
        configs = []

        for config_path in self.CONFIG_PATHS:
            try:
                expanded_path = os.path.expanduser(config_path)
                if os.path.exists(expanded_path):
                    logger.debug(f"Loading configuration from {expanded_path}")
                    config = self._load_single_config(expanded_path)
                    if config:
                        configs.append(config)
                        logger.info(f"Successfully loaded configuration from {expanded_path}")
                else:
                    logger.debug(f"Configuration file not found: {expanded_path}")
            except ConfigurationError:
                # Re-raise configuration errors as they contain detailed error information
                raise
            except Exception as e:
                logger.warning(f"Failed to load configuration from {config_path}: {e}")
                # Continue loading other configs even if one fails
                continue

        if not configs:
            logger.info("No hook configurations found, using empty configuration")
            return {"hooks": {}, "hook_settings": {}}

        try:
            merged_config = self.merge_configurations(configs)
            logger.info(f"Successfully merged {len(configs)} configuration files")
            return merged_config
        except Exception as e:
            raise ConfigurationError(f"Failed to merge configurations: {e}")

    def _load_single_config(self, config_path: str) -> Optional[Dict[str, Any]]:
        """
        Load a single configuration file.

        Args:
            config_path: Path to the configuration file.

        Returns:
            Configuration dictionary or None if loading fails.

        Raises:
            ConfigurationError: If the file exists but cannot be parsed.
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Validate the configuration
            if not self.validate_configuration(config):
                raise ConfigurationError(f"Invalid configuration in {config_path}")

            return config

        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Malformed JSON in {config_path}: {e}")
        except FileNotFoundError:
            # This should not happen as we check existence before calling
            return None
        except Exception as e:
            raise ConfigurationError(f"Error reading {config_path}: {e}")

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Validate a configuration dictionary.

        Args:
            config: Configuration dictionary to validate.

        Returns:
            True if configuration is valid, False otherwise.
        """
        if not isinstance(config, dict):
            logger.error("Configuration must be a JSON object")
            return False

        # Validate hooks section if present
        if "hooks" in config and not self._validate_hooks_section(config["hooks"]):
            return False

        # Validate hook_settings section if present
        if "hook_settings" in config and not self._validate_hook_settings_section(config["hook_settings"]):
            return False

        return True

    def _validate_hooks_section(self, hooks: Any) -> bool:
        """Validate the hooks section of the configuration."""
        if not isinstance(hooks, dict):
            logger.error("'hooks' section must be an object")
            return False

        for event_name, event_hooks in hooks.items():
            # Check if event name is valid
            try:
                HookEvent(event_name)
            except ValueError:
                logger.error(f"Invalid hook event name: {event_name}")
                return False

            if not isinstance(event_hooks, list):
                logger.error(f"Hook event '{event_name}' must be a list")
                return False

            if not all(self._validate_hook_group(group) for group in event_hooks):
                return False

        return True

    def _validate_hook_group(self, hook_group: Any) -> bool:
        """Validate a single hook group configuration."""
        if not isinstance(hook_group, dict):
            logger.error("Hook group must be an object")
            return False

        if "matcher" not in hook_group or "hooks" not in hook_group:
            logger.error("Hook group missing required 'matcher' or 'hooks' field")
            return False

        if not isinstance(hook_group["matcher"], str) or not hook_group["matcher"]:
            logger.error("Hook group 'matcher' must be a non-empty string")
            return False

        if not isinstance(hook_group["hooks"], list):
            logger.error("Hook group 'hooks' must be a list")
            return False

        return all(self._validate_individual_hook(hook) for hook in hook_group["hooks"])

    def _validate_individual_hook(self, hook: Any) -> bool:
        """Validate a single hook configuration."""
        if not isinstance(hook, dict) or "type" not in hook:
            logger.error("Hook must be an object with 'type' field")
            return False

        hook_type = hook["type"]
        if hook_type not in ["command", "python"]:
            logger.error(f"Invalid hook type: {hook_type}")
            return False

        # Command hooks need a command field
        if hook_type == "command" and (not hook.get("command") or not isinstance(hook["command"], str)):
            logger.error("Command hook must have non-empty 'command' string")
            return False

        # Validate optional numeric fields
        if "timeout" in hook and (not isinstance(hook["timeout"], int) or hook["timeout"] <= 0):
            logger.error("Hook 'timeout' must be a positive integer")
            return False

        return True

    def _validate_hook_settings_section(self, settings: Any) -> bool:
        """Validate the hook_settings section of the configuration."""
        if not isinstance(settings, dict):
            logger.error("'hook_settings' section must be an object")
            return False

        # Check numeric settings
        for key in ["default_timeout", "max_concurrent_hooks"]:
            if key in settings and (not isinstance(settings[key], int) or settings[key] <= 0):
                logger.error(f"'{key}' must be a positive integer")
                return False

        # Check boolean settings
        if "enable_performance_monitoring" in settings and not isinstance(settings["enable_performance_monitoring"], bool):
            logger.error("'enable_performance_monitoring' must be a boolean")
            return False

        return True

    def merge_configurations(self, configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge multiple configuration dictionaries with proper precedence.

        Later configurations in the list take precedence over earlier ones.

        Args:
            configs: List of configuration dictionaries to merge.

        Returns:
            Merged configuration dictionary.
        """
        if not configs:
            return {"hooks": {}, "hook_settings": {}}

        merged = {"hooks": {}, "hook_settings": {}}

        for config in configs:
            # Merge hooks section
            if "hooks" in config:
                for event_name, event_hooks in config["hooks"].items():
                    if event_name not in merged["hooks"]:
                        merged["hooks"][event_name] = []

                    # Append hooks from this config to the merged list
                    merged["hooks"][event_name].extend(event_hooks)

            # Merge hook_settings section (later configs override earlier ones)
            if "hook_settings" in config:
                merged["hook_settings"].update(config["hook_settings"])

        return merged



    def parse_script_hooks_from_config(self, config: Dict[str, Any]) -> Dict[HookEvent, List[ScriptHook]]:
        """
        Parse script hooks from configuration into ScriptHook objects.

        Args:
            config: Configuration dictionary.

        Returns:
            Dictionary mapping HookEvent to list of ScriptHook objects.
        """
        script_hooks = {}

        if "hooks" not in config:
            return script_hooks

        default_timeout = config.get("hook_settings", {}).get("default_timeout", 60)

        for event_name, event_hooks in config["hooks"].items():
            try:
                hook_event = HookEvent(event_name)
                script_hooks[hook_event] = []

                for hook_group in event_hooks:
                    matcher = hook_group["matcher"]

                    for hook in hook_group["hooks"]:
                        if hook["type"] == "command":
                            script_hook = ScriptHook(
                                matcher=matcher,
                                command=hook["command"],
                                timeout=hook.get("timeout", default_timeout),
                                working_directory=hook.get("working_directory")
                            )
                            script_hooks[hook_event].append(script_hook)

            except ValueError as e:
                logger.warning(f"Skipping invalid hook event '{event_name}': {e}")
                continue

        return script_hooks
