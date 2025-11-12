"""
Regex-based code parsing tools for multi-language support.

This module provides regex-based parsing as a fallback when Tree-sitter is not available.
It extracts basic code elements using pattern matching.
"""

import ast
import re
from pathlib import Path
from typing import List, Dict, Optional, Any

# Language detection mapping
LANGUAGE_EXTENSIONS = {
    '.py': 'python',
    '.go': 'go',
    '.c': 'c',
    '.cpp': 'cpp',
    '.cc': 'cpp',
    '.cxx': 'cpp',
    '.java': 'java',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.jsx': 'javascript',
    '.tsx': 'typescript',
    '.h': 'c',
    '.hpp': 'cpp',
    '.hxx': 'cpp'
}

SUPPORTED_LANGUAGES = {
    'python', 'go', 'c', 'cpp', 'java', 'javascript', 'typescript'
}


def parse_code_with_regex(
    file_path: str,
    element_types: List[str] = None,
    include_docstrings: bool = True,
    include_decorators: bool = True,
    include_line_numbers: bool = True,
    language: str = None
) -> str:
    """
    Parse source code using regex patterns as a fallback method.

    This tool provides basic code parsing using regular expressions when
    Tree-sitter is not available. It's less accurate but more compatible.

    Args:
        file_path: Path to the source file to analyze
        element_types: List of element types to extract. If None, extracts all supported types.
                      Supported types by language:

                      Python (.py):
                      - "function": Regular functions (def name(...))
                      - "async_function": Async functions (async def name(...))
                      - "class": Class definitions (class Name(...))
                      - "method": Class methods (functions inside classes)
                      - "async_method": Async class methods

                      Go (.go):
                      - "function": Functions (func name(...))
                      - "method": Methods with receivers (func (r Type) name(...))
                      - "struct": Struct types (type Name struct {...})
                      - "interface": Interface types (type Name interface {...})

                      Java (.java):
                      - "class": Class definitions (class Name {...})
                      - "interface": Interface definitions (interface Name {...})
                      - "method": Methods inside classes/interfaces

                      JavaScript/TypeScript (.js, .ts, .jsx, .tsx):
                      - "function": Regular functions (function name(...))
                      - "async_function": Async functions (async function name(...))
                      - "class": ES6 classes (class Name {...})
                      - "method": Class methods
                      - "interface": TypeScript interfaces (interface Name {...})
                      - "type": TypeScript type aliases (type Name = ...)

                      C/C++ (.c, .cpp, .h, .hpp):
                      - "function": Functions (return_type name(...))
                      - "struct": Struct definitions (struct name {...})
                      - "class": C++ classes (class name {...})
                      - "namespace": C++ namespaces (namespace name {...})

        include_docstrings: Whether to include documentation/comments
        include_decorators: Whether to include decorators/annotations (Python, Java, TypeScript)
        include_line_numbers: Whether to include line numbers
        language: Force specific language detection (auto-detected from file extension if None)

    Returns:
        str: Basic analysis of code elements using regex patterns (less accurate than Tree-sitter)

    Examples:
        >>> parse_code_with_regex("src/utils.py", ["function", "class"])
        >>> parse_code_with_regex("main.go", ["function", "struct"])
        >>> parse_code_with_regex("app.ts", ["function", "class", "interface"])
        >>> parse_code_with_regex("service.java", ["class", "method"])
    """
    # Validate inputs
    if not file_path or not file_path.strip():
        raise ValueError("file_path is required and cannot be empty")

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File '{file_path}' does not exist")

    # Detect language
    detected_language = language or _detect_language(path)
    if detected_language not in SUPPORTED_LANGUAGES:
        return f"❌ Language '{detected_language}' not supported by regex parser.\n✅ Supported: {', '.join(SUPPORTED_LANGUAGES)}"

    # Set default element types
    if element_types is None:
        element_types = _get_default_element_types(detected_language)

    try:
        # Read source code
        with open(path, 'r', encoding='utf-8') as f:
            source_code = f.read()

        # Extract elements based on language
        elements = _extract_elements_by_language(
            source_code, detected_language, element_types,
            include_docstrings, include_decorators, include_line_numbers
        )

        # Format output
        result = f"Regex Analysis for: {file_path} ({detected_language.upper()})\n"
        result += "=" * 70 + "\n"
        result += "Parser: Regex patterns (fallback)\n"
        result += f"Language: {detected_language}\n"
        result += f"Elements found: {len(elements)}\n"
        result += "=" * 70 + "\n\n"

        if not elements:
            result += "No code elements found matching the specified criteria.\n"
            result += f"Searched for: {', '.join(element_types)}\n"
            return result

        for i, element in enumerate(elements, 1):
            result += f"[{i}/{len(elements)}] "
            result += _format_regex_element(element) + "\n\n"

        result += f"Successfully parsed {len(elements)} elements using regex patterns\n"
        return result

    except Exception as e:
        return f"❌ Error parsing {detected_language} file '{file_path}' with regex: {e}"


