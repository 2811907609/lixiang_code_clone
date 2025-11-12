"""
Unified code parsing interface that intelligently selects the best parser.

This module provides a single interface that automatically chooses between
Tree-sitter (high accuracy) and regex (fallback) parsing based on availability.
It also includes high-level analysis tools for code structure analysis.
"""

from pathlib import Path
from typing import List, Dict

# Import parsers
try:
    from .treesitter_parser import parse_code_with_treesitter
    TREESITTER_AVAILABLE = True
except ImportError:
    TREESITTER_AVAILABLE = False

try:
    from .regex_parser import parse_code_with_regex
    REGEX_AVAILABLE = True
except ImportError:
    REGEX_AVAILABLE = False


def parse_code_elements(
    file_path: str,
    element_types: List[str] = None,
    include_docstrings: bool = True,
    include_decorators: bool = True,
    include_line_numbers: bool = True,
    language: str = None,
    prefer_treesitter: bool = True
) -> str:
    """
    Parse source code using the best available parser.

    This unified interface automatically selects the most appropriate parser:
    1. Tree-sitter (if available and preferred) - High accuracy
    2. Regex patterns (fallback) - Basic compatibility

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
        include_line_numbers: Whether to include line number information
        language: Force specific language detection (auto-detected from file extension if None)
        prefer_treesitter: Whether to prefer Tree-sitter over regex parsing

    Returns:
        str: Detailed analysis of code elements with metadata

    Examples:
        >>> parse_code_elements("src/utils.py")
        >>> parse_code_elements("main.go", ["function", "struct"])
        >>> parse_code_elements("app.ts", ["function", "class", "interface"])
        >>> parse_code_elements("service.java", ["class", "method"])
        >>> parse_code_elements("lib.cpp", ["function", "class", "namespace"])
    """
    # Validate inputs
    if not file_path or not file_path.strip():
        raise ValueError("file_path is required and cannot be empty")

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File '{file_path}' does not exist")

    # Determine parsing strategy
    strategy = _determine_parsing_strategy(prefer_treesitter)

    # Try parsing with the selected strategy
    for parser_name, parser_func in strategy:
        try:
            result = parser_func(
                file_path=file_path,
                element_types=element_types,
                include_docstrings=include_docstrings,
                include_decorators=include_decorators,
                include_line_numbers=include_line_numbers,
                language=language
            )

            # Check if parsing was successful
            if _is_successful_parse(result):
                return result + f"\n\nSuccessfully parsed using {parser_name}"

        except Exception as e:
            # Log the error and try next parser
            error_msg = f"{parser_name} failed: {e}"
            if parser_name == strategy[-1][0]:  # Last parser
                return f"All parsers failed. Last error: {error_msg}"
            continue

    return "No suitable parser available. Please install tree-sitter or check file format."


def _determine_parsing_strategy(prefer_treesitter: bool) -> List[tuple]:
    """Determine the parsing strategy based on availability and preference."""
    strategy = []

    if prefer_treesitter and TREESITTER_AVAILABLE:
        strategy.append(("Tree-sitter", parse_code_with_treesitter))

    if REGEX_AVAILABLE:
        strategy.append(("Regex", parse_code_with_regex))

    if not prefer_treesitter and TREESITTER_AVAILABLE:
        strategy.append(("Tree-sitter", parse_code_with_treesitter))

    return strategy


def _is_successful_parse(result: str) -> bool:
    """Check if the parsing result indicates success."""
    success_indicators = [
        "Tree-sitter Analysis",
        "Regex Analysis",
        "Elements found:",
        "Successfully parsed"
    ]

    failure_indicators = [
        "not available",
        "not supported",
        "Error parsing",
        "Error"
    ]

    # Check for failure indicators first
    for indicator in failure_indicators:
        if indicator in result:
            return False

    # Check for success indicators
    for indicator in success_indicators:
        if indicator in result:
            return True

    return False



def compare_parsers(file_path: str, element_types: List[str] = None) -> str:
    """
    Compare parsing results between Tree-sitter and regex parsers.

    Args:
        file_path: Path to the source file to analyze
        element_types: List of element types to extract

    Returns:
        str: Comparison of parsing results
    """
    if not TREESITTER_AVAILABLE or not REGEX_AVAILABLE:
        return "Both parsers must be available for comparison"

    comparison = f"Parser Comparison for: {file_path}\n"
    comparison += "=" * 60 + "\n\n"

    # Parse with Tree-sitter
    try:
        ts_result = parse_code_with_treesitter(
            file_path=file_path,
            element_types=element_types,
            include_docstrings=True,
            include_line_numbers=True
        )
        ts_elements = _count_elements(ts_result)
        comparison += "Tree-sitter Results:\n"
        comparison += f"   Elements found: {ts_elements}\n"
        comparison += f"   Status: {'Success' if _is_successful_parse(ts_result) else 'Failed'}\n\n"
    except Exception as e:
        comparison += "Tree-sitter Results:\n"
        comparison += f"   Error: {e}\n\n"
        ts_elements = 0

    # Parse with Regex
    try:
        regex_result = parse_code_with_regex(
            file_path=file_path,
            element_types=element_types,
            include_docstrings=True,
            include_line_numbers=True
        )
        regex_elements = _count_elements(regex_result)
        comparison += "Regex Results:\n"
        comparison += f"   Elements found: {regex_elements}\n"
        comparison += f"   Status: {'Success' if _is_successful_parse(regex_result) else 'Failed'}\n\n"
    except Exception as e:
        comparison += "Regex Results:\n"
        comparison += f"   Error: {e}\n\n"
        regex_elements = 0

    # Comparison summary
    comparison += "Comparison Summary:\n"
    if ts_elements > regex_elements:
        comparison += f"   Tree-sitter found {ts_elements - regex_elements} more elements\n"
        comparison += "   Tree-sitter provides more accurate parsing\n"
    elif regex_elements > ts_elements:
        comparison += f"   Regex found {regex_elements - ts_elements} more elements\n"
        comparison += "   Regex may have false positives\n"
    else:
        comparison += "   Both parsers found the same number of elements\n"

    comparison += f"\nRecommendation: Use {'Tree-sitter' if ts_elements >= regex_elements else 'Regex'} for this file\n"

    return comparison


