import logging
import re
import os
from pathlib import Path
from typing import Tuple, Set, Optional


def extract_coverity_compile_info(
    compile_info_txtpath: str,
    encoding: str = "auto",
    max_size_mb: float = 100.0
) -> Tuple[str, bool]:
    """
    Extract effective compilation information from Coverity compile logs.

    This tool analyzes Coverity compilation logs to determine compilation success/failure
    and extracts unique failure chain logs while removing repetitive compilation messages.

    Args:
        compile_info_txtpath: Path to the compilation log text file (relative or absolute)
        encoding: File encoding to use. Use "auto" for automatic detection (default: auto)
        max_size_mb: Maximum file size in MB to read (default: 100.0)

    Returns:
        Tuple[str, bool]: A tuple containing:
            - info_txt: Extracted effective compilation information
            - bool_compile_ok: Whether compilation was successful

    Raises:
        ValueError: If parameters are invalid
        FileNotFoundError: If the file doesn't exist
        PermissionError: If insufficient permissions to read file
        OSError: If there's an error reading the file
        UnicodeDecodeError: If the file cannot be decoded with the specified encoding

    Examples:
        >>> info, success = extract_coverity_compile_info("/path/to/compile.log")
        >>> if success:
        ...     print("Compilation successful")
        ... else:
        ...     print(f"Compilation failed:\\n{info}")
    """
    # Validate inputs
    if not compile_info_txtpath or not compile_info_txtpath.strip():
        raise ValueError("compile_info_txtpath is required and cannot be empty")

    if max_size_mb <= 0:
        raise ValueError("max_size_mb must be positive")

    if len(compile_info_txtpath)<10000 and os.path.exists(compile_info_txtpath):


        # Convert to Path object
        path = Path(compile_info_txtpath)

        # Check if file exists
        if not path.exists():
            raise FileNotFoundError(f"File '{compile_info_txtpath}' does not exist")

        if not path.is_file():
            raise ValueError(f"Path '{compile_info_txtpath}' is not a file")

        try:
            # Check file size
            file_size = path.stat().st_size
            max_size_bytes = max_size_mb * 1024 * 1024

            if file_size > max_size_bytes:
                raise ValueError(f"File '{compile_info_txtpath}' is too large ({file_size / 1024 / 1024:.2f} MB). "
                            f"Maximum allowed size is {max_size_mb} MB.")

            # Determine encoding
            if encoding == "auto":
                detected_encoding = _detect_file_encoding(path)
                actual_encoding = detected_encoding or "utf-8"
            else:
                actual_encoding = encoding
            # Read the file
            with open(path, 'r', encoding=actual_encoding, errors='replace') as f:
                content = f.read()
        except PermissionError as e:
            error_msg = f"Permission denied when reading file '{compile_info_txtpath}': {e}"
            logging.error(error_msg)
            raise PermissionError(error_msg) from e
        except OSError as e:
            error_msg = f"Failed to read file '{compile_info_txtpath}': {e}"
            logging.error(error_msg)
            raise OSError(error_msg) from e

        except UnicodeDecodeError as e:
            error_msg = f"Encoding error when reading file '{compile_info_txtpath}' with encoding '{actual_encoding}': {e}"
            logging.error(error_msg)
            raise UnicodeDecodeError(e.encoding, e.object, e.start, e.end, error_msg) from e
        logging.info(f"Analyzed compile log: {path} ({file_size} bytes, encoding: {actual_encoding})")

    else:
        content=compile_info_txtpath
    # # Extract compilation information
    ##todo modify
    info_txt, bool_compile_ok = _analyze_compile_log(content)
    info_txt_truncate='\n'.join(content.split('\n')[-200:])

    # Log the operation
    # logging.info(f"Analyzed compile log: {path} ({file_size} bytes, encoding: {actual_encoding})")
    logging.info(f"Compilation status: {'SUCCESS' if bool_compile_ok else 'FAILED'}")
    logging.info(f"Compilation info: {info_txt_truncate}")
    return info_txt_truncate, bool_compile_ok