def _detect_language(path: Path) -> str:
    """Detect programming language from file extension."""
    suffix = path.suffix.lower()
    return LANGUAGE_EXTENSIONS.get(suffix, 'unknown')


def _get_default_element_types(language: str) -> List[str]:
    """Get default element types for each language."""
    defaults = {
        'python': ['function', 'class', 'method', 'async_function'],
        'go': ['function', 'struct', 'interface', 'method'],
        'java': ['class', 'method', 'interface'],
        'c': ['function', 'struct'],
        'cpp': ['function', 'class', 'struct', 'namespace'],
        'javascript': ['function', 'class', 'method', 'async_function'],
        'typescript': ['function', 'class', 'interface', 'method', 'type']
    }
    return defaults.get(language, ['function', 'class'])


def _extract_elements_by_language(
    source_code: str, language: str, element_types: List[str],
    include_docstrings: bool, include_decorators: bool, include_line_numbers: bool
) -> List[Dict[str, Any]]:
    """Extract code elements based on the programming language."""

    if language == 'python':
        return _extract_python_elements(source_code, element_types, include_docstrings, include_decorators, include_line_numbers)
    elif language == 'go':
        return _extract_go_elements(source_code, element_types, include_docstrings, include_line_numbers)
    elif language == 'java':
        return _extract_java_elements(source_code, element_types, include_docstrings, include_decorators, include_line_numbers)
    elif language in ['c', 'cpp']:
        return _extract_c_cpp_elements(source_code, language, element_types, include_docstrings, include_line_numbers)
    elif language in ['javascript', 'typescript']:
        return _extract_js_ts_elements(source_code, language, element_types, include_docstrings, include_decorators, include_line_numbers)
    else:
        return []


def _extract_python_elements(
    source_code: str, element_types: List[str],
    include_docstrings: bool, include_decorators: bool, include_line_numbers: bool
) -> List[Dict[str, Any]]:
    """Extract elements from Python source code using AST (most accurate for Python)."""
    try:
        tree = ast.parse(source_code)
        elements = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and 'function' in element_types:
                elements.append(_extract_python_function_info(node, include_docstrings, include_decorators, include_line_numbers))
            elif isinstance(node, ast.AsyncFunctionDef) and 'async_function' in element_types:
                elements.append(_extract_python_async_function_info(node, include_docstrings, include_decorators, include_line_numbers))
            elif isinstance(node, ast.ClassDef) and 'class' in element_types:
                elements.append(_extract_python_class_info(node, include_docstrings, include_decorators, include_line_numbers))

        return elements
    except SyntaxError:
        # Fall back to regex if AST parsing fails
        return _extract_python_regex(source_code, element_types, include_docstrings, include_line_numbers)


def _extract_python_function_info(node: ast.FunctionDef, include_docstrings: bool, include_decorators: bool, include_line_numbers: bool) -> Dict[str, Any]:
    """Extract Python function information from AST node."""
    info = {
        'type': 'function',
        'name': node.name,
        'language': 'python',
        'is_async': False
    }

    if include_line_numbers:
        info['line_start'] = node.lineno
        info['line_end'] = node.end_lineno

    if include_docstrings:
        docstring = ast.get_docstring(node)
        if docstring:
            info['docstring'] = docstring

    if include_decorators and node.decorator_list:
        info['decorators'] = [_get_decorator_name(dec) for dec in node.decorator_list]

    # Extract arguments
    if node.args.args:
        info['parameters'] = [arg.arg for arg in node.args.args]

    # Extract return annotation
    if node.returns:
        info['returns'] = ast.unparse(node.returns)

    return info


