
import os
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
import yaml

from ai_agents.tools.vendor_tools.vendor_tools import (
    ToolManager,
    ensure_tool,
    ensure_all_tools,
    get_tool_path,
    add_tools_to_path,
)


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        'download_dir': '/tmp/test_tools',
        'download_url': 'https://example.com/${name}/${version}/${name}-${os}-${arch}',
        'tools': [
            {
                'name': 'rg',
                'download_version': '14.1.1',
                'min_version': '13.0.0',
                'version_args': '-V',
                'version_reg_pattern': r'ripgrep\s(\d+\.\d+\.\d+)'
            },
            {
                'name': 'custom_tool',
                'download_version': '2.0.0',
                'min_version': '1.5.0',
                'version_args': '--version',
                'version_reg_pattern': r'version\s(\d+\.\d+\.\d+)',
                'download_url': 'https://custom.com/tool.bin'
            }
        ]
    }


@pytest.fixture
def temp_config_file(sample_config):
    """Create a temporary config file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(sample_config, f)
        yield f.name
    os.unlink(f.name)


class TestToolManager:
    def test_init(self):
        m = ToolManager()
        assert 'ept' in m.config.download_dir
        assert len(m.config.tools) > 0
        assert m.config.tools[0].name == "rg"

    def test_init_with_custom_config(self, temp_config_file):
        manager = ToolManager(temp_config_file)
        assert manager.config.download_dir == '/tmp/test_tools'
        assert len(manager.config.tools) == 2
        assert manager.config.tools[0].name == 'rg'

    @patch('platform.system')
    @patch('platform.machine')
    def test_get_system_info(self, mock_machine, mock_system):
        mock_system.return_value = 'Darwin'
        mock_machine.return_value = 'x86_64'

        manager = ToolManager()
        os_name, arch = manager._get_system_info()

        assert os_name == 'darwin'
        assert arch == 'amd64'

    @patch('platform.system')
    @patch('platform.machine')
    def test_get_system_info_arm64(self, mock_machine, mock_system):
        mock_system.return_value = 'Linux'
        mock_machine.return_value = 'aarch64'

        manager = ToolManager()
        os_name, arch = manager._get_system_info()

        assert os_name == 'linux'
        assert arch == 'arm64'

    def test_substitute_variables(self, temp_config_file):
        manager = ToolManager(temp_config_file)
        template = 'https://example.com/${name}/${version}/${os}-${arch}'
        result = manager._substitute_variables(
            template,
            name='tool',
            version='1.0.0',
            os='linux',
            arch='amd64'
        )
        assert result == 'https://example.com/tool/1.0.0/linux-amd64'

    def test_get_tool_path(self, temp_config_file):
        manager = ToolManager(temp_config_file)
        path = manager._get_tool_path('rg')
        assert path == Path('/tmp/test_tools/rg')

    @patch('os.access')
    def test_check_tool_exists(self, mock_access, temp_config_file):
        manager = ToolManager(temp_config_file)

        # Mock file exists and is executable
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_access.return_value = True

        assert manager._check_tool_exists(mock_path) is True

        # Mock file doesn't exist
        mock_path.exists.return_value = False
        assert manager._check_tool_exists(mock_path) is False

    @patch('subprocess.run')
    def test_get_current_version_success(self, mock_run, temp_config_file):
        manager = ToolManager(temp_config_file)
        tool_config = manager.config.tools[0]  # rg tool

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = 'ripgrep 14.1.1'
        mock_run.return_value = mock_result

        version = manager._get_current_version(tool_config, Path('/tmp/rg'))
        assert version == '14.1.1'

    @patch('subprocess.run')
    def test_get_current_version_failure(self, mock_run, temp_config_file):
        manager = ToolManager(temp_config_file)
        tool_config = manager.config.tools[0]

        mock_result = Mock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        version = manager._get_current_version(tool_config, Path('/tmp/rg'))
        assert version is None

    @patch('subprocess.run')
    def test_get_current_version_timeout(self, mock_run, temp_config_file):
        manager = ToolManager(temp_config_file)
        tool_config = manager.config.tools[0]

        mock_run.side_effect = subprocess.TimeoutExpired('cmd', 10)

        version = manager._get_current_version(tool_config, Path('/tmp/rg'))
        assert version is None

    def test_version_meets_requirement(self, temp_config_file):
        manager = ToolManager(temp_config_file)

        assert manager._version_meets_requirement('14.1.1', '13.0.0') is True
        assert manager._version_meets_requirement('12.9.9', '13.0.0') is False
        assert manager._version_meets_requirement('13.0.0', '13.0.0') is True

        # Test invalid version
        assert manager._version_meets_requirement('invalid', '13.0.0') is False

    @patch('ai_agents.tools.vendor_tools.vendor_tools.ToolManager._get_system_info')
    def test_build_download_url_global_template(self, mock_system_info, temp_config_file):
        manager = ToolManager(temp_config_file)
        mock_system_info.return_value = ('linux', 'amd64')

        tool_config = manager.config.tools[0]  # rg tool (no custom download_url)
        url = manager._build_download_url(tool_config)

        expected = 'https://example.com/rg/14.1.1/rg-linux-amd64'
        assert url == expected

    def test_build_download_url_custom(self, temp_config_file):
        manager = ToolManager(temp_config_file)

        tool_config = manager.config.tools[1]  # custom_tool with custom download_url
        url = manager._build_download_url(tool_config)

        assert url == 'https://custom.com/tool.bin'

    @patch('urllib.request.urlretrieve')
    @patch('pathlib.Path.chmod')
    def test_download_tool_success(self, mock_chmod, mock_urlretrieve, temp_config_file):
        manager = ToolManager(temp_config_file)

        mock_path = Mock()
        mock_path.name = 'test_tool'

        result = manager._download_tool('https://example.com/tool', mock_path)

        assert result is True
        mock_urlretrieve.assert_called_once_with('https://example.com/tool', mock_path)
        mock_path.chmod.assert_called_once_with(0o755)

    @patch('urllib.request.urlretrieve')
    def test_download_tool_failure(self, mock_urlretrieve, temp_config_file):
        manager = ToolManager(temp_config_file)
        mock_urlretrieve.side_effect = Exception('Download failed')

        mock_path = Mock()
        mock_path.name = 'test_tool'

        result = manager._download_tool('https://example.com/tool', mock_path)
        assert result is False

    def test_find_tool_config(self, temp_config_file):
        manager = ToolManager(temp_config_file)

        config = manager._find_tool_config('rg')
        assert config is not None
        assert config.name == 'rg'

        config = manager._find_tool_config('nonexistent')
        assert config is None

    @patch('ai_agents.tools.vendor_tools.vendor_tools.ToolManager._check_tool_exists')
    @patch('ai_agents.tools.vendor_tools.vendor_tools.ToolManager._get_current_version')
    @patch('ai_agents.tools.vendor_tools.vendor_tools.ToolManager._version_meets_requirement')
    def test_ensure_tool_already_available(self, mock_version_meets, mock_get_version,
                                         mock_check_exists, temp_config_file):
        manager = ToolManager(temp_config_file)

        mock_check_exists.return_value = True
        mock_get_version.return_value = '14.1.1'
        mock_version_meets.return_value = True

        result = manager.ensure_tool('rg')
        assert result is True

    @patch('ai_agents.tools.vendor_tools.vendor_tools.ToolManager._check_tool_exists')
    @patch('ai_agents.tools.vendor_tools.vendor_tools.ToolManager._download_tool')
    @patch('ai_agents.tools.vendor_tools.vendor_tools.ToolManager._build_download_url')
    @patch('ai_agents.tools.vendor_tools.vendor_tools.ToolManager._get_current_version')
    def test_ensure_tool_download_success(self, mock_get_version, mock_build_url,
                                        mock_download, mock_check_exists, temp_config_file):
        manager = ToolManager(temp_config_file)

        # First call: tool doesn't exist, second call: tool exists after download
        mock_check_exists.side_effect = [False, True]
        mock_build_url.return_value = 'https://example.com/rg'
        mock_download.return_value = True
        mock_get_version.return_value = '14.1.1'

        result = manager.ensure_tool('rg')
        assert result is True
        mock_download.assert_called_once()

    def test_ensure_tool_not_found(self, temp_config_file):
        manager = ToolManager(temp_config_file)

        result = manager.ensure_tool('nonexistent_tool')
        assert result is False

    @patch('ai_agents.tools.vendor_tools.vendor_tools.ToolManager.ensure_tool')
    def test_ensure_all_tools(self, mock_ensure_tool, temp_config_file):
        manager = ToolManager(temp_config_file)
        mock_ensure_tool.side_effect = [True, False]  # rg succeeds, custom_tool fails

        results = manager.ensure_all_tools()

        assert results == {'rg': True, 'custom_tool': False}
        assert mock_ensure_tool.call_count == 2

    @patch('ai_agents.tools.vendor_tools.vendor_tools.ToolManager._check_tool_exists')
    def test_get_tool_path_exists(self, mock_check_exists, temp_config_file):
        manager = ToolManager(temp_config_file)
        mock_check_exists.return_value = True

        path = manager.get_tool_path('rg')
        assert path == Path('/tmp/test_tools/rg')

    @patch('ai_agents.tools.vendor_tools.vendor_tools.ToolManager._check_tool_exists')
    def test_get_tool_path_not_exists(self, mock_check_exists, temp_config_file):
        manager = ToolManager(temp_config_file)
        mock_check_exists.return_value = False

        path = manager.get_tool_path('rg')
        assert path is None


class TestConvenienceFunctions:
    @patch('ai_agents.tools.vendor_tools.vendor_tools.ToolManager')
    def test_ensure_tool_function(self, mock_manager_class):
        mock_manager = Mock()
        mock_manager.ensure_tool.return_value = True
        mock_manager_class.return_value = mock_manager

        result = ensure_tool('test_tool', 'config.yaml')

        assert result is True
        mock_manager_class.assert_called_once_with('config.yaml')
        mock_manager.ensure_tool.assert_called_once_with('test_tool')

    @patch('ai_agents.tools.vendor_tools.vendor_tools.ToolManager')
    def test_ensure_all_tools_function(self, mock_manager_class):
        mock_manager = Mock()
        mock_manager.ensure_all_tools.return_value = {'tool1': True, 'tool2': False}
        mock_manager_class.return_value = mock_manager

        result = ensure_all_tools('config.yaml')

        assert result == {'tool1': True, 'tool2': False}
        mock_manager_class.assert_called_once_with('config.yaml')
        mock_manager.ensure_all_tools.assert_called_once()

    @patch('ai_agents.tools.vendor_tools.vendor_tools.ToolManager')
    def test_get_tool_path_function(self, mock_manager_class):
        mock_manager = Mock()
        mock_manager.get_tool_path.return_value = Path('/tmp/tool')
        mock_manager_class.return_value = mock_manager

        result = get_tool_path('test_tool', 'config.yaml')

        assert result == Path('/tmp/tool')
        mock_manager_class.assert_called_once_with('config.yaml')
        mock_manager.get_tool_path.assert_called_once_with('test_tool')

    @patch('ai_agents.tools.vendor_tools.vendor_tools.ToolManager')
    @patch.dict(os.environ, {'PATH': '/usr/bin:/bin'})
    def test_add_tools_to_path_new_path(self, mock_manager_class):
        mock_manager = Mock()
        mock_manager.download_dir = Path('/tmp/test_tools')
        mock_manager_class.return_value = mock_manager

        result = add_tools_to_path('config.yaml')

        expected_path = f"/tmp/test_tools{os.pathsep}/usr/bin:/bin"
        assert result == expected_path
        assert os.environ['PATH'] == expected_path
        mock_manager_class.assert_called_once_with('config.yaml')

    @patch('ai_agents.tools.vendor_tools.vendor_tools.ToolManager')
    @patch.dict(os.environ, {'PATH': '/tmp/test_tools:/usr/bin:/bin'})
    def test_add_tools_to_path_already_exists(self, mock_manager_class):
        mock_manager = Mock()
        mock_manager.download_dir = Path('/tmp/test_tools')
        mock_manager_class.return_value = mock_manager

        original_path = '/tmp/test_tools:/usr/bin:/bin'
        result = add_tools_to_path('config.yaml')

        assert result == original_path
        assert os.environ['PATH'] == original_path
        mock_manager_class.assert_called_once_with('config.yaml')

    @patch('ai_agents.tools.vendor_tools.vendor_tools.ToolManager')
    @patch.dict(os.environ, {}, clear=True)
    def test_add_tools_to_path_empty_path(self, mock_manager_class):
        mock_manager = Mock()
        mock_manager.download_dir = Path('/tmp/test_tools')
        mock_manager_class.return_value = mock_manager

        result = add_tools_to_path('config.yaml')

        expected_path = f"/tmp/test_tools{os.pathsep}"
        assert result == expected_path
        assert os.environ['PATH'] == expected_path
        mock_manager_class.assert_called_once_with('config.yaml')