def _count_elements(result: str) -> int:
    """Count the number of elements found in a parsing result."""
    if "Elements found:" in result:
        try:
            # Extract number from "Elements found: X"
            import re
            match = re.search(r'Elements found: (\d+)', result)
            if match:
                return int(match.group(1))
        except Exception:
            pass

    # Fallback: count element markers
    element_markers = ["FUNCTION:", "CLASS:", "STRUCT:", "INTERFACE:", "METHOD:", "TYPE:"]
    count = 0
    for marker in element_markers:
        count += result.count(marker)

    return count


# Additional high-level analysis tools

def analyze_file_structure(file_path: str) -> str:
    """
    Analyze the overall structure of a source file.

    This provides a high-level overview of the file's organization,
    including counts of different element types and complexity indicators.

    Args:
        file_path: Path to the source file to analyze

    Returns:
        str: Structural analysis of the file
    """
    try:
        # Get detailed analysis
        detailed_result = parse_code_elements(
            file_path=file_path,
            prefer_treesitter=True
        )

        if "Error" in detailed_result:
            return detailed_result

        # Extract summary information
        summary = _extract_summary_from_result(detailed_result, file_path)
        return summary

    except Exception as e:
        return f"Error analyzing file structure for '{file_path}': {e}"


def _extract_summary_from_result(detailed_result: str, file_path: str) -> str:
    """Extract summary information from detailed parsing result."""
    lines = detailed_result.split('\n')

    # Extract basic info
    language = "unknown"
    parser = "unknown"
    element_count = 0

    for line in lines:
        if "Language:" in line:
            language = line.split("Language:")[-1].strip()
        elif "Parser:" in line:
            parser = line.split("Parser:")[-1].strip()
        elif "Elements found:" in line:
            try:
                element_count = int(line.split("Elements found:")[-1].strip())
            except Exception:
                pass

    # Count different element types
    element_types = {}
    for line in lines:
        if any(marker in line for marker in ["FUNCTION:", "CLASS:", "STRUCT:", "INTERFACE:", "METHOD:", "TYPE:"]):
            for marker in ["FUNCTION", "CLASS", "STRUCT", "INTERFACE", "METHOD", "TYPE"]:
                if f"{marker}:" in line:
                    element_types[marker.lower()] = element_types.get(marker.lower(), 0) + 1
                    break

    # Build summary
    summary = f"File Structure Analysis: {file_path}\n"
    summary += "=" * 60 + "\n\n"

    summary += f"Language: {language}\n"
    summary += f"Parser: {parser}\n"
    summary += f"Total Elements: {element_count}\n\n"

    if element_types:
        summary += "Element Breakdown:\n"
        for elem_type, count in sorted(element_types.items()):
            summary += f"   {elem_type.title()}s: {count}\n"
        summary += "\n"

    # Add complexity indicators
    complexity_indicators = _analyze_complexity_indicators(detailed_result)
    if complexity_indicators:
        summary += "Complexity Indicators:\n"
        for indicator in complexity_indicators:
            summary += f"   - {indicator}\n"
        summary += "\n"

    # Add recommendations
    recommendations = _generate_recommendations(element_types, language)
    if recommendations:
        summary += "Testing Recommendations:\n"
        for rec in recommendations:
            summary += f"   - {rec}\n"

    return summary


def _analyze_complexity_indicators(detailed_result: str) -> List[str]:
    """Analyze complexity indicators from the detailed result."""
    indicators = []

    if "async" in detailed_result.lower():
        indicators.append("Contains async/await patterns")

    if "complexity:" in detailed_result.lower():
        indicators.append("Complex control flow detected")

    # Count total elements to gauge file size
    element_count = detailed_result.count("FUNCTION:") + detailed_result.count("CLASS:") + detailed_result.count("STRUCT:")
    if element_count > 10:
        indicators.append(f"Large file with {element_count} elements")
    elif element_count > 5:
        indicators.append(f"Medium-sized file with {element_count} elements")

    return indicators


def _generate_recommendations(element_types: Dict[str, int], language: str) -> List[str]:
    """Generate testing recommendations based on file structure."""
    recommendations = []

    # Function-based recommendations
    func_count = element_types.get('function', 0) + element_types.get('method', 0)
    if func_count > 10:
        recommendations.append("Consider breaking down large files for better testability")
    elif func_count > 5:
        recommendations.append("Focus on testing public methods and complex functions")

    # Class-based recommendations
    class_count = element_types.get('class', 0)
    if class_count > 0:
        recommendations.append("Test class instantiation and method interactions")
        recommendations.append("Consider testing inheritance and polymorphism")

    # Language-specific recommendations
    if language == 'python':
        recommendations.append("Use pytest for comprehensive testing")
        if element_types.get('function', 0) > 0:
            recommendations.append("Test both sync and async functions if present")
    elif language == 'go':
        recommendations.append("Use Go's built-in testing package")
        if element_types.get('interface', 0) > 0:
            recommendations.append("Test interface implementations")
    elif language == 'javascript' or language == 'typescript':
        recommendations.append("Use Jest or similar testing framework")
        recommendations.append("Test both browser and Node.js environments if applicable")

    return recommendations
