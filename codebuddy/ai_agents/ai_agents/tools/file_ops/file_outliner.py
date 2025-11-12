import logging
import re
from pathlib import Path
from typing import List
from commonlibs.encoding.detect_content_encoding import detect_file_encoding

def get_file_outline(
    file_path: str,
    detail_level: str = "detailed",
    max_size_mb: float = 50.0,
    encoding: str = "auto",
    include_line_numbers: bool = True,
    max_items_per_section: int = 50
) -> str:
    """
    Generate a structural outline/summary of a file for large file analysis.

    This tool analyzes file structure and extracts key elements like functions,
    classes, imports, and other structural components without loading the entire
    file content. Particularly useful for understanding large files quickly.

    Args:
        file_path: Path to the file to analyze (relative or absolute)
        detail_level: Level of detail in outline. Options: "brief", "detailed", "full" (default: detailed)
        max_size_mb: Maximum file size in MB to analyze (default: 50.0)
        encoding: File encoding to use. Use "auto" for automatic detection (default: auto)
        include_line_numbers: Whether to include line numbers in the outline (default: True)
        max_items_per_section: Maximum items to show per section to avoid overwhelming output (default: 50)

    Returns:
        str: Structured outline of the file

    Raises:
        ValueError: If parameters are invalid
        FileNotFoundError: If the file doesn't exist
        PermissionError: If insufficient permissions to read file
        OSError: If there's an error reading the file

    Examples:
        >>> get_file_outline("large_module.py")
        >>> get_file_outline("app.js", detail_level="brief")
        >>> get_file_outline("README.md", detail_level="full", include_line_numbers=False)
    """
    # Validate inputs
    if not file_path or not file_path.strip():
        raise ValueError("file_path is required and cannot be empty")

    if detail_level not in ["brief", "detailed", "full"]:
        raise ValueError("detail_level must be one of: brief, detailed, full")

    if max_size_mb <= 0:
        raise ValueError("max_size_mb must be positive")

    if max_items_per_section < 1:
        raise ValueError("max_items_per_section must be at least 1")

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

        if file_size > max_size_bytes:
            raise ValueError(f"File '{file_path}' is too large ({file_size / 1024 / 1024:.2f} MB). "
                           f"Maximum allowed size is {max_size_mb} MB.")

        # Determine encoding
        if encoding == "auto":
            detected_encoding = detect_file_encoding(path)
            actual_encoding = detected_encoding or "utf-8"
        else:
            actual_encoding = encoding

        # Determine file type
        file_type = _determine_file_type(path)

        # Generate outline based on file type
        outline = _generate_outline(path, file_type, detail_level, actual_encoding,
                                  include_line_numbers, max_items_per_section)

        # Log the operation
        logging.info(f"Generated outline for: {path} (type: {file_type}, detail: {detail_level})")

        return outline

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

def _determine_file_type(file_path: Path) -> str:
    """
    Determine the type of file based on extension and content.
    """
    extension = file_path.suffix.lower()

    # Programming languages
    if extension in ['.py', '.pyw']:
        return 'python'
    elif extension in ['.js', '.jsx', '.ts', '.tsx']:
        return 'javascript'
    elif extension in ['.go']:
        return 'go'
    elif extension in ['.java']:
        return 'java'
    elif extension in ['.c', '.h']:
        return 'c'
    elif extension in ['.cpp', '.cc', '.cxx', '.hpp', '.hxx']:
        return 'cpp'
    elif extension in ['.rs']:
        return 'rust'
    elif extension in ['.rb']:
        return 'ruby'
    elif extension in ['.php']:
        return 'php'
    elif extension in ['.cs']:
        return 'csharp'
    elif extension in ['.swift']:
        return 'swift'
    elif extension in ['.kt', '.kts']:
        return 'kotlin'
    elif extension in ['.scala']:
        return 'scala'

    # Markup and documentation
    elif extension in ['.md', '.markdown']:
        return 'markdown'
    elif extension in ['.rst']:
        return 'restructuredtext'
    elif extension in ['.html', '.htm']:
        return 'html'
    elif extension in ['.xml']:
        return 'xml'
    elif extension in ['.tex']:
        return 'latex'

    # Configuration and data
    elif extension in ['.json']:
        return 'json'
    elif extension in ['.yaml', '.yml']:
        return 'yaml'
    elif extension in ['.toml']:
        return 'toml'
    elif extension in ['.ini', '.cfg', '.conf']:
        return 'config'
    elif extension in ['.sql']:
        return 'sql'
    elif extension in ['.sh', '.bash', '.zsh']:
        return 'shell'
    elif extension in ['.dockerfile']:
        return 'dockerfile'
    elif extension in ['.makefile'] or file_path.name.lower() in ['makefile', 'gnumakefile']:
        return 'makefile'

    # Default to text
    else:
        return 'text'


