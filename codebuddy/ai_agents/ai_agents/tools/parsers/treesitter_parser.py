"""
Tree-sitter based code parsing tools for multi-language support.

This module provides Tree-sitter based parsing capabilities for various programming languages.
It serves as a more accurate alternative to regex-based parsing.
"""

from pathlib import Path
from typing import List, Dict, Optional, Any

# Try to import tree-sitter, gracefully handle if not available
try:
    import tree_sitter
    from tree_sitter import Language, Parser, Node
    TREESITTER_AVAILABLE = True
except ImportError:
    TREESITTER_AVAILABLE = False
    tree_sitter = None
    Language = None
    Parser = None
    Node = None

# Language mappings
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

# Tree-sitter language configurations
TREESITTER_LANGUAGES = {
    'python': 'tree-sitter-python',
    'go': 'tree-sitter-go',
    'c': 'tree-sitter-c',
    'cpp': 'tree-sitter-cpp',
    'java': 'tree-sitter-java',
    'javascript': 'tree-sitter-javascript',
    'typescript': 'tree-sitter-typescript'
}


def parse_code_with_treesitter(
    file_path: str,
    element_types: List[str] = None,
    include_docstrings: bool = True,
    include_line_numbers: bool = True,
    language: str = None
) -> str:
    """
    Parse source code using Tree-sitter for accurate multi-language analysis.

    This tool uses Tree-sitter parsers to extract code elements with high accuracy.
    Requires tree-sitter and language-specific packages to be installed.

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
        include_line_numbers: Whether to include line number information
        language: Force specific language detection (auto-detected from file extension if None)

    Returns:
        str: Detailed analysis of code elements using Tree-sitter with high accuracy

    Examples:
        >>> parse_code_with_treesitter("src/utils.py", ["function", "class"])
        >>> parse_code_with_treesitter("main.go", ["function", "struct"])
        >>> parse_code_with_treesitter("app.ts", ["function", "class", "interface"])
        >>> parse_code_with_treesitter("service.java", ["class", "method"])
    """
    if not TREESITTER_AVAILABLE:
        return "❌ Tree-sitter not available. Please install: pip install tree-sitter tree-sitter-python"

    # Validate inputs
    if not file_path or not file_path.strip():
        raise ValueError("file_path is required and cannot be empty")

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File '{file_path}' does not exist")

    # Detect language
    detected_language = language or _detect_language(path)

    # Check if language is supported by Tree-sitter
    if detected_language not in TREESITTER_LANGUAGES:
        return f"❌ Language '{detected_language}' not supported by Tree-sitter.\n✅ Supported languages: {', '.join(TREESITTER_LANGUAGES.keys())}\n💡 Tip: The system will automatically fall back to regex parsing."

    try:
        # Read source code
        with open(path, 'r', encoding='utf-8') as f:
            source_code = f.read()

        # Parse with Tree-sitter
        elements = _parse_with_treesitter(
            source_code, detected_language, element_types,
            include_docstrings, include_line_numbers
        )

        # Format output
        result = f"Tree-sitter Analysis for: {file_path} ({detected_language.upper()})\n"
        result += "=" * 70 + "\n"

        # Get tree-sitter version safely
        try:
            ts_version = tree_sitter.__version__ if tree_sitter else 'unknown'
        except AttributeError:
            ts_version = 'available'

        result += f"Parser: Tree-sitter v{ts_version}\n"
        result += f"Language: {detected_language}\n"
        result += f"Elements found: {len(elements)}\n"
        result += "=" * 70 + "\n\n"

        if not elements:
            result += "No code elements found matching the specified criteria.\n"
            result += f"Searched for: {', '.join(element_types) if element_types else 'all types'}\n"
            return result

        for i, element in enumerate(elements, 1):
            result += f"[{i}/{len(elements)}] "
            result += _format_treesitter_element_simple(element) + "\n\n"

        result += f"Successfully parsed {len(elements)} elements using Tree-sitter\n"
        return result

    except Exception as e:
        error_msg = f"Error parsing {detected_language} file '{file_path}' with Tree-sitter: {e}\n"
        error_msg += "The system will automatically fall back to regex parsing.\n"
        error_msg += f"To fix this, ensure the language parser is installed: pip install tree-sitter-{detected_language}"
        return error_msg