def _extract_python_async_function_info(node: ast.AsyncFunctionDef, include_docstrings: bool, include_decorators: bool, include_line_numbers: bool) -> Dict[str, Any]:
    """Extract Python async function information."""
    info = _extract_python_function_info(node, include_docstrings, include_decorators, include_line_numbers)
    info['type'] = 'async_function'
    info['is_async'] = True
    return info


def _extract_python_class_info(node: ast.ClassDef, include_docstrings: bool, include_decorators: bool, include_line_numbers: bool) -> Dict[str, Any]:
    """Extract Python class information."""
    info = {
        'type': 'class',
        'name': node.name,
        'language': 'python',
        'methods': []
    }

    if include_line_numbers:
        info['line_start'] = node.lineno
        info['line_end'] = node.end_lineno

    if include_docstrings:
        docstring = ast.get_docstring(node)
        if docstring:
            info['docstring'] = docstring

    if include_decorators and node.decorator_list:
        info['decorators'] = [_get_decorator_name(dec) for dec in node.decorator_list]

    # Extract base classes
    if node.bases:
        info['bases'] = [_get_base_name(base) for base in node.bases]

    # Extract methods
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            method_info = {
                'name': item.name,
                'type': 'async_method' if isinstance(item, ast.AsyncFunctionDef) else 'method',
                'line_start': item.lineno if include_line_numbers else None
            }
            info['methods'].append(method_info)

    return info


def _get_decorator_name(decorator) -> str:
    """Get decorator name as string."""
    if isinstance(decorator, ast.Name):
        return decorator.id
    elif isinstance(decorator, ast.Attribute):
        return ast.unparse(decorator)
    elif isinstance(decorator, ast.Call):
        return ast.unparse(decorator.func)
    else:
        return ast.unparse(decorator)


def _get_base_name(base) -> str:
    """Get base class name as string."""
    if isinstance(base, ast.Name):
        return base.id
    elif isinstance(base, ast.Attribute):
        return ast.unparse(base)
    else:
        return ast.unparse(base)


def _extract_python_regex(source_code: str, element_types: List[str], include_docstrings: bool, include_line_numbers: bool) -> List[Dict[str, Any]]:
    """Extract Python elements using regex as fallback."""
    elements = []
    lines = source_code.split('\n')

    # Python function pattern
    func_pattern = r'^(?:async\s+)?def\s+(\w+)\s*\('
    class_pattern = r'^class\s+(\w+)(?:\([^)]*\))?\s*:'

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if 'function' in element_types or 'async_function' in element_types:
            func_match = re.search(func_pattern, stripped)
            if func_match:
                is_async = stripped.startswith('async')
                func_type = 'async_function' if is_async else 'function'
                if func_type in element_types:
                    elements.append({
                        'type': func_type,
                        'name': func_match.group(1),
                        'language': 'python',
                        'is_async': is_async,
                        'line_start': i if include_line_numbers else None
                    })

        if 'class' in element_types:
            class_match = re.search(class_pattern, stripped)
            if class_match:
                elements.append({
                    'type': 'class',
                    'name': class_match.group(1),
                    'language': 'python',
                    'line_start': i if include_line_numbers else None
                })

    return elements


def _extract_go_elements(source_code: str, element_types: List[str], include_docstrings: bool, include_line_numbers: bool) -> List[Dict[str, Any]]:
    """Extract Go elements using regex patterns."""
    elements = []
    lines = source_code.split('\n')

    # Go patterns
    func_pattern = r'func\s*(?:\([^)]*\))?\s*(\w+)\s*\([^)]*\)(?:\s*\([^)]*\))?\s*{'
    struct_pattern = r'type\s+(\w+)\s+struct\s*{'
    interface_pattern = r'type\s+(\w+)\s+interface\s*{'

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if 'function' in element_types:
            func_match = re.search(func_pattern, stripped)
            if func_match:
                elements.append({
                    'type': 'function',
                    'name': func_match.group(1),
                    'language': 'go',
                    'line_start': i if include_line_numbers else None,
                    'docstring': _extract_go_comment(lines, i-1) if include_docstrings else None
                })

        if 'struct' in element_types:
            struct_match = re.search(struct_pattern, stripped)
            if struct_match:
                elements.append({
                    'type': 'struct',
                    'name': struct_match.group(1),
                    'language': 'go',
                    'line_start': i if include_line_numbers else None,
                    'docstring': _extract_go_comment(lines, i-1) if include_docstrings else None
                })

        if 'interface' in element_types:
            interface_match = re.search(interface_pattern, stripped)
            if interface_match:
                elements.append({
                    'type': 'interface',
                    'name': interface_match.group(1),
                    'language': 'go',
                    'line_start': i if include_line_numbers else None,
                    'docstring': _extract_go_comment(lines, i-1) if include_docstrings else None
                })

    return elements


