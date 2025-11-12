import logging
import subprocess
import shutil
from typing import List, Optional


def _check_tool_available(tool_name: str) -> bool:
    """Check if a command-line tool is available in the system PATH."""
    return shutil.which(tool_name) is not None


def _run_search_command(cmd: List[str], max_lines: Optional[int] = None) -> str:
    """Run a search command and return the output, optionally limited by max_lines."""
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30  # 30 second timeout to prevent hanging
        )

        # Handle different exit codes
        if result.returncode == 0:
            output = result.stdout
        elif result.returncode == 1:
            # No matches found (normal for grep-like tools)
            output = ""
        else:
            # Other error codes
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)

        # Limit output lines if specified
        if max_lines and max_lines > 0:
            lines = output.splitlines()
            if len(lines) > max_lines:
                limited_lines = lines[:max_lines]
                limited_lines.append(f"... (output truncated, showing first {max_lines} lines of {len(lines)} total)")
                output = "\n".join(limited_lines)

        return output

    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"Search command timed out: {' '.join(cmd)}") from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Search command failed: {' '.join(cmd)}\nError: {e.stderr}") from e


def search_keyword_in_directory(
    directory: str,
    keyword: str,
    max_output_lines: Optional[int] = 100,
    case_sensitive: bool = False,
    include_line_numbers: bool = True,
    file_extensions: Optional[List[str]] = None
) -> str:
    """
    Search for a keyword in a directory using the best available search tool.

    This function tries to use search tools in the following order of preference:
    1. ag (The Silver Searcher) - fastest and most feature-rich
    2. rg (ripgrep) - very fast and modern
    3. grep - standard Unix tool, available everywhere

    Args:
        directory (str): **REQUIRED** The directory path to search in
        keyword (str): **REQUIRED** The keyword/pattern to search for.
                      **SUPPORTS REGULAR EXPRESSIONS** - you can use regex patterns like:
                      - 'function.*name' for pattern matching
                      - '^import' for lines starting with 'import'
                      - 'TODO|FIXME' for multiple keywords
                      - '\\bclass\\b' for word boundaries
        max_output_lines: Maximum number of output lines to return (default: 100, None for unlimited)
        case_sensitive: Whether the search should be case-sensitive (default: False)
        include_line_numbers: Whether to include line numbers in output (default: True)
        file_extensions: Optional list of file extensions to search (e.g., ['.py', '.js', '.go'])

    Returns:
        str: Search results containing matched lines with file paths and line numbers

    Examples:
        >>> search_keyword_in_directory('/path/to/repo', 'function_name')
        >>> search_keyword_in_directory('/path/to/repo', 'TODO', max_output_lines=50)
        >>> search_keyword_in_directory('/path/to/repo', 'import', file_extensions=['.py'])
        >>> search_keyword_in_directory('/path/to/repo', '^class.*:', file_extensions=['.py'])  # regex example
        >>> search_keyword_in_directory('/path/to/repo', 'TODO|FIXME|XXX')  # multiple keywords
    """
    if not directory:
        raise ValueError("directory is required")
    if not keyword:
        raise ValueError("keyword is required")

    logging.info(f"Searching for '{keyword}' in directory: {directory}")

    # Build search command based on available tools
    cmd = []

    if _check_tool_available("ag"):
        # Use ag (The Silver Searcher)
        cmd = ["ag"]
        if not case_sensitive:
            cmd.append("-i")
        if include_line_numbers:
            cmd.append("--line-numbers")
        else:
            cmd.append("--no-line-number")

        # Add file extension filters if specified
        if file_extensions:
            for ext in file_extensions:
                # Remove leading dot if present
                ext_clean = ext.lstrip('.')
                cmd.extend(["-G", f"\\.{ext_clean}$"])

        cmd.extend([keyword, directory])

    elif _check_tool_available("rg"):
        # Use rg (ripgrep)
        cmd = ["rg"]
        if not case_sensitive:
            cmd.append("-i")
        if include_line_numbers:
            cmd.append("-n")
        else:
            cmd.append("--no-line-number")

        # Add file extension filters if specified
        if file_extensions:
            for ext in file_extensions:
                # Remove leading dot if present
                ext_clean = ext.lstrip('.')
                cmd.extend(["-g", f"*.{ext_clean}"])

        cmd.extend([keyword, directory])

    elif _check_tool_available("grep"):
        # Use standard grep
        cmd = ["grep", "-r", "-E"]  # Add -E for extended regex support
        if not case_sensitive:
            cmd.append("-i")
        if include_line_numbers:
            cmd.append("-n")

        # Add file extension filters if specified
        if file_extensions:
            for ext in file_extensions:
                # Remove leading dot if present
                ext_clean = ext.lstrip('.')
                cmd.extend(["--include", f"*.{ext_clean}"])

        cmd.extend([keyword, directory])

    else:
        raise RuntimeError("No search tool available. Please install ag, rg, or ensure grep is available.")

    logging.info(f"Running search command: {' '.join(cmd)}")

    try:
        result = _run_search_command(cmd, max_output_lines)

        if not result.strip():
            return f"No matches found for '{keyword}' in {directory}"

        return result

    except Exception as e:
        logging.error(f"Search failed: {e}")
        raise RuntimeError(f"Search failed: {e}") from e