def _generate_outline(file_path: Path, file_type: str, detail_level: str,
                     encoding: str, include_line_numbers: bool, max_items: int) -> str:
    """
    Generate outline based on file type and detail level.
    """
    # Read file content
    with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
        lines = f.readlines()

    total_lines = len(lines)

    # Start building outline
    outline_parts = []
    outline_parts.append(f"File Outline: {file_path}")
    outline_parts.append(f"Type: {file_type.title()}")
    outline_parts.append(f"Lines: {total_lines:,}")
    outline_parts.append(f"Size: {file_path.stat().st_size:,} bytes")
    outline_parts.append("=" * 50)

    # Generate type-specific outline
    if file_type == 'python':
        outline_parts.extend(_analyze_python_file(lines, detail_level, include_line_numbers, max_items))
    elif file_type in ['javascript', 'typescript']:
        outline_parts.extend(_analyze_javascript_file(lines, detail_level, include_line_numbers, max_items))
    elif file_type == 'go':
        outline_parts.extend(_analyze_go_file(lines, detail_level, include_line_numbers, max_items))
    elif file_type == 'java':
        outline_parts.extend(_analyze_java_file(lines, detail_level, include_line_numbers, max_items))
    elif file_type in ['c', 'cpp']:
        outline_parts.extend(_analyze_c_cpp_file(lines, detail_level, include_line_numbers, max_items))
    elif file_type == 'markdown':
        outline_parts.extend(_analyze_markdown_file(lines, detail_level, include_line_numbers, max_items))
    elif file_type in ['json', 'yaml', 'toml']:
        outline_parts.extend(_analyze_data_file(lines, file_type, detail_level, include_line_numbers, max_items))
    else:
        outline_parts.extend(_analyze_generic_file(lines, detail_level, include_line_numbers, max_items))

    return '\n'.join(outline_parts)