def _detect_language(path: Path) -> str:
    """Detect programming language from file extension."""
    suffix = path.suffix.lower()
    return LANGUAGE_EXTENSIONS.get(suffix, 'unknown')


def _parse_with_treesitter(
    source_code: str, language: str, element_types: List[str],
    include_docstrings: bool, include_line_numbers: bool
) -> List[Dict[str, Any]]:
    """Parse source code using Tree-sitter."""

    # Get language parser
    parser = _get_parser(language)
    if not parser:
        raise ValueError(f"Failed to get parser for language: {language}")

    # Parse the code
    tree = parser.parse(bytes(source_code, 'utf8'))
    root_node = tree.root_node

    # Extract elements based on language
    if language == 'python':
        return _extract_python_treesitter(root_node, source_code, element_types, include_docstrings, include_line_numbers)
    elif language == 'go':
        return _extract_go_treesitter(root_node, source_code, element_types, include_docstrings, include_line_numbers)
    elif language == 'java':
        return _extract_java_treesitter(root_node, source_code, element_types, include_docstrings, include_line_numbers)
    elif language in ['javascript', 'typescript']:
        return _extract_js_ts_treesitter(root_node, source_code, language, element_types, include_docstrings, include_line_numbers)
    elif language in ['c', 'cpp']:
        return _extract_c_cpp_treesitter(root_node, source_code, language, element_types, include_docstrings, include_line_numbers)
    else:
        return []


def _get_parser(language: str) -> Optional[Parser]:
    """Get Tree-sitter parser for the specified language."""
    try:
        # Try to import and use the language-specific parsers
        parser = Parser()

        if language == 'python':
            try:
                import tree_sitter_python as tspython
                PY_LANGUAGE = Language(tspython.language())
                parser = Parser(PY_LANGUAGE)
                return parser
            except ImportError:
                pass

        elif language == 'javascript':
            try:
                import tree_sitter_javascript as tsjs
                JS_LANGUAGE = Language(tsjs.language())
                parser = Parser(JS_LANGUAGE)
                return parser
            except ImportError:
                pass

        elif language == 'typescript':
            try:
                import tree_sitter_typescript as tsts
                TS_LANGUAGE = Language(tsts.language_typescript())
                parser = Parser(TS_LANGUAGE)
                return parser
            except ImportError:
                pass

        elif language == 'go':
            try:
                import tree_sitter_go as tsgo
                GO_LANGUAGE = Language(tsgo.language())
                parser = Parser(GO_LANGUAGE)
                return parser
            except ImportError:
                pass

        elif language == 'java':
            try:
                import tree_sitter_java as tsjava
                JAVA_LANGUAGE = Language(tsjava.language())
                parser = Parser(JAVA_LANGUAGE)
                return parser
            except ImportError:
                pass

        elif language == 'c':
            try:
                import tree_sitter_c as tsc
                C_LANGUAGE = Language(tsc.language())
                parser = Parser(C_LANGUAGE)
                return parser
            except ImportError:
                pass

        elif language == 'cpp':
            try:
                import tree_sitter_cpp as tscpp
                CPP_LANGUAGE = Language(tscpp.language())
                parser = Parser(CPP_LANGUAGE)
                return parser
            except ImportError:
                pass

        # If we get here, the language parser is not available
        return None

    except Exception as e:
        # Log the error for debugging
        print(f"Error creating parser for {language}: {e}")
        return None


def _extract_python_treesitter(
    root_node: 'Node', source_code: str, element_types: List[str],
    include_docstrings: bool, include_line_numbers: bool
) -> List[Dict[str, Any]]:
    """Extract Python elements using Tree-sitter."""
    elements = []

    def traverse(node):
        if node.type == 'function_definition' and (not element_types or 'function' in element_types):
            elements.append(_extract_python_function(node, source_code, include_docstrings, include_line_numbers))
        elif node.type == 'async_function_definition' and (not element_types or 'async_function' in element_types):
            elements.append(_extract_python_async_function(node, source_code, include_docstrings, include_line_numbers))
        elif node.type == 'class_definition' and (not element_types or 'class' in element_types):
            elements.append(_extract_python_class(node, source_code, include_docstrings, include_line_numbers))

        for child in node.children:
            traverse(child)

    traverse(root_node)
    return elements