def _analyze_compile_log(content: str) -> Tuple[str, bool]:
    """
    Analyze compilation log content to determine success/failure and extract unique errors.

    Args:
        content: Raw compilation log content

    Returns:
        Tuple[str, bool]: Extracted info and compilation success status
    """
    lines = content.strip().split('\n')

    # Track compilation status indicators
    error_indicators = set()
    unique_errors = set()
    warning_counts = {}
    make_errors = []

    # Patterns for different types of messages
    error_patterns = [
        r':\s*error\s*:',  # Standard C/C++ errors
        r':\s*fatal error\s*:',  # Fatal errors
        r'make:\s*\*\*\*.*Error\s+\d+',  # Make errors
        r'compilation terminated',  # Compilation termination
        r'failed.*compilation',  # Failed compilation messages
        r'not a valid identifier'
    ]

    warning_patterns = [
        r':\s*warning\s*:',  # Standard warnings
        r'overriding recipe for target',  # Make warnings
        r'ignoring old recipe for target',  # Make warnings
    ]

    # Compile patterns
    compiled_error_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in error_patterns]
    compiled_warning_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in warning_patterns]

    # Process each line
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue

        # Check for errors
        for pattern in compiled_error_patterns:
            if pattern.search(line):
                error_indicators.add(line)
                if 'make:' in line.lower() and '***' in line:
                    make_errors.append(line)
                elif not _is_repetitive_error(line, unique_errors):
                    unique_errors.add(line)
                break

        # Check for warnings (count repetitive warnings)
        for pattern in compiled_warning_patterns:
            if pattern.search(line):
                warning_key = _normalize_warning(line)
                warning_counts[warning_key] = warning_counts.get(warning_key, 0) + 1
                break

    # Determine compilation success
    has_fatal_errors = bool(error_indicators)
    has_make_errors = bool(make_errors)
    bool_compile_ok = not (has_fatal_errors or has_make_errors)

    # Build extracted information
    info_sections = []

    # Add compilation status summary
    status = "COMPILATION SUCCESS" if bool_compile_ok else "COMPILATION FAILED"
    info_sections.append(f"=== {status} ===")

    if not bool_compile_ok:
        # Add unique compilation errors
        if unique_errors:
            info_sections.append("\n=== UNIQUE COMPILATION ERRORS ===")
            for error in sorted(unique_errors):
                info_sections.append(error)

        # Add make errors
        if make_errors:
            info_sections.append("\n=== MAKE ERRORS ===")
            for make_error in make_errors:
                info_sections.append(make_error)

    # Add warning summary (only if significant)
    if warning_counts:
        significant_warnings = {k: v for k, v in warning_counts.items() if v <= 5 or k not in ['overriding recipe', 'ignoring old recipe']}
        if significant_warnings:
            info_sections.append("\n=== WARNING SUMMARY ===")
            for warning, count in sorted(significant_warnings.items()):
                if count > 1:
                    info_sections.append(f"{warning} (occurred {count} times)")
                else:
                    info_sections.append(warning)

    # Add statistics
    info_sections.append("\n=== STATISTICS ===")
    info_sections.append(f"Total lines processed: {len(lines)}")
    info_sections.append(f"Unique errors found: {len(unique_errors)}")
    info_sections.append(f"Make errors found: {len(make_errors)}")
    info_sections.append(f"Warning types found: {len(warning_counts)}")

    info_txt = "\n".join(info_sections)
    return info_txt, bool_compile_ok


def _is_repetitive_error(error_line: str, existing_errors: Set[str]) -> bool:
    """
    Check if an error line is repetitive based on existing errors.

    Args:
        error_line: Current error line to check
        existing_errors: Set of already seen errors

    Returns:
        bool: True if the error is considered repetitive
    """
    # Normalize the error line for comparison
    normalized = re.sub(r':\d+:', ':LINE:', error_line)  # Replace line numbers
    normalized = re.sub(r'\b\d+\b', 'NUM', normalized)  # Replace other numbers

    # Check if we've seen a similar error
    for existing in existing_errors:
        existing_normalized = re.sub(r':\d+:', ':LINE:', existing)
        existing_normalized = re.sub(r'\b\d+\b', 'NUM', existing_normalized)

        if normalized == existing_normalized:
            return True

    return False


def _normalize_warning(warning_line: str) -> str:
    """
    Normalize warning lines for counting purposes.

    Args:
        warning_line: Warning line to normalize

    Returns:
        str: Normalized warning key
    """
    if 'overriding recipe' in warning_line.lower():
        return 'overriding recipe'
    elif 'ignoring old recipe' in warning_line.lower():
        return 'ignoring old recipe'
    else:
        # Extract the core warning message
        match = re.search(r'warning:\s*(.+)', warning_line, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return warning_line.strip()


def _detect_file_encoding(file_path: Path) -> Optional[str]:
    """
    Detect the encoding of a file using chardet.

    Args:
        file_path: Path to the file

    Returns:
        str: Detected encoding or None if detection fails
    """
    try:
        import chardet
        with open(file_path, 'rb') as f:
            # Read a sample of the file for encoding detection
            sample_size = min(8192, file_path.stat().st_size)
            raw_data = f.read(sample_size)

        if not raw_data:
            return "utf-8"  # Default for empty files

        result = chardet.detect(raw_data)
        encoding = result.get('encoding')
        confidence = result.get('confidence', 0)

        # Only use detected encoding if confidence is reasonable
        if encoding and confidence > 0.5:  # Lower threshold
            return encoding

        # Fall back to common encodings
        for fallback_encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
            try:
                with open(file_path, 'r', encoding=fallback_encoding) as f:
                    f.read(1024)  # Try to read a small portion
                return fallback_encoding
            except UnicodeDecodeError:
                continue

        return "utf-8"  # Final fallback

    except ImportError:
        # chardet not available, fall back to utf-8
        return "utf-8"
    except Exception as e:
        logging.warning(f"Failed to detect encoding for {file_path}: {e}")
        return "utf-8"  # Safe fallback
