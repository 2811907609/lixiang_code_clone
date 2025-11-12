import logging
from pathlib import Path


def create_new_file(
    file_path: str,
    content: str = "",
    create_directories: bool = True,
    overwrite: bool = False,
    encoding: str = "utf-8"
) -> str:
    """
    Create a new file with the specified content.

    This tool creates a new file at the given path with the provided content.
    It can optionally create parent directories and handle file overwriting.

    Args:
        file_path: The path where the new file should be created (relative or absolute)
        content: The content to write to the file (default: empty string)
        create_directories: Whether to create parent directories if they don't exist (default: True)
        overwrite: Whether to overwrite the file if it already exists (default: False)
        encoding: The encoding to use when writing the file (default: utf-8)

    Returns:
        str: Success message with file path and size information

    Raises:
        ValueError: If file_path is empty or invalid
        FileExistsError: If file exists and overwrite is False
        PermissionError: If insufficient permissions to create file or directories
        OSError: If there's an error creating directories or writing the file

    Examples:
        >>> create_new_file("test.txt", "Hello, World!")
        >>> create_new_file("src/utils/helper.py", "# Helper functions\\n")
        >>> create_new_file("config/settings.json", '{"debug": true}', overwrite=True)
    """
    if not file_path:
        raise ValueError("file_path is required and cannot be empty")

    if not file_path.strip():
        raise ValueError("file_path cannot be just whitespace")

    # Convert to Path object for easier manipulation
    path = Path(file_path)

    # Validate the path
    if path.is_dir():
        raise ValueError(f"Path '{file_path}' is a directory, not a file")

    # Check if file already exists
    file_existed = path.exists()
    if file_existed and not overwrite:
        raise FileExistsError(f"File '{file_path}' already exists. Use overwrite=True to replace it.")

    try:
        # Create parent directories if needed
        if create_directories and path.parent != path:
            path.parent.mkdir(parents=True, exist_ok=True)
            logging.info(f"Created directories: {path.parent}")

        # Write the file
        with open(path, 'w', encoding=encoding) as f:
            f.write(content)

        # Get file size for confirmation
        file_size = path.stat().st_size

        # Log the operation
        logging.info(f"Created file: {path} ({file_size} bytes)")

        # Return success message
        action = "Overwritten" if file_existed and overwrite else "Created"
        return f"{action} file '{file_path}' successfully. Size: {file_size} bytes, Encoding: {encoding}"

    except PermissionError as e:
        error_msg = f"Permission denied when creating file '{file_path}': {e}"
        logging.error(error_msg)
        raise PermissionError(error_msg) from e

    except OSError as e:
        error_msg = f"Failed to create file '{file_path}': {e}"
        logging.error(error_msg)
        raise OSError(error_msg) from e

    except UnicodeEncodeError as e:
        error_msg = f"Encoding error when writing file '{file_path}' with encoding '{encoding}': {e}"
        logging.error(error_msg)
        raise ValueError(error_msg) from e