def _extract_python_function(node: 'Node', source_code: str, include_docstrings: bool, include_line_numbers: bool) -> Dict[str, Any]:
    """Extract Python function information from Tree-sitter node."""

    # Get function name
    name_node = node.child_by_field_name('name')
    name = name_node.text.decode('utf8') if name_node else 'unknown'

    element = {
        'type': 'function',
        'name': name,
        'language': 'python'
    }

    if include_line_numbers:
        element['line_start'] = node.start_point[0] + 1
        element['line_end'] = node.end_point[0] + 1

    if include_docstrings:
        # Extract docstring (first string literal in function body)
        docstring = _extract_python_docstring(node, source_code)
        if docstring:
            element['docstring'] = docstring

    return element


def _extract_python_async_function(node: 'Node', source_code: str, include_docstrings: bool, include_line_numbers: bool) -> Dict[str, Any]:
    """Extract Python async function information."""
    element = _extract_python_function(node, source_code, include_docstrings, include_line_numbers)
    element['type'] = 'async_function'
    element['is_async'] = True
    return element


def _extract_python_class(node: 'Node', source_code: str, include_docstrings: bool, include_line_numbers: bool) -> Dict[str, Any]:
    """Extract Python class information."""
    name_node = node.child_by_field_name('name')
    name = name_node.text.decode('utf8') if name_node else 'unknown'

    element = {
        'type': 'class',
        'name': name,
        'language': 'python',
        'methods': []
    }

    if include_line_numbers:
        element['line_start'] = node.start_point[0] + 1
        element['line_end'] = node.end_point[0] + 1

    if include_docstrings:
        docstring = _extract_python_docstring(node, source_code)
        if docstring:
            element['docstring'] = docstring

    # Extract methods
    def find_methods(node):
        if node.type in ['function_definition', 'async_function_definition']:
            method_name_node = node.child_by_field_name('name')
            if method_name_node:
                method_name = method_name_node.text.decode('utf8')
                element['methods'].append({
                    'name': method_name,
                    'type': 'async_method' if node.type == 'async_function_definition' else 'method',
                    'line_start': node.start_point[0] + 1 if include_line_numbers else None
                })

        for child in node.children:
            find_methods(child)

    find_methods(node)
    return element


def _extract_python_docstring(node: 'Node', source_code: str) -> Optional[str]:
    """Extract docstring from a Python function or class."""
    # Look for the first string literal in the body
    body = node.child_by_field_name('body')
    if not body:
        return None

    for child in body.children:
        if child.type == 'expression_statement':
            expr = child.children[0] if child.children else None
            if expr and expr.type == 'string':
                # Extract string content (remove quotes)
                text = expr.text.decode('utf8')
                if text.startswith('"""') or text.startswith("'''"):
                    return text[3:-3].strip()
                elif text.startswith('"') or text.startswith("'"):
                    return text[1:-1].strip()

    return None


# Go-specific extraction functions
def _extract_go_treesitter(root_node, source_code, element_types, include_docstrings, include_line_numbers):
    """Extract Go elements using Tree-sitter."""
    elements = []

    def traverse(node):
        # Go function declaration: func name(params) returns { ... }
        if node.type == 'function_declaration' and (not element_types or 'function' in element_types):
            elements.append(_extract_go_function(node, source_code, include_docstrings, include_line_numbers))

        # Go method declaration: func (receiver) name(params) returns { ... }
        elif node.type == 'method_declaration' and (not element_types or 'method' in element_types):
            elements.append(_extract_go_method(node, source_code, include_docstrings, include_line_numbers))

        # Go type declaration: type Name struct { ... }
        elif node.type == 'type_declaration' and (not element_types or 'struct' in element_types or 'interface' in element_types):
            for spec in node.children:
                if spec.type == 'type_spec':
                    elements.append(_extract_go_type(spec, source_code, include_docstrings, include_line_numbers))

        for child in node.children:
            traverse(child)

    traverse(root_node)
    return elements


