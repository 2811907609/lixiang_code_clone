"""Advanced command validation using bashlex AST parsing."""

import logging
import re
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Any
import bashlex
import bashlex.errors


class SecurityLevel(Enum):
    """Security levels for command validation."""
    SAFE = "safe"
    WARNING = "warning"
    DANGEROUS = "dangerous"
    BLOCKED = "blocked"


@dataclass
class ValidationResult:
    """Result of command validation."""
    is_safe: bool
    security_level: SecurityLevel
    violations: List[str]
    warnings: List[str]
    command: str
    parsed_ast: Optional[Any] = None


class CommandValidator:
    """
    Advanced command validator using bashlex for AST-based analysis.

    This validator provides more accurate security analysis by parsing
    command structure rather than relying on string matching.
    """

    def __init__(self, allow_dangerous_commands: bool = False):
        """
        Initialize the command validator.

        Args:
            allow_dangerous_commands: Whether to allow potentially dangerous commands
        """
        self.logger = logging.getLogger(__name__)
        self.allow_dangerous_commands = allow_dangerous_commands

        # Define security rules
        self._init_security_rules()

    def _init_security_rules(self):
        """Initialize security rules and patterns."""

        # Commands that are always blocked
        self.always_blocked_commands = {
            'rm': self._check_rm_command,
            'dd': self._check_dd_command,
            'mkfs': self._check_mkfs_command,
            'fdisk': self._check_fdisk_command,
            'format': self._check_format_command,
        }

        # Commands that are dangerous but may be allowed
        self.dangerous_commands = {
            'sudo': self._check_sudo_command,
            'chmod': self._check_chmod_command,
            'chown': self._check_chown_command,
            'kill': self._check_kill_command,
            'killall': self._check_killall_command,
            'shutdown': self._check_shutdown_command,
            'reboot': self._check_reboot_command,
            'halt': self._check_halt_command,
            'init': self._check_init_command,
            'systemctl': self._check_systemctl_command,
            'service': self._check_service_command,
            'mv': self._check_mv_command,
            'cp': self._check_cp_command,
        }

        # Network download patterns that could be dangerous
        self.download_patterns = [
            (r'curl.*\|.*sh', 'Piping curl output to shell'),
            (r'wget.*\|.*sh', 'Piping wget output to shell'),
            (r'curl.*\|.*bash', 'Piping curl output to bash'),
            (r'wget.*\|.*bash', 'Piping wget output to bash'),
        ]

        # Fork bomb patterns
        self.fork_bomb_patterns = [
            r':\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:',  # :(){ :|:& };:
            r'\.\/\$0.*&',  # ./$0 & variations
        ]

    def validate_command(self, command: str) -> ValidationResult:
        """
        Validate a command for security issues.

        Args:
            command: The shell command to validate

        Returns:
            ValidationResult with safety assessment
        """
        command = command.strip()
        violations = []
        warnings = []
        security_level = SecurityLevel.SAFE

        try:
            # Parse the command using bashlex
            parsed_ast = bashlex.parse(command)

            # Analyze the AST for security issues
            for ast_node in parsed_ast:
                node_violations, node_warnings, node_level = self._analyze_ast_node(ast_node, command)
                violations.extend(node_violations)
                warnings.extend(node_warnings)

                # Update security level (take the most severe)
                if node_level.value == SecurityLevel.BLOCKED.value:
                    security_level = SecurityLevel.BLOCKED
                elif node_level.value == SecurityLevel.DANGEROUS.value and security_level != SecurityLevel.BLOCKED:
                    security_level = SecurityLevel.DANGEROUS
                elif node_level.value == SecurityLevel.WARNING.value and security_level == SecurityLevel.SAFE:
                    security_level = SecurityLevel.WARNING

            # Check for additional regex-based patterns
            regex_violations, regex_warnings, regex_level = self._check_regex_patterns(command)
            violations.extend(regex_violations)
            warnings.extend(regex_warnings)

            if regex_level.value == SecurityLevel.BLOCKED.value:
                security_level = SecurityLevel.BLOCKED
            elif regex_level.value == SecurityLevel.DANGEROUS.value and security_level != SecurityLevel.BLOCKED:
                security_level = SecurityLevel.DANGEROUS
            elif regex_level.value == SecurityLevel.WARNING.value and security_level == SecurityLevel.SAFE:
                security_level = SecurityLevel.WARNING

            # Determine if command is safe
            is_safe = self._determine_safety(security_level, violations)

            return ValidationResult(
                is_safe=is_safe,
                security_level=security_level,
                violations=violations,
                warnings=warnings,
                command=command,
                parsed_ast=parsed_ast
            )

        except bashlex.errors.ParsingError as e:
            # If parsing fails, fall back to basic validation
            self.logger.warning(f"Failed to parse command with bashlex: {e}")
            return self._fallback_validation(command)

        except Exception as e:
            self.logger.error(f"Unexpected error during command validation: {e}")
            # In case of error, be conservative and block
            return ValidationResult(
                is_safe=False,
                security_level=SecurityLevel.BLOCKED,
                violations=[f"Validation error: {e}"],
                warnings=[],
                command=command
            )

    def _analyze_ast_node(self, node: Any, full_command: str) -> tuple[List[str], List[str], SecurityLevel]:
        """Analyze a single AST node for security issues."""
        violations = []
        warnings = []
        security_level = SecurityLevel.SAFE

        if node.kind == 'command':
            # Extract command name and arguments
            parts = []
            for part in node.parts:
                if part.kind == 'word':
                    parts.append(part.word)

            if parts:
                cmd_name = parts[0]
                cmd_args = parts[1:] if len(parts) > 1 else []

                # Check against security rules
                cmd_violations, cmd_warnings, cmd_level = self._check_command_security(
                    cmd_name, cmd_args, full_command
                )
                violations.extend(cmd_violations)
                warnings.extend(cmd_warnings)
                security_level = cmd_level

        elif node.kind == 'pipeline':
            # Check for dangerous pipeline patterns
            pipeline_violations, pipeline_warnings, pipeline_level = self._check_pipeline_security(node, full_command)
            violations.extend(pipeline_violations)
            warnings.extend(pipeline_warnings)
            if pipeline_level.value != SecurityLevel.SAFE.value:
                security_level = pipeline_level

        elif node.kind == 'list':
            # Recursively check list components
            for child in node.parts:
                if hasattr(child, 'kind'):
                    child_violations, child_warnings, child_level = self._analyze_ast_node(child, full_command)
                    violations.extend(child_violations)
                    warnings.extend(child_warnings)
                    if child_level.value != SecurityLevel.SAFE.value:
                        security_level = child_level

        # Check for redirections
        if hasattr(node, 'parts'):
            for part in node.parts:
                if hasattr(part, 'kind') and part.kind == 'redirect':
                    redir_violations, redir_warnings, redir_level = self._check_redirection_security(part)
                    violations.extend(redir_violations)
                    warnings.extend(redir_warnings)
                    if redir_level.value != SecurityLevel.SAFE.value:
                        security_level = redir_level

        return violations, warnings, security_level

    def _check_command_security(self, cmd_name: str, cmd_args: List[str], full_command: str) -> tuple[List[str], List[str], SecurityLevel]:
        """Check security for a specific command."""
        violations = []
        warnings = []
        security_level = SecurityLevel.SAFE

        # Check always blocked commands
        blocked = False
        if cmd_name in self.always_blocked_commands:
            check_func = self.always_blocked_commands[cmd_name]
            is_dangerous, reason = check_func(cmd_args, full_command)
            if is_dangerous:
                violations.append(f"Blocked command '{cmd_name}': {reason}")
                security_level = SecurityLevel.BLOCKED
                blocked = True

        # Check for commands that start with blocked prefixes (like mkfs.*)
        if not blocked:
            for blocked_cmd in self.always_blocked_commands:
                if cmd_name.startswith(blocked_cmd + '.') or cmd_name.startswith(blocked_cmd + '_'):
                    check_func = self.always_blocked_commands[blocked_cmd]
                    is_dangerous, reason = check_func(cmd_args, full_command)
                    if is_dangerous:
                        violations.append(f"Blocked command '{cmd_name}': {reason}")
                        security_level = SecurityLevel.BLOCKED
                        blocked = True
                        break

        # Check dangerous commands
        if not blocked and cmd_name in self.dangerous_commands:
            check_func = self.dangerous_commands[cmd_name]
            is_dangerous, reason = check_func(cmd_args, full_command)
            if is_dangerous:
                if self.allow_dangerous_commands:
                    warnings.append(f"Dangerous command '{cmd_name}': {reason}")
                    security_level = SecurityLevel.WARNING
                else:
                    violations.append(f"Dangerous command '{cmd_name}': {reason}")
                    security_level = SecurityLevel.DANGEROUS

        return violations, warnings, security_level

    def _check_pipeline_security(self, pipeline_node: Any, full_command: str) -> tuple[List[str], List[str], SecurityLevel]:
        """Check security issues in command pipelines."""
        violations = []
        warnings = []
        security_level = SecurityLevel.SAFE

        # Extract pipeline parts
        parts = []
        for part in pipeline_node.parts:
            if part.kind == 'command':
                cmd_parts = []
                for cmd_part in part.parts:
                    if cmd_part.kind == 'word':
                        cmd_parts.append(cmd_part.word)
                if cmd_parts:
                    parts.append(cmd_parts[0])

        # Check for dangerous download-to-shell patterns
        if len(parts) >= 2:
            first_cmd = parts[0].lower()
            if first_cmd in ['curl', 'wget']:
                # Look for shell execution in pipeline
                for cmd in parts[1:]:
                    if cmd.lower() in ['sh', 'bash', 'zsh', 'fish']:
                        violations.append("Dangerous pattern: downloading and executing remote content")
                        security_level = SecurityLevel.BLOCKED
                        break

        return violations, warnings, security_level

    def _check_redirection_security(self, redirect_node: Any) -> tuple[List[str], List[str], SecurityLevel]:
        """Check security issues in redirections."""
        violations = []
        warnings = []
        security_level = SecurityLevel.SAFE

        # Check for dangerous redirection targets
        if hasattr(redirect_node, 'output'):
            target = redirect_node.output.word if hasattr(redirect_node.output, 'word') else str(redirect_node.output)

            if target.startswith('/dev/'):
                if target in ['/dev/sda', '/dev/sdb', '/dev/hda', '/dev/hdb']:
                    violations.append(f"Dangerous redirection to disk device: {target}")
                    security_level = SecurityLevel.BLOCKED
                elif target == '/dev/null':
                    warnings.append("Redirection to /dev/null (data will be discarded)")
                    security_level = SecurityLevel.WARNING

        return violations, warnings, security_level

    def _check_regex_patterns(self, command: str) -> tuple[List[str], List[str], SecurityLevel]:
        """Check command against regex patterns."""
        violations = []
        warnings = []
        security_level = SecurityLevel.SAFE

        # Check for fork bombs
        for pattern in self.fork_bomb_patterns:
            if re.search(pattern, command):
                violations.append("Fork bomb pattern detected")
                security_level = SecurityLevel.BLOCKED
                break

        # Check dangerous download patterns
        for pattern, description in self.download_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                violations.append(f"Dangerous pattern: {description}")
                security_level = SecurityLevel.BLOCKED
                break

        return violations, warnings, security_level

    def _determine_safety(self, security_level: SecurityLevel, violations: List[str]) -> bool:
        """Determine if command is safe based on security level and violations."""
        if security_level == SecurityLevel.BLOCKED:
            return False
        elif security_level == SecurityLevel.DANGEROUS and not self.allow_dangerous_commands:
            return False
        elif violations:
            return False
        return True

    def _fallback_validation(self, command: str) -> ValidationResult:
        """Fallback validation when bashlex parsing fails."""
        violations = []
        warnings = []
        security_level = SecurityLevel.SAFE

        # Basic string-based checks as fallback
        command_lower = command.lower().strip()

        # Check for extremely dangerous patterns
        extremely_dangerous = [
            'rm -rf /',
            'rm -rf /*',
            'dd if=/dev/zero',
            'mkfs.',
            ':(){ :|:& };:',
        ]

        for dangerous in extremely_dangerous:
            if dangerous in command_lower:
                violations.append(f"Extremely dangerous pattern detected: {dangerous}")
                security_level = SecurityLevel.BLOCKED
                break

        is_safe = len(violations) == 0

        return ValidationResult(
            is_safe=is_safe,
            security_level=security_level,
            violations=violations,
            warnings=warnings,
            command=command
        )

    # Command-specific check methods
    def _check_rm_command(self, args: List[str], full_command: str) -> tuple[bool, str]:
        """Check rm command for dangerous usage."""
        args_str = ' '.join(args).lower()

        # Always dangerous patterns
        if '-rf /' in args_str or '-rf /*' in args_str or 'rf /' in args_str:
            return True, "attempting to delete root filesystem"

        # Check for recursive deletion of important directories
        dangerous_paths = ['/usr', '/var', '/etc', '/home', '/opt', '/bin', '/sbin']
        if '-rf' in args_str or '-r' in args_str:
            for path in dangerous_paths:
                if path in args_str:
                    return True, f"recursive deletion of system directory: {path}"

        return False, ""

    def _check_dd_command(self, args: List[str], full_command: str) -> tuple[bool, str]:
        """Check dd command for dangerous usage."""
        args_str = ' '.join(args).lower()

        if 'if=/dev/zero' in args_str:
            return True, "writing zeros to potentially dangerous target"

        # Check for writing to disk devices
        disk_patterns = ['/dev/sd', '/dev/hd', '/dev/nvme']
        for pattern in disk_patterns:
            if f'of={pattern}' in args_str:
                return True, "writing to disk device"

        return False, ""

    def _check_mkfs_command(self, args: List[str], full_command: str) -> tuple[bool, str]:
        """Check mkfs command."""
        return True, "filesystem creation command"

    def _check_fdisk_command(self, args: List[str], full_command: str) -> tuple[bool, str]:
        """Check fdisk command."""
        return True, "disk partitioning command"

    def _check_format_command(self, args: List[str], full_command: str) -> tuple[bool, str]:
        """Check format command."""
        return True, "disk formatting command"

    def _check_sudo_command(self, args: List[str], full_command: str) -> tuple[bool, str]:
        """Check sudo command usage."""
        if not args:
            return False, ""

        # Check what command is being run with sudo
        sudo_cmd = args[0] if args else ""
        if sudo_cmd in ['rm', 'dd', 'mkfs', 'fdisk', 'format']:
            return True, f"running dangerous command '{sudo_cmd}' with elevated privileges"

        return True, "elevated privilege execution"

    def _check_chmod_command(self, args: List[str], full_command: str) -> tuple[bool, str]:
        """Check chmod command."""
        args_str = ' '.join(args)

        if '777' in args_str:
            return True, "setting dangerous file permissions (777)"

        return False, ""

    def _check_chown_command(self, args: List[str], full_command: str) -> tuple[bool, str]:
        """Check chown command."""
        args_str = ' '.join(args)

        if '-R' in args_str or '-r' in args_str:
            return True, "recursive ownership change"

        return False, ""

    def _check_kill_command(self, args: List[str], full_command: str) -> tuple[bool, str]:
        """Check kill command."""
        args_str = ' '.join(args)

        if '-9' in args_str:
            return True, "force killing processes"

        return False, ""

    def _check_killall_command(self, args: List[str], full_command: str) -> tuple[bool, str]:
        """Check killall command."""
        return True, "killing all processes by name"

    def _check_shutdown_command(self, args: List[str], full_command: str) -> tuple[bool, str]:
        """Check shutdown command."""
        return True, "system shutdown"

    def _check_reboot_command(self, args: List[str], full_command: str) -> tuple[bool, str]:
        """Check reboot command."""
        return True, "system reboot"

    def _check_halt_command(self, args: List[str], full_command: str) -> tuple[bool, str]:
        """Check halt command."""
        return True, "system halt"

    def _check_init_command(self, args: List[str], full_command: str) -> tuple[bool, str]:
        """Check init command."""
        args_str = ' '.join(args)

        if '0' in args_str:
            return True, "system shutdown via init 0"
        elif '6' in args_str:
            return True, "system reboot via init 6"

        return False, ""

    def _check_systemctl_command(self, args: List[str], full_command: str) -> tuple[bool, str]:
        """Check systemctl command."""
        if not args:
            return False, ""

        action = args[0].lower()
        if action in ['stop', 'disable', 'mask']:
            return True, f"systemctl {action} - potentially disruptive system service operation"

        return False, ""

    def _check_service_command(self, args: List[str], full_command: str) -> tuple[bool, str]:
        """Check service command."""
        args_str = ' '.join(args).lower()

        if 'stop' in args_str:
            return True, "stopping system service"

        return False, ""

    def _check_mv_command(self, args: List[str], full_command: str) -> tuple[bool, str]:
        """Check mv command."""
        args_str = ' '.join(args)

        # Check for moving system directories
        dangerous_paths = ['/usr', '/var', '/etc', '/bin', '/sbin']
        for path in dangerous_paths:
            if path in args_str:
                return True, f"moving system directory: {path}"

        return False, ""

    def _check_cp_command(self, args: List[str], full_command: str) -> tuple[bool, str]:
        """Check cp command."""
        args_str = ' '.join(args)

        # Check for recursive copying of large system directories
        if '-r' in args_str.lower() or '-R' in args_str:
            dangerous_paths = ['/usr', '/var', '/etc']
            for path in dangerous_paths:
                if path in args_str:
                    return True, f"recursive copying of system directory: {path}"

        return False, ""
