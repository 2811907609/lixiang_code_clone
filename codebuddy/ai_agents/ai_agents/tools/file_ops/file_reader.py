import logging
from pathlib import Path
from typing import Optional
from commonlibs.encoding.detect_content_encoding import detect_file_encoding

def read_file_content(
    file_path: str,
    encoding: str = "auto",
    max_size_mb: float = 10.0,
    strip_whitespace: bool = False,
    normalize_line_endings: bool = False,
    # auto_outline_threshold_kb: float = 50.0
    auto_outline_threshold_kb: float = 100.0
) -> str:
    """
    Read and return the complete content of a file, or an outline for large files.

    This tool reads a file and returns its content as a string. For files larger than
    the auto_outline_threshold_kb, it automatically returns a structural outline instead
    of the full content to make large files more manageable.

    Args:
        file_path: Path to the file to read (relative or absolute)
        encoding: File encoding to use. Use "auto" for automatic detection (default: auto)
        max_size_mb: Maximum file size in MB to read (default: 10.0)
        strip_whitespace: Whether to strip leading/trailing whitespace (default: False)
        normalize_line_endings: Whether to normalize line endings to \\n (default: False)
        auto_outline_threshold_kb: File size in KB above which to return outline instead of content (default: 50.0)

    Returns:
        str: The content of the file, or a structural outline for large files

    Raises:
        ValueError: If parameters are invalid
        FileNotFoundError: If the file doesn't exist
        PermissionError: If insufficient permissions to read file
        OSError: If there's an error reading the file
        UnicodeDecodeError: If the file cannot be decoded with the specified encoding

    Examples:
        >>> read_file_content("config.py")  # Returns full content for small files
        >>> read_file_content("data.txt", encoding="utf-8")
        >>> read_file_content("large_file.py")  # Returns outline for files > 50KB
        >>> read_file_content("huge_file.log", auto_outline_threshold_kb=100.0)  # Custom threshold
    """
    # Validate inputs
    if not file_path or not file_path.strip():
        raise ValueError("file_path is required and cannot be empty")

    if max_size_mb <= 0:
        raise ValueError("max_size_mb must be positive")

    if auto_outline_threshold_kb < 0:
        raise ValueError("auto_outline_threshold_kb must be non-negative")

    # Convert to Path object
    path = Path(file_path)

    # Check if file exists
    if not path.exists():
        raise FileNotFoundError(f"File '{file_path}' does not exist")

    if not path.is_file():
        raise ValueError(f"Path '{file_path}' is not a file")

    try:
        # Check file size
        file_size = path.stat().st_size
        max_size_bytes = max_size_mb * 1024 * 1024
        outline_threshold_bytes = auto_outline_threshold_kb * 1024

        if file_size > max_size_bytes:
            raise ValueError(f"File '{file_path}' is too large ({file_size / 1024 / 1024:.2f} MB). "
                           f"Maximum allowed size is {max_size_mb} MB.")

        # Determine encoding
        if encoding == "auto":
            detected_encoding = detect_file_encoding(path)
            actual_encoding = detected_encoding or "utf-8"
        else:
            actual_encoding = encoding

        # Check if file is large enough to warrant outline instead of full content
        if auto_outline_threshold_kb > 0 and file_size > outline_threshold_bytes:
            # Import and use the file outliner for large files
            from .file_outliner import get_file_outline

            outline_result = get_file_outline(
                file_path=file_path,
                detail_level="detailed",
                encoding=actual_encoding,
                include_line_numbers=True,
                max_items_per_section=30
            )

            # Add a note about why outline was returned
            size_kb = file_size / 1024
            note = (f"\n{'='*60}\n"
                   f"NOTE: File is {size_kb:.1f} KB (> {auto_outline_threshold_kb} KB threshold).\n"
                   f"Returning structural outline instead of full content.\n"
                   f"Use read_file_lines() to read specific sections, or\n"
                   f"increase auto_outline_threshold_kb parameter to get full content.\n"
                   f"{'='*60}")

            logging.info(f"Returned outline for large file: {path} ({file_size} bytes, encoding: {actual_encoding})")
            return outline_result + note

        # Read the file normally for smaller files
        with open(path, 'r', encoding=actual_encoding) as f:
            content = f.read()

        # Apply transformations if requested
        if strip_whitespace:
            content = content.strip()

        if normalize_line_endings:
            content = content.replace('\r\n', '\n').replace('\r', '\n')

        # Log the operation
        logging.info(f"Read file: {path} ({file_size} bytes, encoding: {actual_encoding})")

        return content

    except PermissionError as e:
        error_msg = f"Permission denied when reading file '{file_path}': {e}"
        logging.error(error_msg)
        raise PermissionError(error_msg) from e

    except OSError as e:
        error_msg = f"Failed to read file '{file_path}': {e}"
        logging.error(error_msg)
        raise OSError(error_msg) from e

    except UnicodeDecodeError as e:
        error_msg = f"Encoding error when reading file '{file_path}' with encoding '{actual_encoding}': {e}"
        logging.error(error_msg)
        raise UnicodeDecodeError(e.encoding, e.object, e.start, e.end, error_msg) from e