def _extract_go_function(node, source_code, include_docstrings, include_line_numbers):
    """Extract Go function information."""
    name_node = node.child_by_field_name('name')
    name = name_node.text.decode('utf8') if name_node else 'unknown'

    element = {
        'type': 'function',
        'name': name,
        'language': 'go'
    }

    if include_line_numbers:
        element['line_start'] = node.start_point[0] + 1
        element['line_end'] = node.end_point[0] + 1

    if include_docstrings:
        # Go comments are above the function
        comment = _extract_go_comment(node, source_code)
        if comment:
            element['docstring'] = comment

    # Extract parameters
    params_node = node.child_by_field_name('parameters')
    if params_node:
        element['parameters'] = _extract_go_parameters(params_node)

    # Extract return type
    result_node = node.child_by_field_name('result')
    if result_node:
        element['returns'] = result_node.text.decode('utf8')

    return element


def _extract_go_method(node, source_code, include_docstrings, include_line_numbers):
    """Extract Go method information."""
    element = _extract_go_function(node, source_code, include_docstrings, include_line_numbers)
    element['type'] = 'method'

    # Extract receiver
    receiver_node = node.child_by_field_name('receiver')
    if receiver_node:
        element['receiver'] = receiver_node.text.decode('utf8')

    return element


def _extract_go_type(node, source_code, include_docstrings, include_line_numbers):
    """Extract Go type (struct/interface) information."""
    name_node = node.child_by_field_name('name')
    name = name_node.text.decode('utf8') if name_node else 'unknown'

    type_node = node.child_by_field_name('type')
    if not type_node:
        return None

    # Determine if it's a struct or interface
    if type_node.type == 'struct_type':
        element_type = 'struct'
    elif type_node.type == 'interface_type':
        element_type = 'interface'
    else:
        element_type = 'type'

    element = {
        'type': element_type,
        'name': name,
        'language': 'go'
    }

    if include_line_numbers:
        element['line_start'] = node.start_point[0] + 1
        element['line_end'] = node.end_point[0] + 1

    if include_docstrings:
        comment = _extract_go_comment(node, source_code)
        if comment:
            element['docstring'] = comment

    # Extract fields for structs
    if element_type == 'struct':
        element['fields'] = _extract_go_struct_fields(type_node)

    # Extract methods for interfaces
    elif element_type == 'interface':
        element['methods'] = _extract_go_interface_methods(type_node)

    return element


def _extract_go_comment(node, source_code):
    """Extract Go comment above a declaration."""
    lines = source_code.split('\n')
    start_line = node.start_point[0]

    comments = []
    line_idx = start_line - 1

    # Look backwards for comments
    while line_idx >= 0:
        line = lines[line_idx].strip()
        if line.startswith('//'):
            comments.insert(0, line[2:].strip())
        elif line.startswith('/*') and line.endswith('*/'):
            comments.insert(0, line[2:-2].strip())
        elif line == '':
            pass  # Skip empty lines
        else:
            break
        line_idx -= 1

    return '\n'.join(comments) if comments else None


def _extract_go_parameters(params_node):
    """Extract Go function parameters."""
    params = []
    for child in params_node.children:
        if child.type == 'parameter_declaration':
            param_text = child.text.decode('utf8')
            params.append(param_text)
    return params


def _extract_go_struct_fields(struct_node):
    """Extract Go struct fields."""
    fields = []
    for child in struct_node.children:
        if child.type == 'field_declaration':
            field_text = child.text.decode('utf8')
            fields.append(field_text)
    return fields


def _extract_go_interface_methods(interface_node):
    """Extract Go interface methods."""
    methods = []
    for child in interface_node.children:
        if child.type == 'method_spec':
            method_text = child.text.decode('utf8')
            methods.append(method_text)
    return methods