def _analyze_python_file(lines: List[str], detail_level: str, include_line_numbers: bool, max_items: int) -> List[str]:
    """Analyze Python file structure."""
    outline = []

    # Extract imports
    imports = []
    classes = []
    functions = []
    constants = []

    current_class = None
    indent_level = 0

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith('#'):
            continue

        # Calculate indentation
        line_indent = len(line) - len(line.lstrip())

        # Imports
        if stripped.startswith(('import ', 'from ')):
            imports.append((i, stripped) if include_line_numbers else stripped)

        # Classes
        elif stripped.startswith('class '):
            match = re.match(r'class\s+(\w+)(?:\([^)]*\))?:', stripped)
            if match:
                class_name = match.group(1)
                current_class = class_name
                indent_level = line_indent
                classes.append((i, class_name, []) if include_line_numbers else (class_name, []))

        # Functions and methods
        elif stripped.startswith('def '):
            match = re.match(r'def\s+(\w+)\s*\([^)]*\)(?:\s*->\s*[^:]+)?:', stripped)
            if match:
                func_name = match.group(1)
                if current_class and line_indent > indent_level:
                    # Method
                    if include_line_numbers:
                        classes[-1][2].append((i, func_name))
                    else:
                        classes[-1][1].append(func_name)
                else:
                    # Function
                    current_class = None
                    functions.append((i, func_name) if include_line_numbers else func_name)

        # Constants (uppercase variables at module level)
        elif line_indent == 0 and '=' in stripped and not stripped.startswith(('def ', 'class ', 'import ', 'from ')):
            match = re.match(r'([A-Z][A-Z0-9_]*)\s*=', stripped)
            if match:
                const_name = match.group(1)
                constants.append((i, const_name) if include_line_numbers else const_name)

    # Build outline sections
    if imports:
        outline.append("\n📦 IMPORTS:")
        for item in imports[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: {item[1]}")
            else:
                outline.append(f"  {item}")
        if len(imports) > max_items:
            outline.append(f"  ... and {len(imports) - max_items} more imports")

    if constants:
        outline.append("\n🔢 CONSTANTS:")
        for item in constants[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: {item[1]}")
            else:
                outline.append(f"  {item}")
        if len(constants) > max_items:
            outline.append(f"  ... and {len(constants) - max_items} more constants")

    if classes:
        outline.append("\n🏛️  CLASSES:")
        for item in classes[:max_items]:
            if include_line_numbers:
                line_num, class_name, methods = item
                outline.append(f"  {line_num:4d}: class {class_name}")
                if detail_level in ["detailed", "full"] and methods:
                    for method_line, method_name in methods[:10]:  # Limit methods shown
                        outline.append(f"    {method_line:4d}:   def {method_name}()")
                    if len(methods) > 10:
                        outline.append(f"    ... and {len(methods) - 10} more methods")
            else:
                class_name, methods = item
                outline.append(f"  class {class_name}")
                if detail_level in ["detailed", "full"] and methods:
                    for method_name in methods[:10]:
                        outline.append(f"    def {method_name}()")
                    if len(methods) > 10:
                        outline.append(f"    ... and {len(methods) - 10} more methods")
        if len(classes) > max_items:
            outline.append(f"  ... and {len(classes) - max_items} more classes")

    if functions:
        outline.append("\n⚙️  FUNCTIONS:")
        for item in functions[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: def {item[1]}()")
            else:
                outline.append(f"  def {item}()")
        if len(functions) > max_items:
            outline.append(f"  ... and {len(functions) - max_items} more functions")

    return outline


def _analyze_javascript_file(lines: List[str], detail_level: str, include_line_numbers: bool, max_items: int) -> List[str]:
    """Analyze JavaScript/TypeScript file structure."""
    outline = []

    imports = []
    exports = []
    functions = []
    classes = []
    constants = []
    interfaces = []  # For TypeScript

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
            continue

        # Imports
        if stripped.startswith(('import ', 'const ')) and ' from ' in stripped:
            imports.append((i, stripped) if include_line_numbers else stripped)
        elif stripped.startswith('require('):
            imports.append((i, stripped) if include_line_numbers else stripped)

        # Exports
        elif stripped.startswith('export '):
            exports.append((i, stripped) if include_line_numbers else stripped)

        # Functions
        elif 'function ' in stripped:
            match = re.search(r'function\s+(\w+)\s*\(', stripped)
            if match:
                func_name = match.group(1)
                functions.append((i, func_name) if include_line_numbers else func_name)

        # Arrow functions
        elif '=>' in stripped and ('const ' in stripped or 'let ' in stripped or 'var ' in stripped):
            match = re.search(r'(?:const|let|var)\s+(\w+)\s*=.*=>', stripped)
            if match:
                func_name = match.group(1)
                functions.append((i, func_name) if include_line_numbers else func_name)

        # Classes
        elif stripped.startswith('class '):
            match = re.match(r'class\s+(\w+)', stripped)
            if match:
                class_name = match.group(1)
                classes.append((i, class_name) if include_line_numbers else class_name)

        # TypeScript interfaces
        elif stripped.startswith('interface '):
            match = re.match(r'interface\s+(\w+)', stripped)
            if match:
                interface_name = match.group(1)
                interfaces.append((i, interface_name) if include_line_numbers else interface_name)

        # Constants
        elif stripped.startswith('const ') and '=' in stripped and '=>' not in stripped:
            match = re.match(r'const\s+([A-Z][A-Z0-9_]*)\s*=', stripped)
            if match:
                const_name = match.group(1)
                constants.append((i, const_name) if include_line_numbers else const_name)

    # Build outline
    if imports:
        outline.append("\n📦 IMPORTS:")
        for item in imports[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: {item[1]}")
            else:
                outline.append(f"  {item}")
        if len(imports) > max_items:
            outline.append(f"  ... and {len(imports) - max_items} more imports")

    if interfaces:
        outline.append("\n🔗 INTERFACES:")
        for item in interfaces[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: interface {item[1]}")
            else:
                outline.append(f"  interface {item}")
        if len(interfaces) > max_items:
            outline.append(f"  ... and {len(interfaces) - max_items} more interfaces")

    if classes:
        outline.append("\n🏛️  CLASSES:")
        for item in classes[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: class {item[1]}")
            else:
                outline.append(f"  class {item}")
        if len(classes) > max_items:
            outline.append(f"  ... and {len(classes) - max_items} more classes")

    if functions:
        outline.append("\n⚙️  FUNCTIONS:")
        for item in functions[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: {item[1]}()")
            else:
                outline.append(f"  {item}()")
        if len(functions) > max_items:
            outline.append(f"  ... and {len(functions) - max_items} more functions")

    if constants:
        outline.append("\n🔢 CONSTANTS:")
        for item in constants[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: {item[1]}")
            else:
                outline.append(f"  {item}")
        if len(constants) > max_items:
            outline.append(f"  ... and {len(constants) - max_items} more constants")

    if exports:
        outline.append("\n📤 EXPORTS:")
        for item in exports[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: {item[1]}")
            else:
                outline.append(f"  {item}")
        if len(exports) > max_items:
            outline.append(f"  ... and {len(exports) - max_items} more exports")

    return outline


def _analyze_go_file(lines: List[str], detail_level: str, include_line_numbers: bool, max_items: int) -> List[str]:
    """Analyze Go file structure."""
    outline = []

    imports = []
    functions = []
    types = []
    constants = []
    variables = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if not stripped or stripped.startswith('//'):
            continue

        # Package declaration
        if stripped.startswith('package '):
            outline.append(f"\n📦 PACKAGE: {stripped}")

        # Imports
        elif stripped.startswith('import '):
            imports.append((i, stripped) if include_line_numbers else stripped)

        # Functions
        elif stripped.startswith('func '):
            match = re.match(r'func\s+(?:\([^)]*\)\s+)?(\w+)\s*\(', stripped)
            if match:
                func_name = match.group(1)
                functions.append((i, func_name) if include_line_numbers else func_name)

        # Types (structs, interfaces)
        elif stripped.startswith('type '):
            match = re.match(r'type\s+(\w+)\s+(struct|interface)', stripped)
            if match:
                type_name, type_kind = match.groups()
                types.append((i, f"{type_name} ({type_kind})") if include_line_numbers else f"{type_name} ({type_kind})")

        # Constants
        elif stripped.startswith('const '):
            match = re.match(r'const\s+(\w+)', stripped)
            if match:
                const_name = match.group(1)
                constants.append((i, const_name) if include_line_numbers else const_name)

        # Variables
        elif stripped.startswith('var '):
            match = re.match(r'var\s+(\w+)', stripped)
            if match:
                var_name = match.group(1)
                variables.append((i, var_name) if include_line_numbers else var_name)

    # Build outline
    if imports:
        outline.append("\n📦 IMPORTS:")
        for item in imports[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: {item[1]}")
            else:
                outline.append(f"  {item}")
        if len(imports) > max_items:
            outline.append(f"  ... and {len(imports) - max_items} more imports")

    if types:
        outline.append("\n🏗️  TYPES:")
        for item in types[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: {item[1]}")
            else:
                outline.append(f"  {item}")
        if len(types) > max_items:
            outline.append(f"  ... and {len(types) - max_items} more types")

    if constants:
        outline.append("\n🔢 CONSTANTS:")
        for item in constants[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: {item[1]}")
            else:
                outline.append(f"  {item}")
        if len(constants) > max_items:
            outline.append(f"  ... and {len(constants) - max_items} more constants")

    if variables:
        outline.append("\n📊 VARIABLES:")
        for item in variables[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: {item[1]}")
            else:
                outline.append(f"  {item}")
        if len(variables) > max_items:
            outline.append(f"  ... and {len(variables) - max_items} more variables")

    if functions:
        outline.append("\n⚙️  FUNCTIONS:")
        for item in functions[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: {item[1]}()")
            else:
                outline.append(f"  {item}()")
        if len(functions) > max_items:
            outline.append(f"  ... and {len(functions) - max_items} more functions")

    return outline


def _analyze_java_file(lines: List[str], detail_level: str, include_line_numbers: bool, max_items: int) -> List[str]:
    """Analyze Java file structure."""
    outline = []

    imports = []
    classes = []
    interfaces = []
    methods = []
    fields = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
            continue

        # Package declaration
        if stripped.startswith('package '):
            outline.append(f"\n📦 PACKAGE: {stripped}")

        # Imports
        elif stripped.startswith('import '):
            imports.append((i, stripped) if include_line_numbers else stripped)

        # Classes
        elif 'class ' in stripped and not stripped.startswith('//'):
            match = re.search(r'class\s+(\w+)', stripped)
            if match:
                class_name = match.group(1)
                classes.append((i, class_name) if include_line_numbers else class_name)

        # Interfaces
        elif 'interface ' in stripped:
            match = re.search(r'interface\s+(\w+)', stripped)
            if match:
                interface_name = match.group(1)
                interfaces.append((i, interface_name) if include_line_numbers else interface_name)

        # Methods
        elif re.search(r'(public|private|protected|static).*\w+\s*\([^)]*\)\s*\{', stripped):
            match = re.search(r'\b(\w+)\s*\([^)]*\)\s*\{', stripped)
            if match:
                method_name = match.group(1)
                methods.append((i, method_name) if include_line_numbers else method_name)

        # Fields
        elif re.search(r'(public|private|protected|static).*\w+\s+\w+\s*[;=]', stripped):
            match = re.search(r'\b(\w+)\s*[;=]', stripped)
            if match:
                field_name = match.group(1)
                fields.append((i, field_name) if include_line_numbers else field_name)

    # Build outline
    if imports:
        outline.append("\n📦 IMPORTS:")
        for item in imports[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: {item[1]}")
            else:
                outline.append(f"  {item}")
        if len(imports) > max_items:
            outline.append(f"  ... and {len(imports) - max_items} more imports")

    if interfaces:
        outline.append("\n🔗 INTERFACES:")
        for item in interfaces[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: interface {item[1]}")
            else:
                outline.append(f"  interface {item}")
        if len(interfaces) > max_items:
            outline.append(f"  ... and {len(interfaces) - max_items} more interfaces")

    if classes:
        outline.append("\n🏛️  CLASSES:")
        for item in classes[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: class {item[1]}")
            else:
                outline.append(f"  class {item}")
        if len(classes) > max_items:
            outline.append(f"  ... and {len(classes) - max_items} more classes")

    if fields:
        outline.append("\n📊 FIELDS:")
        for item in fields[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: {item[1]}")
            else:
                outline.append(f"  {item}")
        if len(fields) > max_items:
            outline.append(f"  ... and {len(fields) - max_items} more fields")

    if methods:
        outline.append("\n⚙️  METHODS:")
        for item in methods[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: {item[1]}()")
            else:
                outline.append(f"  {item}()")
        if len(methods) > max_items:
            outline.append(f"  ... and {len(methods) - max_items} more methods")

    return outline


def _analyze_c_cpp_file(lines: List[str], detail_level: str, include_line_numbers: bool, max_items: int) -> List[str]:
    """Analyze C/C++ file structure."""
    outline = []

    includes = []
    functions = []
    classes = []  # For C++
    structs = []
    defines = []
    typedefs = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
            continue

        # Includes
        if stripped.startswith('#include'):
            includes.append((i, stripped) if include_line_numbers else stripped)

        # Defines
        elif stripped.startswith('#define'):
            match = re.match(r'#define\s+(\w+)', stripped)
            if match:
                define_name = match.group(1)
                defines.append((i, define_name) if include_line_numbers else define_name)

        # Functions
        elif re.search(r'\w+\s+\w+\s*\([^)]*\)\s*\{', stripped) and not stripped.startswith('if') and not stripped.startswith('for'):
            match = re.search(r'\b(\w+)\s*\([^)]*\)\s*\{', stripped)
            if match:
                func_name = match.group(1)
                functions.append((i, func_name) if include_line_numbers else func_name)

        # Classes (C++)
        elif stripped.startswith('class '):
            match = re.match(r'class\s+(\w+)', stripped)
            if match:
                class_name = match.group(1)
                classes.append((i, class_name) if include_line_numbers else class_name)

        # Structs
        elif stripped.startswith('struct '):
            match = re.match(r'struct\s+(\w+)', stripped)
            if match:
                struct_name = match.group(1)
                structs.append((i, struct_name) if include_line_numbers else struct_name)

        # Typedefs
        elif stripped.startswith('typedef '):
            match = re.search(r'typedef.*\s+(\w+)\s*;', stripped)
            if match:
                typedef_name = match.group(1)
                typedefs.append((i, typedef_name) if include_line_numbers else typedef_name)

    # Build outline
    if includes:
        outline.append("\n📦 INCLUDES:")
        for item in includes[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: {item[1]}")
            else:
                outline.append(f"  {item}")
        if len(includes) > max_items:
            outline.append(f"  ... and {len(includes) - max_items} more includes")

    if defines:
        outline.append("\n🔧 DEFINES:")
        for item in defines[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: #define {item[1]}")
            else:
                outline.append(f"  #define {item}")
        if len(defines) > max_items:
            outline.append(f"  ... and {len(defines) - max_items} more defines")

    if typedefs:
        outline.append("\n🏷️  TYPEDEFS:")
        for item in typedefs[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: {item[1]}")
            else:
                outline.append(f"  {item}")
        if len(typedefs) > max_items:
            outline.append(f"  ... and {len(typedefs) - max_items} more typedefs")

    if structs:
        outline.append("\n🏗️  STRUCTS:")
        for item in structs[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: struct {item[1]}")
            else:
                outline.append(f"  struct {item}")
        if len(structs) > max_items:
            outline.append(f"  ... and {len(structs) - max_items} more structs")

    if classes:
        outline.append("\n🏛️  CLASSES:")
        for item in classes[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: class {item[1]}")
            else:
                outline.append(f"  class {item}")
        if len(classes) > max_items:
            outline.append(f"  ... and {len(classes) - max_items} more classes")

    if functions:
        outline.append("\n⚙️  FUNCTIONS:")
        for item in functions[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: {item[1]}()")
            else:
                outline.append(f"  {item}()")
        if len(functions) > max_items:
            outline.append(f"  ... and {len(functions) - max_items} more functions")

    return outline


def _analyze_markdown_file(lines: List[str], detail_level: str, include_line_numbers: bool, max_items: int) -> List[str]:
    """Analyze Markdown file structure."""
    outline = []

    headers = []
    links = []
    images = []
    code_blocks = []

    in_code_block = False
    code_block_lang = None

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if not stripped:
            continue

        # Headers
        if stripped.startswith('#'):
            level = len(stripped) - len(stripped.lstrip('#'))
            header_text = stripped.lstrip('#').strip()
            headers.append((i, level, header_text) if include_line_numbers else (level, header_text))

        # Code blocks
        elif stripped.startswith('```'):
            if not in_code_block:
                in_code_block = True
                code_block_lang = stripped[3:].strip() or 'text'
                code_blocks.append((i, code_block_lang) if include_line_numbers else code_block_lang)
            else:
                in_code_block = False
                code_block_lang = None

        # Links
        elif '[' in stripped and '](' in stripped:
            link_matches = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', stripped)
            for link_text, link_url in link_matches:
                links.append((i, f"{link_text} -> {link_url}") if include_line_numbers else f"{link_text} -> {link_url}")

        # Images
        elif '![' in stripped and '](' in stripped:
            img_matches = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', stripped)
            for img_alt, img_url in img_matches:
                images.append((i, f"{img_alt} -> {img_url}") if include_line_numbers else f"{img_alt} -> {img_url}")

    # Build outline
    if headers:
        outline.append("\n📋 HEADERS:")
        for item in headers[:max_items]:
            if include_line_numbers:
                line_num, level, text = item
                indent = "  " * level
                outline.append(f"  {line_num:4d}: {indent}{'#' * level} {text}")
            else:
                level, text = item
                indent = "  " * level
                outline.append(f"  {indent}{'#' * level} {text}")
        if len(headers) > max_items:
            outline.append(f"  ... and {len(headers) - max_items} more headers")

    if code_blocks and detail_level in ["detailed", "full"]:
        outline.append("\n💻 CODE BLOCKS:")
        for item in code_blocks[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: ```{item[1]}")
            else:
                outline.append(f"  ```{item}")
        if len(code_blocks) > max_items:
            outline.append(f"  ... and {len(code_blocks) - max_items} more code blocks")

    if links and detail_level == "full":
        outline.append("\n🔗 LINKS:")
        for item in links[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: {item[1]}")
            else:
                outline.append(f"  {item}")
        if len(links) > max_items:
            outline.append(f"  ... and {len(links) - max_items} more links")

    if images and detail_level == "full":
        outline.append("\n🖼️  IMAGES:")
        for item in images[:max_items]:
            if include_line_numbers:
                outline.append(f"  {item[0]:4d}: {item[1]}")
            else:
                outline.append(f"  {item}")
        if len(images) > max_items:
            outline.append(f"  ... and {len(images) - max_items} more images")

    return outline


def _analyze_data_file(lines: List[str], file_type: str, detail_level: str, include_line_numbers: bool, max_items: int) -> List[str]:
    """Analyze data files (JSON, YAML, TOML, etc.)."""
    outline = []

    if file_type == 'json':
        # For JSON, try to parse and show structure
        try:
            import json
            content = ''.join(lines)
            data = json.loads(content)
            outline.append("\n📊 JSON STRUCTURE:")
            outline.extend(_analyze_json_structure(data, detail_level, max_items))
        except json.JSONDecodeError as e:
            outline.append(f"\n❌ JSON PARSE ERROR: {e}")
            outline.extend(_analyze_generic_file(lines, detail_level, include_line_numbers, max_items))

    elif file_type == 'yaml':
        # For YAML, show top-level keys and structure
        top_level_keys = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and ':' in stripped and not stripped.startswith(' '):
                key = stripped.split(':')[0].strip()
                top_level_keys.append((i, key) if include_line_numbers else key)

        if top_level_keys:
            outline.append("\n🔑 TOP-LEVEL KEYS:")
            for item in top_level_keys[:max_items]:
                if include_line_numbers:
                    outline.append(f"  {item[0]:4d}: {item[1]}")
                else:
                    outline.append(f"  {item}")
            if len(top_level_keys) > max_items:
                outline.append(f"  ... and {len(top_level_keys) - max_items} more keys")

    elif file_type == 'toml':
        # For TOML, show sections and keys
        sections = []
        keys = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith('[') and stripped.endswith(']'):
                section = stripped[1:-1]
                sections.append((i, section) if include_line_numbers else section)
            elif '=' in stripped and not stripped.startswith('#'):
                key = stripped.split('=')[0].strip()
                keys.append((i, key) if include_line_numbers else key)

        if sections:
            outline.append("\n📂 SECTIONS:")
            for item in sections[:max_items]:
                if include_line_numbers:
                    outline.append(f"  {item[0]:4d}: [{item[1]}]")
                else:
                    outline.append(f"  [{item}]")
            if len(sections) > max_items:
                outline.append(f"  ... and {len(sections) - max_items} more sections")

        if keys:
            outline.append("\n🔑 KEYS:")
            for item in keys[:max_items]:
                if include_line_numbers:
                    outline.append(f"  {item[0]:4d}: {item[1]}")
                else:
                    outline.append(f"  {item}")
            if len(keys) > max_items:
                outline.append(f"  ... and {len(keys) - max_items} more keys")

    else:
        outline.extend(_analyze_generic_file(lines, detail_level, include_line_numbers, max_items))

    return outline


def _analyze_json_structure(data, detail_level: str, max_items: int, indent: int = 0) -> List[str]:
    """Recursively analyze JSON structure."""
    outline = []
    indent_str = "  " * indent

    if isinstance(data, dict):
        for i, (key, value) in enumerate(data.items()):
            if i >= max_items:
                outline.append(f"{indent_str}... and {len(data) - max_items} more keys")
                break

            if isinstance(value, (dict, list)):
                outline.append(f"{indent_str}{key}: {type(value).__name__} ({len(value)} items)")
                if detail_level in ["detailed", "full"] and indent < 2:
                    outline.extend(_analyze_json_structure(value, detail_level, max_items, indent + 1))
            else:
                outline.append(f"{indent_str}{key}: {type(value).__name__}")

    elif isinstance(data, list):
        outline.append(f"{indent_str}Array with {len(data)} items")
        if detail_level in ["detailed", "full"] and data and indent < 2:
            # Show structure of first item if it's complex
            first_item = data[0]
            if isinstance(first_item, (dict, list)):
                outline.append(f"{indent_str}Item structure:")
                outline.extend(_analyze_json_structure(first_item, detail_level, max_items, indent + 1))

    return outline


def _analyze_generic_file(lines: List[str], detail_level: str, include_line_numbers: bool, max_items: int) -> List[str]:
    """Analyze generic text files."""
    outline = []

    # Basic statistics
    total_lines = len(lines)
    non_empty_lines = sum(1 for line in lines if line.strip())
    empty_lines = total_lines - non_empty_lines

    # Character and word counts
    total_chars = sum(len(line) for line in lines)
    total_words = sum(len(line.split()) for line in lines)

    outline.append("\n📊 STATISTICS:")
    outline.append(f"  Total lines: {total_lines:,}")
    outline.append(f"  Non-empty lines: {non_empty_lines:,}")
    outline.append(f"  Empty lines: {empty_lines:,}")
    outline.append(f"  Total characters: {total_chars:,}")
    outline.append(f"  Total words: {total_words:,}")

    if detail_level in ["detailed", "full"]:
        # Find longest lines
        long_lines = []
        for i, line in enumerate(lines, 1):
            if len(line) > 100:  # Lines longer than 100 characters
                long_lines.append((i, len(line), line[:80] + "..." if len(line) > 80 else line))

        if long_lines:
            outline.append("\n📏 LONG LINES (>100 chars):")
            for item in long_lines[:max_items]:
                if include_line_numbers:
                    line_num, length, preview = item
                    outline.append(f"  {line_num:4d}: ({length} chars) {preview}")
                else:
                    _, length, preview = item
                    outline.append(f"  ({length} chars) {preview}")
            if len(long_lines) > max_items:
                outline.append(f"  ... and {len(long_lines) - max_items} more long lines")

    if detail_level == "full":
        # Show first few lines as preview
        outline.append("\n👀 CONTENT PREVIEW:")
        preview_lines = min(10, len(lines))
        for i in range(preview_lines):
            line = lines[i].rstrip()
            if include_line_numbers:
                outline.append(f"  {i+1:4d}: {line[:100]}{'...' if len(line) > 100 else ''}")
            else:
                outline.append(f"  {line[:100]}{'...' if len(line) > 100 else ''}")
        if len(lines) > preview_lines:
            outline.append(f"  ... and {len(lines) - preview_lines} more lines")

    return outline
