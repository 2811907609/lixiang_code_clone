"""Tests for security policies."""

import pytest

from ai_agents.tools.execution.docker.security_policies import (
    SecurityPolicy,
    get_security_policy,
    SECURITY_POLICIES
)


class TestSecurityPolicy:
    """Test SecurityPolicy functionality."""

    def test_default_initialization(self):
        """Test default initialization."""
        policy = SecurityPolicy()

        assert policy.allow_dangerous is False
        assert policy.enable_network_commands is False
        assert policy.custom_blocked_patterns == []
        assert policy.custom_allowed_patterns == []

    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        blocked_patterns = [r'rm\s+.*']
        allowed_patterns = [r'pip install.*']

        policy = SecurityPolicy(
            allow_dangerous=True,
            enable_network_commands=True,
            custom_blocked_patterns=blocked_patterns,
            custom_allowed_patterns=allowed_patterns
        )

        assert policy.allow_dangerous is True
        assert policy.enable_network_commands is True
        assert policy.custom_blocked_patterns == blocked_patterns
        assert policy.custom_allowed_patterns == allowed_patterns

    def test_validate_safe_command(self):
        """Test validation of safe commands."""
        policy = SecurityPolicy()

        # These should not raise
        policy.validate_command("echo 'hello'")
        policy.validate_command("ls -la")
        policy.validate_command("cat file.txt")
        policy.validate_command("python script.py")
        policy.validate_command("grep pattern file.txt")

    def test_validate_extremely_dangerous_commands(self):
        """Test validation blocks extremely dangerous commands."""
        policy = SecurityPolicy(allow_dangerous=True)  # Even with allow_dangerous=True

        dangerous_commands = [
            "rm -rf /",
            "rm -rf /*",
            "dd if=/dev/zero of=/dev/sda",
            "mkfs.ext4 /dev/sda",
            "fdisk /dev/sda",
            ":(){ :|:& };:"  # Fork bomb
        ]

        for cmd in dangerous_commands:
            with pytest.raises(ValueError, match="extremely dangerous pattern"):
                policy.validate_command(cmd)

    def test_validate_dangerous_commands_blocked(self):
        """Test validation blocks dangerous commands when allow_dangerous=False."""
        policy = SecurityPolicy(allow_dangerous=False)

        dangerous_commands = [
            "sudo rm file",
            "killall nginx",
            "shutdown now"
        ]

        for cmd in dangerous_commands:
            with pytest.raises(ValueError, match="potentially dangerous pattern"):
                policy.validate_command(cmd)

    def test_validate_dangerous_commands_allowed(self):
        """Test validation allows dangerous commands when allow_dangerous=True."""
        policy = SecurityPolicy(allow_dangerous=True)

        # These should not raise when allow_dangerous=True (avoid extremely dangerous ones)
        policy.validate_command("kill -9 1234")
        policy.validate_command("sudo ls")
        policy.validate_command("chmod 755 /tmp/file")

    def test_validate_network_commands_disabled(self):
        """Test network commands when network is disabled."""
        policy = SecurityPolicy(enable_network_commands=False)

        # These should not raise (just warn) even when network is disabled
        policy.validate_command("curl http://example.com")
        policy.validate_command("wget http://example.com")
        policy.validate_command("ping google.com")

    def test_validate_network_commands_enabled(self):
        """Test network commands when network is enabled."""
        policy = SecurityPolicy(enable_network_commands=True)

        # These should not raise when network is enabled
        policy.validate_command("curl http://example.com")
        policy.validate_command("wget http://example.com")
        policy.validate_command("ping google.com")

    def test_validate_docker_dangerous_commands(self):
        """Test validation blocks Docker-specific dangerous commands."""
        policy = SecurityPolicy()

        docker_dangerous = [
            "docker run ubuntu",
            "docker exec container cmd",
            "systemctl stop service",
            "mount /dev/sda1 /mnt",
            "modprobe module"
        ]

        for cmd in docker_dangerous:
            with pytest.raises(ValueError, match="Docker/system dangerous pattern"):
                policy.validate_command(cmd)

    def test_validate_custom_blocked_patterns(self):
        """Test custom blocked patterns."""
        policy = SecurityPolicy(custom_blocked_patterns=[r'forbidden.*'])

        with pytest.raises(ValueError, match="custom blocked pattern"):
            policy.validate_command("forbidden command")

        # This should be fine
        policy.validate_command("allowed command")

    def test_validate_injection_patterns_warning(self):
        """Test injection patterns generate warnings but don't block."""
        policy = SecurityPolicy()

        # These should not raise but may generate warnings
        policy.validate_command("echo 'test' && echo 'test2'")
        policy.validate_command("ls | grep pattern")
        policy.validate_command("echo $(date)")

    def test_validate_safe_injection_contexts(self):
        """Test safe contexts for injection patterns."""
        policy = SecurityPolicy()

        # These should not raise warnings due to safe contexts
        policy.validate_command("git log --oneline | head -10")
        policy.validate_command("find . -name '*.py' | wc -l")
        policy.validate_command("grep -r pattern . | awk '{print $1}'")

    def test_get_safe_commands_help(self):
        """Test getting safe commands help."""
        policy = SecurityPolicy()
        help_text = policy.get_safe_commands_help()

        assert isinstance(help_text, str)
        assert "Safe commands" in help_text
        assert "File operations" in help_text
        assert "Programming" in help_text