def _extract_go_comment(lines: List[str], line_index: int) -> Optional[str]:
    """Extract Go comment above a declaration."""
    if line_index < 0:
        return None

    comments = []
    i = line_index
    while i >= 0 and (lines[i].strip().startswith('//') or lines[i].strip() == ''):
        if lines[i].strip().startswith('//'):
            comments.insert(0, lines[i].strip()[2:].strip())
        i -= 1

    return '\n'.join(comments) if comments else None


def _extract_java_elements(source_code: str, element_types: List[str], include_docstrings: bool, include_decorators: bool, include_line_numbers: bool) -> List[Dict[str, Any]]:
    """Extract Java elements using regex patterns."""
    elements = []
    lines = source_code.split('\n')

    # Java patterns
    class_pattern = r'(?:public|private|protected)?\s*(?:abstract|final)?\s*class\s+(\w+)'
    interface_pattern = r'(?:public|private|protected)?\s*interface\s+(\w+)'
    method_pattern = r'(?:public|private|protected)?\s*(?:static)?\s*(?:final)?\s*(?:\w+\s+)?(\w+)\s*\([^)]*\)\s*(?:throws\s+[^{]+)?\s*{'

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if 'class' in element_types:
            class_match = re.search(class_pattern, stripped)
            if class_match:
                elements.append({
                    'type': 'class',
                    'name': class_match.group(1),
                    'language': 'java',
                    'line_start': i if include_line_numbers else None,
                    'docstring': _extract_java_javadoc(lines, i-1) if include_docstrings else None,
                    'annotations': _extract_java_annotations(lines, i-1) if include_decorators else None
                })

        if 'interface' in element_types:
            interface_match = re.search(interface_pattern, stripped)
            if interface_match:
                elements.append({
                    'type': 'interface',
                    'name': interface_match.group(1),
                    'language': 'java',
                    'line_start': i if include_line_numbers else None,
                    'docstring': _extract_java_javadoc(lines, i-1) if include_docstrings else None,
                    'annotations': _extract_java_annotations(lines, i-1) if include_decorators else None
                })

        if 'method' in element_types and not stripped.startswith('class') and not stripped.startswith('interface'):
            method_match = re.search(method_pattern, stripped)
            if method_match and method_match.group(1) not in ['class', 'interface', 'if', 'for', 'while']:
                elements.append({
                    'type': 'method',
                    'name': method_match.group(1),
                    'language': 'java',
                    'line_start': i if include_line_numbers else None,
                    'docstring': _extract_java_javadoc(lines, i-1) if include_docstrings else None,
                    'annotations': _extract_java_annotations(lines, i-1) if include_decorators else None
                })

    return elements


def _extract_java_javadoc(lines: List[str], line_index: int) -> Optional[str]:
    """Extract JavaDoc comment above a declaration."""
    if line_index < 0:
        return None

    javadoc_lines = []
    i = line_index
    in_javadoc = False

    while i >= 0:
        line = lines[i].strip()
        if line.endswith('*/'):
            in_javadoc = True
            javadoc_lines.insert(0, line[:-2].strip())
        elif in_javadoc:
            if line.startswith('/**'):
                javadoc_lines.insert(0, line[3:].strip())
                break
            elif line.startswith('*'):
                javadoc_lines.insert(0, line[1:].strip())
            else:
                javadoc_lines.insert(0, line)
        elif line == '':
            pass
        else:
            break
        i -= 1

    return '\n'.join(javadoc_lines) if javadoc_lines else None


def _extract_java_annotations(lines: List[str], line_index: int) -> Optional[List[str]]:
    """Extract Java annotations above a declaration."""
    if line_index < 0:
        return None

    annotations = []
    i = line_index

    while i >= 0:
        line = lines[i].strip()
        if line.startswith('@'):
            annotations.insert(0, line)
        elif line == '' or line.startswith('//') or line.startswith('/*'):
            pass
        else:
            break
        i -= 1

    return annotations if annotations else None