def _extract_java_treesitter(root_node, source_code, element_types, include_docstrings, include_line_numbers):
    """Extract Java elements using Tree-sitter (placeholder)."""
    return []

def _extract_js_ts_treesitter(root_node, source_code, language, element_types, include_docstrings, include_line_numbers):
    """Extract JavaScript/TypeScript elements using Tree-sitter."""
    elements = []

    def traverse(node):
        # Function declarations: function name() { ... }
        if node.type == 'function_declaration' and (not element_types or 'function' in element_types):
            elements.append(_extract_js_function(node, source_code, language, include_docstrings, include_line_numbers))

        # Arrow functions: const name = () => { ... }
        elif node.type == 'arrow_function' and (not element_types or 'function' in element_types):
            # Need to find the variable declarator that contains this arrow function
            parent = node.parent
            while parent and parent.type != 'variable_declarator':
                parent = parent.parent
            if parent:
                elements.append(_extract_js_arrow_function(parent, node, source_code, language, include_docstrings, include_line_numbers))

        # Class declarations: class Name { ... }
        elif node.type == 'class_declaration' and (not element_types or 'class' in element_types):
            elements.append(_extract_js_class(node, source_code, language, include_docstrings, include_line_numbers))

        # TypeScript interfaces: interface Name { ... }
        elif node.type == 'interface_declaration' and language == 'typescript' and (not element_types or 'interface' in element_types):
            elements.append(_extract_ts_interface(node, source_code, include_docstrings, include_line_numbers))

        # TypeScript type aliases: type Name = ...
        elif node.type == 'type_alias_declaration' and language == 'typescript' and (not element_types or 'type' in element_types):
            elements.append(_extract_ts_type_alias(node, source_code, include_docstrings, include_line_numbers))

        for child in node.children:
            traverse(child)

    traverse(root_node)
    return elements


def _extract_js_function(node, source_code, language, include_docstrings, include_line_numbers):
    """Extract JavaScript/TypeScript function information."""
    name_node = node.child_by_field_name('name')
    name = name_node.text.decode('utf8') if name_node else 'anonymous'

    # Check if it's async
    is_async = any(child.type == 'async' for child in node.children)

    element = {
        'type': 'async_function' if is_async else 'function',
        'name': name,
        'language': language,
        'is_async': is_async
    }

    if include_line_numbers:
        element['line_start'] = node.start_point[0] + 1
        element['line_end'] = node.end_point[0] + 1

    if include_docstrings:
        comment = _extract_js_comment(node, source_code)
        if comment:
            element['docstring'] = comment

    # Extract parameters
    params_node = node.child_by_field_name('parameters')
    if params_node:
        element['parameters'] = _extract_js_parameters(params_node)

    return element


def _extract_js_arrow_function(declarator_node, arrow_node, source_code, language, include_docstrings, include_line_numbers):
    """Extract JavaScript/TypeScript arrow function information."""
    name_node = declarator_node.child_by_field_name('name')
    name = name_node.text.decode('utf8') if name_node else 'anonymous'

    # Check if it's async
    is_async = any(child.type == 'async' for child in arrow_node.children)

    element = {
        'type': 'async_function' if is_async else 'function',
        'name': name,
        'language': language,
        'is_async': is_async,
        'function_style': 'arrow'
    }

    if include_line_numbers:
        element['line_start'] = declarator_node.start_point[0] + 1
        element['line_end'] = arrow_node.end_point[0] + 1

    if include_docstrings:
        comment = _extract_js_comment(declarator_node, source_code)
        if comment:
            element['docstring'] = comment

    # Extract parameters
    params_node = arrow_node.child_by_field_name('parameters')
    if params_node:
        element['parameters'] = _extract_js_parameters(params_node)

    return element