def read_file_lines(
    file_path: str,
    start_line: int = 1,
    end_line: Optional[int] = None,
    encoding: str = "auto",
    include_line_numbers: bool = False,
    strip_whitespace: bool = False
) -> str:
    """
    Read specific lines or line ranges from a file.

    This tool reads a portion of a file by line numbers, which is useful for
    large files or when you only need specific sections.

    Args:
        file_path: Path to the file to read (relative or absolute)
        start_line: Starting line number (1-based, default: 1)
        end_line: Ending line number (1-based, inclusive). None means read to end (default: None)
        encoding: File encoding to use. Use "auto" for automatic detection (default: auto)
        include_line_numbers: Whether to include line numbers in output (default: False)
        strip_whitespace: Whether to strip whitespace from each line (default: False)

    Returns:
        str: The requested lines from the file

    Raises:
        ValueError: If parameters are invalid
        FileNotFoundError: If the file doesn't exist
        PermissionError: If insufficient permissions to read file
        OSError: If there's an error reading the file

    Examples:
        >>> read_file_lines("app.py", 1, 50)  # First 50 lines
        >>> read_file_lines("log.txt", 100)   # From line 100 to end
        >>> read_file_lines("code.py", 10, 20, include_line_numbers=True)
    """
    # Validate inputs
    if not file_path or not file_path.strip():
        raise ValueError("file_path is required and cannot be empty")

    if start_line < 1:
        raise ValueError("start_line must be >= 1")

    if end_line is not None and end_line < start_line:
        raise ValueError("end_line must be >= start_line")

    # Convert to Path object
    path = Path(file_path)

    # Check if file exists
    if not path.exists():
        raise FileNotFoundError(f"File '{file_path}' does not exist")

    if not path.is_file():
        raise ValueError(f"Path '{file_path}' is not a file")

    try:
        # Determine encoding
        if encoding == "auto":
            detected_encoding = detect_file_encoding(path)
            actual_encoding = detected_encoding or "utf-8"
        else:
            actual_encoding = encoding

        # Read the file lines
        with open(path, 'r', encoding=actual_encoding) as f:
            lines = f.readlines()

        total_lines = len(lines)

        # Validate line numbers against actual file content
        if start_line > total_lines:
            return f"File '{file_path}' only has {total_lines} lines. Cannot read from line {start_line}."

        # Adjust end_line if necessary
        actual_end_line = min(end_line or total_lines, total_lines)

        # Extract the requested lines (convert to 0-based indexing)
        selected_lines = lines[start_line - 1:actual_end_line]

        # Apply transformations
        if strip_whitespace:
            selected_lines = [line.strip() for line in selected_lines]

        # Format output
        if include_line_numbers:
            formatted_lines = []
            for i, line in enumerate(selected_lines, start=start_line):
                # Remove trailing newline for consistent formatting
                clean_line = line.rstrip('\n\r')
                formatted_lines.append(f"{i:4d}: {clean_line}")
            result = '\n'.join(formatted_lines)
        else:
            # Join lines, preserving original line endings
            result = ''.join(selected_lines)
            # Remove final newline if it was added by join
            if result.endswith('\n') and not lines[-1].endswith('\n'):
                result = result.rstrip('\n')

        # Log the operation
        lines_read = actual_end_line - start_line + 1
        logging.info(f"Read lines {start_line}-{actual_end_line} from {path} ({lines_read} lines)")

        return result

    except PermissionError as e:
        error_msg = f"Permission denied when reading file '{file_path}': {e}"
        logging.error(error_msg)
        raise PermissionError(error_msg) from e

    except OSError as e:
        error_msg = f"Failed to read file '{file_path}': {e}"
        logging.error(error_msg)
        raise OSError(error_msg) from e

    except UnicodeDecodeError as e:
        error_msg = f"Encoding error when reading file '{file_path}' with encoding '{actual_encoding}': {e}"
        logging.error(error_msg)
        raise UnicodeDecodeError(e.encoding, e.object, e.start, e.end, error_msg) from e