def search_keyword_with_context(
    directory: str,
    keyword: str,
    context_lines: int = 3,
    max_output_lines: Optional[int] = 100,
    case_sensitive: bool = False,
    file_extensions: Optional[List[str]] = None
) -> str:
    """
    Search for a keyword in a directory with surrounding context lines.

    This function provides context around each match by showing lines before and after
    the matching line, which is useful for understanding the usage context.

    Args:
        directory (str): **REQUIRED** The directory path to search in
        keyword (str): **REQUIRED** The keyword/pattern to search for.
                      **SUPPORTS REGULAR EXPRESSIONS** - you can use regex patterns like:
                      - 'function.*name' for pattern matching
                      - '^import' for lines starting with 'import'
                      - 'TODO|FIXME' for multiple keywords
                      - '\\bclass\\b' for word boundaries
        context_lines: Number of lines to show before and after each match (default: 3)
        max_output_lines: Maximum number of output lines to return (default: 100, None for unlimited)
        case_sensitive: Whether the search should be case-sensitive (default: False)
        file_extensions: Optional list of file extensions to search (e.g., ['.py', '.js', '.go'])

    Returns:
        str: Search results with context lines around each match

    Examples:
        >>> search_keyword_with_context('/path/to/repo', 'function_name', context_lines=5)
        >>> search_keyword_with_context('/path/to/repo', 'TODO', context_lines=2, max_output_lines=50)
        >>> search_keyword_with_context('/path/to/repo', '^def .*:', context_lines=3, file_extensions=['.py'])  # regex example
        >>> search_keyword_with_context('/path/to/repo', 'error|exception|fail', context_lines=5)  # multiple keywords
    """
    if not directory:
        raise ValueError("directory is required")
    if not keyword:
        raise ValueError("keyword is required")
    if context_lines < 0:
        raise ValueError("context_lines must be non-negative")

    logging.info(f"Searching for '{keyword}' with {context_lines} context lines in directory: {directory}")

    # Build search command based on available tools
    cmd = []

    if _check_tool_available("ag"):
        # Use ag (The Silver Searcher)
        cmd = ["ag"]
        if not case_sensitive:
            cmd.append("-i")
        cmd.extend(["-A", str(context_lines), "-B", str(context_lines)])

        # Add file extension filters if specified
        if file_extensions:
            for ext in file_extensions:
                ext_clean = ext.lstrip('.')
                cmd.extend(["-G", f"\\.{ext_clean}$"])

        cmd.extend([keyword, directory])

    elif _check_tool_available("rg"):
        # Use rg (ripgrep)
        cmd = ["rg"]
        if not case_sensitive:
            cmd.append("-i")
        cmd.extend(["-A", str(context_lines), "-B", str(context_lines)])

        # Add file extension filters if specified
        if file_extensions:
            for ext in file_extensions:
                ext_clean = ext.lstrip('.')
                cmd.extend(["-g", f"*.{ext_clean}"])

        cmd.extend([keyword, directory])

    elif _check_tool_available("grep"):
        # Use standard grep
        cmd = ["grep", "-r", "-E"]  # Add -E for extended regex support
        if not case_sensitive:
            cmd.append("-i")
        cmd.extend(["-A", str(context_lines), "-B", str(context_lines)])
        cmd.append("-n")  # Always include line numbers for context

        # Add file extension filters if specified
        if file_extensions:
            include_patterns = []
            for ext in file_extensions:
                ext_clean = ext.lstrip('.')
                include_patterns.append(f"*.{ext_clean}")

            if include_patterns:
                for pattern in include_patterns:
                    cmd.extend(["--include", pattern])

        cmd.extend([keyword, directory])

    else:
        raise RuntimeError("No search tool available. Please install ag, rg, or ensure grep is available.")

    logging.info(f"Running context search command: {' '.join(cmd)}")

    try:
        result = _run_search_command(cmd, max_output_lines)

        if not result.strip():
            return f"No matches found for '{keyword}' in {directory}"

        return result

    except Exception as e:
        logging.error(f"Context search failed: {e}")
        raise RuntimeError(f"Context search failed: {e}") from e