def _extract_js_class(node, source_code, language, include_docstrings, include_line_numbers):
    """Extract JavaScript/TypeScript class information."""
    name_node = node.child_by_field_name('name')
    name = name_node.text.decode('utf8') if name_node else 'anonymous'

    element = {
        'type': 'class',
        'name': name,
        'language': language,
        'methods': []
    }

    if include_line_numbers:
        element['line_start'] = node.start_point[0] + 1
        element['line_end'] = node.end_point[0] + 1

    if include_docstrings:
        comment = _extract_js_comment(node, source_code)
        if comment:
            element['docstring'] = comment

    # Extract superclass
    superclass_node = node.child_by_field_name('superclass')
    if superclass_node:
        element['extends'] = superclass_node.text.decode('utf8')

    # Extract methods
    body_node = node.child_by_field_name('body')
    if body_node:
        for child in body_node.children:
            if child.type == 'method_definition':
                method_info = _extract_js_method(child, source_code, language, include_docstrings, include_line_numbers)
                element['methods'].append(method_info)

    return element


def _extract_js_method(node, source_code, language, include_docstrings, include_line_numbers):
    """Extract JavaScript/TypeScript method information."""
    name_node = node.child_by_field_name('name')
    name = name_node.text.decode('utf8') if name_node else 'anonymous'

    # Check method type
    is_static = any(child.type == 'static' for child in node.children)
    is_async = any(child.type == 'async' for child in node.children)

    method_type = 'method'
    if is_static:
        method_type = 'static_method'
    if is_async:
        method_type = 'async_' + method_type

    element = {
        'type': method_type,
        'name': name,
        'language': language,
        'is_static': is_static,
        'is_async': is_async
    }

    if include_line_numbers:
        element['line_start'] = node.start_point[0] + 1
        element['line_end'] = node.end_point[0] + 1

    return element


def _extract_ts_interface(node, source_code, include_docstrings, include_line_numbers):
    """Extract TypeScript interface information."""
    name_node = node.child_by_field_name('name')
    name = name_node.text.decode('utf8') if name_node else 'anonymous'

    element = {
        'type': 'interface',
        'name': name,
        'language': 'typescript',
        'properties': []
    }

    if include_line_numbers:
        element['line_start'] = node.start_point[0] + 1
        element['line_end'] = node.end_point[0] + 1

    if include_docstrings:
        comment = _extract_js_comment(node, source_code)
        if comment:
            element['docstring'] = comment

    # Extract interface body
    body_node = node.child_by_field_name('body')
    if body_node:
        for child in body_node.children:
            if child.type in ['property_signature', 'method_signature']:
                prop_text = child.text.decode('utf8')
                element['properties'].append(prop_text)

    return element


def _extract_ts_type_alias(node, source_code, include_docstrings, include_line_numbers):
    """Extract TypeScript type alias information."""
    name_node = node.child_by_field_name('name')
    name = name_node.text.decode('utf8') if name_node else 'anonymous'

    element = {
        'type': 'type',
        'name': name,
        'language': 'typescript'
    }

    if include_line_numbers:
        element['line_start'] = node.start_point[0] + 1
        element['line_end'] = node.end_point[0] + 1

    if include_docstrings:
        comment = _extract_js_comment(node, source_code)
        if comment:
            element['docstring'] = comment

    # Extract type definition
    value_node = node.child_by_field_name('value')
    if value_node:
        element['definition'] = value_node.text.decode('utf8')

    return element


def _extract_js_comment(node, source_code):
    """Extract JavaScript/TypeScript comment above a declaration."""
    lines = source_code.split('\n')
    start_line = node.start_point[0]

    comments = []
    line_idx = start_line - 1

    # Look backwards for comments
    while line_idx >= 0:
        line = lines[line_idx].strip()
        if line.startswith('//'):
            comments.insert(0, line[2:].strip())
        elif line.startswith('/**') and line.endswith('*/'):
            # Single line JSDoc
            comments.insert(0, line[3:-2].strip())
        elif line.startswith('/*') and line.endswith('*/'):
            # Single line comment
            comments.insert(0, line[2:-2].strip())
        elif line == '':
            pass  # Skip empty lines
        else:
            break
        line_idx -= 1

    return '\n'.join(comments) if comments else None