def get_file_info(
    file_path: str,
    include_encoding_detection: bool = True,
    include_line_count: bool = True,
    include_content_preview: bool = False,
    preview_lines: int = 5
) -> str:
    """
    Get detailed information about a file.

    This tool provides comprehensive metadata about a file including size,
    modification time, encoding, line count, and optionally a content preview.

    Args:
        file_path: Path to the file to analyze (relative or absolute)
        include_encoding_detection: Whether to detect and report file encoding (default: True)
        include_line_count: Whether to count lines in the file (default: True)
        include_content_preview: Whether to include a preview of file content (default: False)
        preview_lines: Number of lines to include in preview (default: 5)

    Returns:
        str: Formatted information about the file

    Raises:
        ValueError: If parameters are invalid
        FileNotFoundError: If the file doesn't exist
        PermissionError: If insufficient permissions to read file
        OSError: If there's an error accessing the file

    Examples:
        >>> get_file_info("config.py")
        >>> get_file_info("data.txt", include_content_preview=True, preview_lines=10)
        >>> get_file_info("binary_file.exe", include_encoding_detection=False)
    """
    # Validate inputs
    if not file_path or not file_path.strip():
        raise ValueError("file_path is required and cannot be empty")

    if preview_lines < 0:
        raise ValueError("preview_lines must be non-negative")

    # Convert to Path object
    path = Path(file_path)

    # Check if file exists
    if not path.exists():
        raise FileNotFoundError(f"File '{file_path}' does not exist")

    if not path.is_file():
        raise ValueError(f"Path '{file_path}' is not a file")

    try:
        # Get basic file stats
        stat = path.stat()
        file_size = stat.st_size
        modified_time = stat.st_mtime

        # Format file size
        if file_size < 1024:
            size_str = f"{file_size} bytes"
        elif file_size < 1024 * 1024:
            size_str = f"{file_size / 1024:.1f} KB"
        elif file_size < 1024 * 1024 * 1024:
            size_str = f"{file_size / (1024 * 1024):.1f} MB"
        else:
            size_str = f"{file_size / (1024 * 1024 * 1024):.1f} GB"

        # Format modification time
        import datetime
        mod_time_str = datetime.datetime.fromtimestamp(modified_time).strftime("%Y-%m-%d %H:%M:%S")

        # Start building the info string
        info_lines = [
            f"File: {file_path}",
            f"Size: {size_str} ({file_size:,} bytes)",
            f"Modified: {mod_time_str}",
            f"Permissions: {oct(stat.st_mode)[-3:]}"
        ]

        # Detect encoding if requested
        detected_encoding = None
        if include_encoding_detection:
            detected_encoding = detect_file_encoding(path)
            if detected_encoding:
                info_lines.append(f"Detected encoding: {detected_encoding}")
            else:
                info_lines.append("Detected encoding: Unable to detect")

        # Count lines if requested
        line_count = None
        if include_line_count and file_size > 0:
            try:
                encoding_to_use = detected_encoding or "utf-8"
                with open(path, 'r', encoding=encoding_to_use, errors='ignore') as f:
                    line_count = sum(1 for _ in f)
                info_lines.append(f"Line count: {line_count:,}")
            except Exception as e:
                info_lines.append(f"Line count: Unable to count ({e})")

        # Add content preview if requested
        if include_content_preview and file_size > 0 and preview_lines > 0:
            try:
                encoding_to_use = detected_encoding or "utf-8"
                with open(path, 'r', encoding=encoding_to_use, errors='ignore') as f:
                    preview_content = []
                    for i, line in enumerate(f):
                        if i >= preview_lines:
                            break
                        # Remove trailing newline and limit line length
                        clean_line = line.rstrip('\n\r')
                        if len(clean_line) > 100:
                            clean_line = clean_line[:97] + "..."
                        preview_content.append(f"  {i+1:2d}: {clean_line}")

                if preview_content:
                    info_lines.append(f"\nContent preview (first {len(preview_content)} lines):")
                    info_lines.extend(preview_content)
                    if line_count and len(preview_content) < line_count:
                        info_lines.append(f"  ... ({line_count - len(preview_content)} more lines)")

            except Exception as e:
                info_lines.append(f"Content preview: Unable to read ({e})")

        # Log the operation
        logging.info(f"Retrieved file info: {path}")

        return '\n'.join(info_lines)

    except PermissionError as e:
        error_msg = f"Permission denied when accessing file '{file_path}': {e}"
        logging.error(error_msg)
        raise PermissionError(error_msg) from e

    except OSError as e:
        error_msg = f"Failed to access file '{file_path}': {e}"
        logging.error(error_msg)
        raise OSError(error_msg) from e
