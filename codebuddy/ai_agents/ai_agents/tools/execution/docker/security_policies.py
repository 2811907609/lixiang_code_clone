"""Security policies for Docker sandbox execution."""

import logging
from typing import List
import re


class SecurityPolicy:
    """Security policy for validating commands in Docker sandbox."""

    def __init__(self,
                 allow_dangerous: bool = False,
                 enable_network_commands: bool = False,
                 custom_blocked_patterns: List[str] = None,
                 custom_allowed_patterns: List[str] = None):
        self.allow_dangerous = allow_dangerous
        self.enable_network_commands = enable_network_commands
        self.custom_blocked_patterns = custom_blocked_patterns or []
        self.custom_allowed_patterns = custom_allowed_patterns or []
        self.logger = logging.getLogger(__name__)

    def validate_command(self, command: str) -> None:
        """
        Validate command against security policy.

        Args:
            command: The command to validate

        Raises:
            ValueError: If command violates security policy
        """
        command_lower = command.lower().strip()

        # Check extremely dangerous commands (always blocked)
        self._check_extremely_dangerous(command_lower)

        # Check Docker-specific dangerous commands
        self._check_docker_dangerous(command_lower)

        # Check network commands if disabled
        if not self.enable_network_commands:
            self._check_network_commands(command_lower)

        # Check general dangerous commands if not allowed
        if not self.allow_dangerous:
            self._check_dangerous_commands(command_lower)

        # Check custom blocked patterns
        self._check_custom_blocked(command, command_lower)

        # Log the validation
        self.logger.debug(f"Command passed security validation: {command}")

    def _check_extremely_dangerous(self, command_lower: str) -> None:
        """Check for extremely dangerous commands that are never allowed."""
        extremely_dangerous = [
            'rm -rf /',
            'rm -rf /*',
            'dd if=/dev/zero',
            'dd if=/dev/random',
            'mkfs.',
            'fdisk',
            'format',
            ':(){ :|:& };:',  # Fork bomb
            'while true; do',  # Infinite loops
            'for((;;));',
            'cat /dev/zero',
            'cat /dev/random',
            '/dev/mem',
            '/dev/kmem',
            'chmod 777 /',
            'chown -R root /',
        ]

        for dangerous in extremely_dangerous:
            if dangerous in command_lower:
                raise ValueError(f"Command contains extremely dangerous pattern: '{dangerous}'. This command is never allowed in sandbox.")

    def _check_docker_dangerous(self, command_lower: str) -> None:
        """Check for Docker-specific dangerous commands."""
        docker_dangerous = [
            'docker run',
            'docker exec',
            'docker build',
            'docker commit',
            'docker push',
            'docker pull',
            'docker system',
            'docker volume',
            'docker network',
            'docker swarm',
            'docker service',
            'docker stack',
            'docker secret',
            'docker config',
            'systemctl',
            'service ',
            'mount ',
            'umount',
            'modprobe',
            'insmod',
            'rmmod',
            'iptables',
            'ip route',
            'ip link',
        ]

        for dangerous in docker_dangerous:
            if dangerous in command_lower:
                raise ValueError(f"Command contains Docker/system dangerous pattern: '{dangerous}'. Not allowed in sandbox.")

    def _check_network_commands(self, command_lower: str) -> None:
        """Check for network-related commands when network is disabled."""
        network_commands = [
            'curl',
            'wget',
            'nc ',
            'netcat',
            'telnet',
            'ssh',
            'scp',
            'rsync',
            'ftp',
            'sftp',
            'ping',
            'nslookup',
            'dig',
            'host ',
            'traceroute',
            'netstat',
            'ss ',
            'lsof -i',
        ]

        for net_cmd in network_commands:
            if net_cmd in command_lower:
                self.logger.warning(f"Network command detected but network is disabled: {net_cmd}")
                # Don't block, just warn, as the container has no network anyway

    def _check_dangerous_commands(self, command_lower: str) -> None:
        """Check for generally dangerous commands."""
        dangerous_patterns = [
            'rm -rf',
            'rm -r /',
            'sudo ',
            'su ',
            'chmod 777',
            'chmod -R 777',
            'chown -R',
            'kill -9',
            'killall',
            'pkill',
            'shutdown',
            'reboot',
            'halt',
            'init 0',
            'init 6',
            'poweroff',
            'mv / ',
            'cp -r / ',
            '> /dev/',
            'curl | sh',
            'wget | sh',
            'curl | bash',
            'wget | bash',
            'eval ',
            'exec ',
            'source /dev/',
            '. /dev/',
        ]

        for pattern in dangerous_patterns:
            if pattern in command_lower:
                raise ValueError(f"Command contains potentially dangerous pattern: '{pattern}'. "
                               f"Use allow_dangerous=True if you're sure this is safe.")

    def _check_custom_blocked(self, command: str, command_lower: str) -> None:
        """Check custom blocked patterns."""
        for pattern in self.custom_blocked_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                raise ValueError(f"Command matches custom blocked pattern: '{pattern}'")

    def get_safe_commands_help(self) -> str:
        """Get help text for safe commands."""
        return """
Safe commands in Docker sandbox:

File operations:
  - ls, cat, head, tail, find, grep, awk, sed
  - mkdir, touch, cp, mv (within allowed directories)
  - file, stat, du, df

Text processing:
  - sort, uniq, cut, tr, wc, diff
  - echo, printf

Programming:
  - python, node, go, java, gcc, make
  - pip install, npm install (if allowed)

System info:
  - ps, top, free, uname, whoami, id
  - env, printenv, which, type

Archive operations:
  - tar, gzip, gunzip, zip, unzip

Note: Network commands are disabled by default.
Dangerous system commands are blocked for security.
        """.strip()


# Predefined security policies
SECURITY_POLICIES = {
    "strict": SecurityPolicy(
        allow_dangerous=False,
        enable_network_commands=False
    ),

    "development": SecurityPolicy(
        allow_dangerous=False,
        enable_network_commands=True,
        custom_allowed_patterns=[
            r'pip install.*',
            r'npm install.*',
            r'go get.*',
            r'cargo install.*'
        ]
    ),

    "permissive": SecurityPolicy(
        allow_dangerous=True,
        enable_network_commands=True
    ),

    "readonly": SecurityPolicy(
        allow_dangerous=False,
        enable_network_commands=False,
        custom_blocked_patterns=[
            r'.*>\s*[^|].*',  # Block output redirection
            r'.*>>\s*[^|].*',  # Block append redirection
            r'rm\s+.*',       # Block all rm commands
            r'mv\s+.*',       # Block all mv commands
            r'cp\s+.*',       # Block all cp commands
        ]
    )
}


def get_security_policy(name: str) -> SecurityPolicy:
    """Get a predefined security policy by name."""
    if name not in SECURITY_POLICIES:
        available = ", ".join(SECURITY_POLICIES.keys())
        raise ValueError(f"Unknown security policy '{name}'. Available: {available}")

    return SECURITY_POLICIES[name]
