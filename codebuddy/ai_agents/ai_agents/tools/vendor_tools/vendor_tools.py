import os
import re
import platform
import subprocess
import urllib.request
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass

import yaml
from packaging import version

from sysutils.xtypes import dataclass_from_dict



@dataclass
class ToolConfig:
    """Configuration for a vendor tool."""
    name: str
    download_version: str
    min_version: str
    version_args: str
    version_reg_pattern: str
    download_url: Optional[str] = None


@dataclass
class Config:
    """Main configuration container."""
    download_dir: str
    download_url: str
    tools: List[ToolConfig]



class ToolManager:
    """Manages downloading and version checking of vendor tools."""

    def __init__(self, config_path: str = None):
        """Initialize with configuration file path."""
        if config_path is None:
            config_path = Path(__file__).parent / "tools.yaml"

        self.config = self._load_config(config_path)
        self.download_dir = Path(os.path.expandvars(self.config.download_dir))
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def _load_config(self, config_path: str) -> Config:
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
            # Convert tools list to ToolConfig objects
            if 'tools' in data:
                data['tools'] = [dataclass_from_dict(ToolConfig, tool) for tool in data['tools']]
            return dataclass_from_dict(Config, data)

    def _get_system_info(self) -> tuple[str, str]:
        """Get current OS and architecture."""
        os_name = platform.system().lower()
        # Keep darwin as is, linux as is

        arch = platform.machine().lower()
        if arch in ["x86_64"]:
            arch = "amd64"
        elif arch in ["aarch64"]:
            arch = "arm64"
        # Keep arm64 and amd64 as is

        return os_name, arch

    def _substitute_variables(self, template: str, **kwargs) -> str:
        """Replace ${var} style variables in template string."""
        result = template
        for key, value in kwargs.items():
            result = result.replace(f"${{{key}}}", str(value))
        return result

    def _get_tool_path(self, tool_name: str) -> Path:
        """Get the expected path for a tool binary."""
        return self.download_dir / tool_name

    def _check_tool_exists(self, tool_path: Path) -> bool:
        """Check if tool binary exists and is executable."""
        return tool_path.exists() and tool_path.is_file() and os.access(tool_path, os.X_OK)

    def _get_current_version(self, tool_config: ToolConfig, tool_path: Path) -> Optional[str]:
        """Get current version of installed tool."""
        try:
            version_args = tool_config.version_args or "--version"
            # Construct command as list to handle paths with spaces correctly
            command = [str(tool_path)] + version_args.split()
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return None

            if tool_config.version_reg_pattern:
                match = re.search(tool_config.version_reg_pattern, result.stdout)
                if match:
                    return match.group(1)

            return None
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            return None

    def _version_meets_requirement(self, current_version: str, min_version: str) -> bool:
        """Check if current version meets minimum requirement."""
        try:
            return version.parse(current_version) >= version.parse(min_version)
        except version.InvalidVersion:
            return False

    def _build_download_url(self, tool_config: ToolConfig) -> str:
        """Build download URL for the tool."""
        if tool_config.download_url:
            return tool_config.download_url

        # Use global template
        os_name, arch = self._get_system_info()

        return self._substitute_variables(
            self.config.download_url,
            name=tool_config.name,
            version=tool_config.download_version,
            os=os_name,
            arch=arch
        )

    def _download_tool(self, url: str, tool_path: Path) -> bool:
        """Download tool binary from URL."""
        try:
            print(f"Downloading {tool_path.name} from {url}")
            urllib.request.urlretrieve(url, tool_path)

            # Make executable
            tool_path.chmod(0o755)
            return True
        except Exception as e:
            print(f"Failed to download {tool_path.name}: {e}")
            return False

    def ensure_tool(self, tool_name: str) -> bool:
        """Ensure tool is available and meets version requirements."""
        tool_config = self._find_tool_config(tool_name)
        if not tool_config:
            print(f"Tool '{tool_name}' not found in configuration")
            return False

        tool_path = self._get_tool_path(tool_name)

        # Check if tool exists and version is acceptable
        if self._check_tool_exists(tool_path):
            current_version = self._get_current_version(tool_config, tool_path)
            if current_version:
                if self._version_meets_requirement(current_version, tool_config.min_version):
                    print(f"Tool '{tool_name}' v{current_version} is already available")
                    return True
                else:
                    print(f"Tool '{tool_name}' v{current_version} does not meet minimum requirement v{tool_config.min_version}")

        # Download tool
        download_url = self._build_download_url(tool_config)
        if self._download_tool(download_url, tool_path):
            # Verify download
            if self._check_tool_exists(tool_path):
                new_version = self._get_current_version(tool_config, tool_path)
                print(f"Successfully installed '{tool_name}' v{new_version or 'unknown'}")
                return True

        print(f"Failed to install tool '{tool_name}'")
        return False

    def _find_tool_config(self, tool_name: str) -> Optional[ToolConfig]:
        """Find tool configuration by name."""
        for tool in self.config.tools:
            if tool.name == tool_name:
                return tool
        return None

    def ensure_all_tools(self) -> Dict[str, bool]:
        """Ensure all configured tools are available."""
        results = {}
        for tool_config in self.config.tools:
            results[tool_config.name] = self.ensure_tool(tool_config.name)
        return results

    def get_tool_path(self, tool_name: str) -> Optional[Path]:
        """Get path to tool binary if available."""
        tool_path = self._get_tool_path(tool_name)
        if self._check_tool_exists(tool_path):
            return tool_path
        return None


# Convenience functions
def ensure_tool(tool_name: str, config_path: str = None) -> bool:
    """Ensure a specific tool is available."""
    manager = ToolManager(config_path)
    return manager.ensure_tool(tool_name)


def ensure_all_tools(config_path: str = None) -> Dict[str, bool]:
    """Ensure all configured tools are available."""
    manager = ToolManager(config_path)
    return manager.ensure_all_tools()


def get_tool_path(tool_name: str, config_path: str = None) -> Optional[Path]:
    """Get path to tool binary if available."""
    manager = ToolManager(config_path)
    return manager.get_tool_path(tool_name)


def add_tools_to_path(config_path: str = None) -> str:
    """Add the download_dir to PATH environment variable.

    Returns:
        The updated PATH value.
    """
    manager = ToolManager(config_path)
    download_dir_str = str(manager.download_dir)

    current_path = os.environ.get('PATH', '')

    # Check if download_dir is already in PATH
    if download_dir_str not in current_path.split(os.pathsep):
        # Add download_dir to the beginning of PATH
        new_path = f"{download_dir_str}{os.pathsep}{current_path}"
        os.environ['PATH'] = new_path
        return new_path

    return current_path