def _extract_c_cpp_elements(source_code: str, language: str, element_types: List[str], include_docstrings: bool, include_line_numbers: bool) -> List[Dict[str, Any]]:
    """Extract C/C++ elements using regex patterns."""
    elements = []
    lines = source_code.split('\n')

    # C/C++ patterns
    func_pattern = r'(?:static\s+)?(?:inline\s+)?(?:\w+\s+)*(\w+)\s*\([^)]*\)\s*{'
    struct_pattern = r'struct\s+(\w+)\s*{'
    class_pattern = r'class\s+(\w+)(?:\s*:\s*[^{]+)?\s*{'
    namespace_pattern = r'namespace\s+(\w+)\s*{'

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Skip preprocessor directives and comments
        if stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('/*'):
            continue

        if 'function' in element_types:
            func_match = re.search(func_pattern, stripped)
            if func_match and func_match.group(1) not in ['if', 'for', 'while', 'switch', 'struct', 'class']:
                elements.append({
                    'type': 'function',
                    'name': func_match.group(1),
                    'language': language,
                    'line_start': i if include_line_numbers else None,
                    'docstring': _extract_c_comment(lines, i-1) if include_docstrings else None
                })

        if 'struct' in element_types:
            struct_match = re.search(struct_pattern, stripped)
            if struct_match:
                elements.append({
                    'type': 'struct',
                    'name': struct_match.group(1),
                    'language': language,
                    'line_start': i if include_line_numbers else None,
                    'docstring': _extract_c_comment(lines, i-1) if include_docstrings else None
                })

        if language == 'cpp' and 'class' in element_types:
            class_match = re.search(class_pattern, stripped)
            if class_match:
                elements.append({
                    'type': 'class',
                    'name': class_match.group(1),
                    'language': language,
                    'line_start': i if include_line_numbers else None,
                    'docstring': _extract_c_comment(lines, i-1) if include_docstrings else None
                })

        if language == 'cpp' and 'namespace' in element_types:
            namespace_match = re.search(namespace_pattern, stripped)
            if namespace_match:
                elements.append({
                    'type': 'namespace',
                    'name': namespace_match.group(1),
                    'language': language,
                    'line_start': i if include_line_numbers else None,
                    'docstring': _extract_c_comment(lines, i-1) if include_docstrings else None
                })

    return elements


def _extract_c_comment(lines: List[str], line_index: int) -> Optional[str]:
    """Extract C/C++ comment above a declaration."""
    if line_index < 0:
        return None

    comments = []
    i = line_index

    while i >= 0:
        line = lines[i].strip()
        if line.startswith('//'):
            comments.insert(0, line[2:].strip())
        elif line.startswith('/*') and line.endswith('*/'):
            comments.insert(0, line[2:-2].strip())
        elif line == '':
            pass
        else:
            break
        i -= 1

    return '\n'.join(comments) if comments else None