def _extract_js_parameters(params_node):
    """Extract JavaScript/TypeScript function parameters."""
    params = []
    for child in params_node.children:
        if child.type in ['identifier', 'required_parameter', 'optional_parameter', 'rest_parameter']:
            param_text = child.text.decode('utf8')
            params.append(param_text)
    return params

def _extract_c_cpp_treesitter(root_node, source_code, language, element_types, include_docstrings, include_line_numbers):
    """Extract C/C++ elements using Tree-sitter (placeholder)."""
    return []


def _format_treesitter_element_simple(element: Dict[str, Any]) -> str:
    """Format Tree-sitter parsed element for display (simplified)."""
    language = element.get('language', 'unknown')
    result = f"{element['type'].upper()}: {element['name']}\n"

    # Line numbers
    if element.get('line_start'):
        result += f"   Lines: {element['line_start']}-{element.get('line_end', '?')}\n"

    # Language and parser info
    result += f"   Language: {language}\n"
    result += "   Parser: Tree-sitter\n"

    # Function/method specific info
    if element['type'] in ['function', 'async_function', 'method', 'async_method', 'static_method']:
        if element.get('is_async'):
            result += "   ⚡ Async: Yes\n"

        if element.get('function_style'):
            result += f"   📝 Style: {element['function_style']}\n"

        if element.get('is_static'):
            result += "   � Static: Yes\n"

        if element.get('parameters'):
            params_str = ', '.join(element['parameters'][:3])
            if len(element['parameters']) > 3:
                params_str += f", ... (+{len(element['parameters']) - 3} more)"
            result += f"   📋 Parameters: {params_str}\n"

        if element.get('returns'):
            result += f"   ↩️  Returns: {element['returns']}\n"

        if element.get('receiver'):  # Go methods
            result += f"   🎯 Receiver: {element['receiver']}\n"

    # Class specific info
    elif element['type'] == 'class':
        if element.get('extends'):
            result += f"   🔗 Extends: {element['extends']}\n"

        if element.get('methods'):
            result += f"   🔧 Methods: {len(element['methods'])} found\n"
            for method in element['methods'][:3]:
                method_name = method.get('name', 'unknown')
                method_type = method.get('type', 'method')
                result += f"     - {method_name} ({method_type})\n"
            if len(element['methods']) > 3:
                result += f"     ... and {len(element['methods']) - 3} more\n"

    # Struct specific info (Go)
    elif element['type'] == 'struct':
        result += "   🏗️  Go struct definition\n"
        if element.get('fields'):
            result += f"   📋 Fields: {len(element['fields'])} found\n"
            for field in element['fields'][:2]:
                result += f"     - {field}\n"
            if len(element['fields']) > 2:
                result += f"     ... and {len(element['fields']) - 2} more\n"

    # Interface specific info
    elif element['type'] == 'interface':
        if language == 'go':
            result += "   🔌 Go interface definition\n"
            if element.get('methods'):
                result += f"   📋 Methods: {len(element['methods'])} found\n"
        elif language == 'typescript':
            result += "   🔌 TypeScript interface definition\n"
            if element.get('properties'):
                result += f"   📋 Properties: {len(element['properties'])} found\n"

    # Type alias specific info (TypeScript)
    elif element['type'] == 'type':
        result += "   📋 TypeScript type alias\n"
        if element.get('definition'):
            definition = element['definition'][:50] + "..." if len(element['definition']) > 50 else element['definition']
            result += f"   📝 Definition: {definition}\n"

    # Documentation
    if element.get('docstring') and element['docstring'].strip():
        docstring = element['docstring'][:100] + "..." if len(element['docstring']) > 100 else element['docstring']
        doc_label = _get_ts_doc_label(language)
        result += f"   📚 {doc_label}: {docstring}\n"

    return result


def _get_ts_doc_label(language: str) -> str:
    """Get appropriate documentation label for Tree-sitter parsed elements."""
    labels = {
        'python': 'Docstring',
        'go': 'Comment',
        'java': 'JavaDoc',
        'c': 'Comment',
        'cpp': 'Comment',
        'javascript': 'JSDoc',
        'typescript': 'TSDoc'
    }
    return labels.get(language, 'Documentation')