class TestPredefinedPolicies:
    """Test predefined security policies."""

    def test_predefined_policies_exist(self):
        """Test that predefined policies exist."""
        assert "strict" in SECURITY_POLICIES
        assert "development" in SECURITY_POLICIES
        assert "permissive" in SECURITY_POLICIES
        assert "readonly" in SECURITY_POLICIES

    def test_get_security_policy_strict(self):
        """Test getting strict security policy."""
        policy = get_security_policy("strict")

        assert isinstance(policy, SecurityPolicy)
        assert policy.allow_dangerous is False
        assert policy.enable_network_commands is False

    def test_get_security_policy_development(self):
        """Test getting development security policy."""
        policy = get_security_policy("development")

        assert isinstance(policy, SecurityPolicy)
        assert policy.allow_dangerous is False
        assert policy.enable_network_commands is True

    def test_get_security_policy_permissive(self):
        """Test getting permissive security policy."""
        policy = get_security_policy("permissive")

        assert isinstance(policy, SecurityPolicy)
        assert policy.allow_dangerous is True
        assert policy.enable_network_commands is True

    def test_get_security_policy_readonly(self):
        """Test getting readonly security policy."""
        policy = get_security_policy("readonly")

        assert isinstance(policy, SecurityPolicy)
        assert policy.allow_dangerous is False
        assert policy.enable_network_commands is False

        # Test that readonly policy blocks write operations
        with pytest.raises(ValueError):
            policy.validate_command("echo 'test' > file.txt")

        with pytest.raises(ValueError):
            policy.validate_command("rm file.txt")

    def test_get_security_policy_invalid(self):
        """Test getting invalid security policy."""
        with pytest.raises(ValueError, match="Unknown security policy"):
            get_security_policy("nonexistent")

    def test_readonly_policy_blocks_write_operations(self):
        """Test that readonly policy blocks various write operations."""
        policy = get_security_policy("readonly")

        write_commands = [
            "echo 'test' > file.txt",
            "echo 'test' >> file.txt",
            "rm file.txt",
            "mv file1.txt file2.txt",
            "cp file1.txt file2.txt"
        ]

        for cmd in write_commands:
            with pytest.raises(ValueError, match="custom blocked pattern"):
                policy.validate_command(cmd)

    def test_readonly_policy_allows_read_operations(self):
        """Test that readonly policy allows read operations."""
        policy = get_security_policy("readonly")

        read_commands = [
            "cat file.txt",
            "ls -la",
            "grep pattern file.txt",
            "head -10 file.txt",
            "tail -10 file.txt"
        ]

        for cmd in read_commands:
            policy.validate_command(cmd)  # Should not raise