def _extract_js_ts_elements(source_code: str, language: str, element_types: List[str], include_docstrings: bool, include_decorators: bool, include_line_numbers: bool) -> List[Dict[str, Any]]:
    """Extract JavaScript/TypeScript elements using regex patterns."""
    elements = []
    lines = source_code.split('\n')

    # JS/TS patterns
    func_patterns = [
        r'function\s+(\w+)\s*\([^)]*\)',
        r'const\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>',
        r'(\w+)\s*:\s*(?:async\s+)?\([^)]*\)\s*=>',
        r'(\w+)\s*\([^)]*\)\s*{'
    ]
    class_pattern = r'class\s+(\w+)(?:\s+extends\s+\w+)?\s*{'
    interface_pattern = r'interface\s+(\w+)(?:\s+extends\s+[^{]+)?\s*{'
    type_pattern = r'type\s+(\w+)\s*='

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if stripped.startswith('//') or stripped.startswith('/*'):
            continue

        if 'function' in element_types or 'async_function' in element_types:
            for pattern in func_patterns:
                func_match = re.search(pattern, stripped)
                if func_match:
                    is_async = 'async' in stripped
                    func_type = 'async_function' if is_async else 'function'

                    if func_type in element_types:
                        elements.append({
                            'type': func_type,
                            'name': func_match.group(1),
                            'language': language,
                            'line_start': i if include_line_numbers else None,
                            'is_async': is_async,
                            'docstring': _extract_js_comment(lines, i-1) if include_docstrings else None,
                            'decorators': _extract_js_decorators(lines, i-1) if include_decorators else None
                        })
                    break

        if 'class' in element_types:
            class_match = re.search(class_pattern, stripped)
            if class_match:
                elements.append({
                    'type': 'class',
                    'name': class_match.group(1),
                    'language': language,
                    'line_start': i if include_line_numbers else None,
                    'docstring': _extract_js_comment(lines, i-1) if include_docstrings else None,
                    'decorators': _extract_js_decorators(lines, i-1) if include_decorators else None
                })

        if language == 'typescript' and 'interface' in element_types:
            interface_match = re.search(interface_pattern, stripped)
            if interface_match:
                elements.append({
                    'type': 'interface',
                    'name': interface_match.group(1),
                    'language': language,
                    'line_start': i if include_line_numbers else None,
                    'docstring': _extract_js_comment(lines, i-1) if include_docstrings else None
                })

        if language == 'typescript' and 'type' in element_types:
            type_match = re.search(type_pattern, stripped)
            if type_match:
                elements.append({
                    'type': 'type',
                    'name': type_match.group(1),
                    'language': language,
                    'line_start': i if include_line_numbers else None,
                    'docstring': _extract_js_comment(lines, i-1) if include_docstrings else None
                })

    return elements


def _extract_js_comment(lines: List[str], line_index: int) -> Optional[str]:
    """Extract JavaScript/TypeScript comment above a declaration."""
    if line_index < 0:
        return None

    comments = []
    i = line_index

    while i >= 0:
        line = lines[i].strip()
        if line.startswith('//'):
            comments.insert(0, line[2:].strip())
        elif line.startswith('/**') and line.endswith('*/'):
            comments.insert(0, line[3:-2].strip())
        elif line.startswith('/*') and line.endswith('*/'):
            comments.insert(0, line[2:-2].strip())
        elif line == '':
            pass
        else:
            break
        i -= 1

    return '\n'.join(comments) if comments else None


def _extract_js_decorators(lines: List[str], line_index: int) -> Optional[List[str]]:
    """Extract JavaScript/TypeScript decorators above a declaration."""
    if line_index < 0:
        return None

    decorators = []
    i = line_index

    while i >= 0:
        line = lines[i].strip()
        if line.startswith('@'):
            decorators.insert(0, line)
        elif line == '' or line.startswith('//') or line.startswith('/*'):
            pass
        else:
            break
        i -= 1

    return decorators if decorators else None


def _format_regex_element(element: Dict[str, Any]) -> str:
    """Format regex parsed element for display (simplified)."""
    language = element.get('language', 'unknown')
    result = f"{element['type'].upper()}: {element['name']}\n"

    # Line numbers
    if element.get('line_start'):
        result += f"   Line: {element['line_start']}\n"

    # Language and parser info
    result += f"   Language: {language}\n"
    result += "   Parser: Regex patterns\n"

    # Function/method specific info
    if element['type'] in ['function', 'async_function', 'method', 'async_method']:
        if element.get('is_async'):
            result += "   Async: Yes\n"

        if element.get('parameters'):
            params_str = ', '.join(element['parameters'][:3])
            if len(element['parameters']) > 3:
                params_str += f", ... (+{len(element['parameters']) - 3} more)"
            result += f"   Parameters: {params_str}\n"

        if element.get('returns'):
            result += f"   Returns: {element['returns']}\n"

    # Class specific info
    elif element['type'] == 'class':
        if element.get('bases'):
            result += f"   Extends: {', '.join(element['bases'])}\n"

        if element.get('methods'):
            result += f"   Methods: {len(element['methods'])} found\n"

    # Decorators/annotations
    if element.get('decorators'):
        result += f"   Decorators: {', '.join(element['decorators'])}\n"

    if element.get('annotations'):
        result += f"   Annotations: {', '.join(element['annotations'])}\n"

    # Documentation
    if element.get('docstring') and element['docstring'].strip():
        docstring = element['docstring'][:80] + "..." if len(element['docstring']) > 80 else element['docstring']
        result += f"   Documentation: {docstring}\n"

    return result
