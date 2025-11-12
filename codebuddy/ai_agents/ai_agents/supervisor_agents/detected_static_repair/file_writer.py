from pathlib import Path


def append_markdown_content_2_file(
    markdown_content: str,
    file_path: str,
    create_directories: bool = True,
    encoding: str = "utf-8",
    add_newline: bool = True
) -> str:
    """
    Append markdown content to an existing file or create a new one if it doesn't exist.

    This tool appends markdown content to the specified file, preserving existing content.
    It can optionally create parent directories if they don't exist.

    Args:
        markdown_content: The markdown content to append to the file
        file_path: The path of the file to append to (relative or absolute)
        create_directories: Whether to create parent directories if they don't exist (default: True)
        encoding: The encoding to use when writing the file (default: utf-8)
        add_newline: Whether to add a newline before the new content if file exists (default: True)

    Returns:
        str: Success message with file path and size information

    Raises:
        ValueError: If file_path or markdown_content is empty or invalid
        PermissionError: If insufficient permissions to create file or directories
        OSError: If there's an error creating directories or writing the file

    Examples:
        >>> append_markdown_content_2_file("# New Section\\nContent here", "README.md")
        >>> append_markdown_content_2_file("## Updates\\n- Added feature", "docs/changelog.md")
        >>> append_markdown_content_2_file("*Note: Important info*", "notes.md")
    """
    if not file_path:
        raise ValueError("file_path is required and cannot be empty")

    if not file_path.strip():
        raise ValueError("file_path cannot be just whitespace")

    if not markdown_content:
        raise ValueError("markdown_content is required and cannot be empty")

    # Convert to Path object for easier manipulation
    path = Path(file_path)

    # Validate the path
    if path.is_dir():
        raise ValueError(f"Path '{file_path}' is a directory, not a file")

    # Check if file exists to determine if we need a newline separator
    file_existed = path.exists()
    file_has_content = False

    if file_existed:
        try:
            with open(path, 'r', encoding=encoding) as f:
                existing_content = f.read()
                file_has_content = bool(existing_content.strip())
        except (OSError, UnicodeDecodeError):
            # If we can't read the file, assume it has content to be safe
            file_has_content = True

    try:
        # Create parent directories if needed
        if create_directories and path.parent != path:
            path.parent.mkdir(parents=True, exist_ok=True)
            print(f"Created directories: {path.parent}")

        # Prepare content to append
        content_to_append = markdown_content
        if file_existed and file_has_content and add_newline:
            # Add newline separator if file exists and has content
            if not markdown_content.startswith('\n'):
                content_to_append = '\n' + markdown_content

        # Append to the file
        with open(path, 'a', encoding=encoding) as f:
            f.write(content_to_append)

        # Get file size for confirmation
        file_size = path.stat().st_size

        # Log the operation
        print(f"Appended to file: {path} ({len(markdown_content)} bytes added, total: {file_size} bytes)")

        # Return success message
        action = "Appended to existing" if file_existed else "Created new"
        return f"{action} file '{file_path}' successfully. Content added: {len(markdown_content)} bytes, Total size: {file_size} bytes, Encoding: {encoding}"

    except PermissionError as e:
        error_msg = f"Permission denied when writing to file '{file_path}': {e}"
        print(error_msg)
        raise PermissionError(error_msg) from e

    except OSError as e:
        error_msg = f"Failed to write to file '{file_path}': {e}"
        print(error_msg)
        raise OSError(error_msg) from e

    except UnicodeEncodeError as e:
        error_msg = f"Encoding error when writing file '{file_path}' with encoding '{encoding}': {e}"
        print(error_msg)
        raise ValueError(error_msg) from e
