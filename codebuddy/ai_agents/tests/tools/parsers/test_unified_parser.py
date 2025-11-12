#!/usr/bin/env python3
"""
Test script for unified parser functionality.

This script tests the unified parser that intelligently selects between
Tree-sitter and regex parsers based on availability and preference.
"""

import os
import tempfile

# Test code samples for different scenarios
TEST_SAMPLES = {
    'python_simple': '''
def simple_function():
    """A simple function."""
    return True

class SimpleClass:
    """A simple class."""
    def method(self):
        return 42
''',

    'python_complex': '''
import asyncio
from typing import List, Dict, Optional

@dataclass
class User:
    """User data class."""
    id: int
    name: str
    email: str

@property
@staticmethod
async def fetch_users(limit: int = 10) -> List[User]:
    """Fetch users asynchronously."""
    # Complex async logic here
    users = []
    for i in range(limit):
        user = User(id=i, name=f"User{i}", email=f"user{i}@example.com")
        users.append(user)
    return users

class UserService:
    """Service for managing users."""

    def __init__(self, database_url: str):
        self.db_url = database_url
        self.cache = {}

    @classmethod
    async def create_user(cls, user_data: Dict) -> User:
        """Create a new user."""
        return User(**user_data)

    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        if user_id in self.cache:
            return self.cache[user_id]

        # Simulate database fetch
        await asyncio.sleep(0.1)
        user = User(id=user_id, name=f"User{user_id}", email=f"user{user_id}@example.com")
        self.cache[user_id] = user
        return user
''',

    'go_sample': '''
package main

import (
    "fmt"
    "log"
)

// User represents a user in the system
type User struct {
    ID    int    `json:"id"`
    Name  string `json:"name"`
    Email string `json:"email"`
}

// UserRepository interface for user data access
type UserRepository interface {
    GetUser(id int) (*User, error)
    SaveUser(user *User) error
    DeleteUser(id int) error
}

// GetDisplayName returns the user's display name
func (u *User) GetDisplayName() string {
    return fmt.Sprintf("%s (%s)", u.Name, u.Email)
}

// NewUser creates a new user instance
func NewUser(id int, name, email string) *User {
    return &User{
        ID:    id,
        Name:  name,
        Email: email,
    }
}

func main() {
    user := NewUser(1, "John Doe", "john@example.com")
    fmt.Println(user.GetDisplayName())
}
''',

    'javascript_sample': '''
/**
 * User management utilities
 */

class UserManager {
    constructor() {
        this.users = new Map();
    }

    /**
     * Add a new user
     * @param {Object} userData - User data
     * @returns {User} Created user
     */
    addUser(userData) {
        const user = new User(userData);
        this.users.set(user.id, user);
        return user;
    }

    /**
     * Get user by ID
     * @param {number} id - User ID
     * @returns {User|null} User or null
     */
    getUser(id) {
        return this.users.get(id) || null;
    }

    /**
     * Fetch users asynchronously
     * @param {number} limit - Maximum number of users
     * @returns {Promise<User[]>} Array of users
     */
    async fetchUsers(limit = 10) {
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 100));
        return Array.from(this.users.values()).slice(0, limit);
    }
}

// Arrow function example
const createUser = (name, email) => ({
    id: Date.now(),
    name,
    email,
    createdAt: new Date()
});

// Async arrow function
const processUserData = async (userData) => {
    const processed = await validateUserData(userData);
    return processed;
};

function validateUserData(data) {
    return new Promise((resolve) => {
        setTimeout(() => resolve(data), 50);
    });
}
''',

    'invalid_syntax': '''
def broken_function(
    # Missing closing parenthesis
    return "This will cause syntax error"

class BrokenClass:
    def method(self):
        # This should still be parseable by regex
        pass
'''
}


def test_unified_parser_basic():
    """Test basic unified parser functionality."""
    print("🧪 Testing Unified Parser - Basic Functionality")
    print("=" * 60)

    try:
        from ai_agents.tools.parsers.unified_parser import parse_code_elements
        print("✅ Successfully imported unified parser")
    except ImportError as e:
        print(f"❌ Failed to import unified parser: {e}")
        return

    # Test with simple Python code
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(TEST_SAMPLES['python_simple'])
        temp_file = f.name

    try:
        # Test with default settings (prefer Tree-sitter)
        result = parse_code_elements(temp_file)
        print("🔍 Default parsing (prefer Tree-sitter):")
        print(result)

        if "Successfully parsed using" in result:
            print("✅ Unified parser successfully selected and used a parser")
        else:
            print("❌ Unified parser failed to parse")

    except Exception as e:
        print(f"❌ Error in basic unified parser test: {e}")
    finally:
        try:
            os.unlink(temp_file)
        except OSError:
            pass


def test_parser_preference():
    """Test parser preference settings."""
    print("\n⚙️  Testing Parser Preference")
    print("=" * 50)

    try:
        from ai_agents.tools.parsers.unified_parser import parse_code_elements
    except ImportError as e:
        print(f"❌ Failed to import unified parser: {e}")
        return

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(TEST_SAMPLES['python_complex'])
        temp_file = f.name

    try:
        # Test with Tree-sitter preference
        result_ts = parse_code_elements(temp_file, prefer_treesitter=True)
        print("🔍 With Tree-sitter preference:")
        if "Tree-sitter" in result_ts:
            print("✅ Used Tree-sitter parser as preferred")
        elif "Regex" in result_ts:
            print("⚠️  Fell back to regex parser")
        else:
            print("❌ Parser selection unclear")

        # Test with regex preference
        result_regex = parse_code_elements(temp_file, prefer_treesitter=False)
        print("\n🔍 With regex preference:")
        if "Regex" in result_regex:
            print("✅ Used regex parser as preferred")
        elif "Tree-sitter" in result_regex:
            print("⚠️  Used Tree-sitter despite preference")
        else:
            print("❌ Parser selection unclear")

    except Exception as e:
        print(f"❌ Error in parser preference test: {e}")
    finally:
        try:
            os.unlink(temp_file)
        except OSError:
            pass


def test_fallback_mechanism():
    """Test fallback mechanism with invalid syntax."""
    print("\n🔄 Testing Fallback Mechanism")
    print("=" * 50)

    try:
        from ai_agents.tools.parsers.unified_parser import parse_code_elements
    except ImportError as e:
        print(f"❌ Failed to import unified parser: {e}")
        return

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(TEST_SAMPLES['invalid_syntax'])
        temp_file = f.name

    try:
        result = parse_code_elements(temp_file)
        print("🔍 Parsing invalid syntax:")
        print(result)

        if "Successfully parsed using" in result:
            print("✅ Fallback mechanism worked - found a working parser")
        elif "All parsers failed" in result:
            print("⚠️  All parsers failed (expected for very broken syntax)")
        else:
            print("❌ Unexpected result from fallback test")

    except Exception as e:
        print(f"❌ Error in fallback test: {e}")
    finally:
        try:
            os.unlink(temp_file)
        except OSError:
            pass


def test_multiple_languages():
    """Test unified parser with multiple languages."""
    print("\n🌍 Testing Multiple Languages")
    print("=" * 50)

    try:
        from ai_agents.tools.parsers.unified_parser import parse_code_elements
    except ImportError as e:
        print(f"❌ Failed to import unified parser: {e}")
        return

    test_cases = [
        ('go', TEST_SAMPLES['go_sample']),
        ('js', TEST_SAMPLES['javascript_sample'])
    ]

    for ext, code in test_cases:
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{ext}', delete=False) as f:
            f.write(code)
            temp_file = f.name

        try:
            result = parse_code_elements(temp_file)
            print(f"🔍 Testing {ext.upper()} file:")

            if "Successfully parsed using" in result:
                print(f"✅ {ext.upper()} parsing successful")
            elif "not supported" in result:
                print(f"⚠️  {ext.upper()} not supported")
            else:
                print(f"❌ {ext.upper()} parsing failed")

        except Exception as e:
            print(f"❌ Error parsing {ext}: {e}")
        finally:
            try:
                os.unlink(temp_file)
            except OSError:
                pass


def test_error_handling():
    """Test error handling scenarios."""
    print("\n🚨 Testing Error Handling")
    print("=" * 50)

    try:
        from ai_agents.tools.parsers.unified_parser import parse_code_elements
    except ImportError as e:
        print(f"❌ Failed to import unified parser: {e}")
        return

    # Test with non-existent file
    try:
        parse_code_elements("/non/existent/file.py")
        print("❌ Should have raised FileNotFoundError")
    except FileNotFoundError:
        print("✅ Correctly handled non-existent file")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    # Test with empty file path
    try:
        parse_code_elements("")
        print("❌ Should have raised ValueError")
    except ValueError:
        print("✅ Correctly handled empty file path")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def _get_extension(language):
    """Get file extension for language."""
    extensions = {
        'python': 'py',
        'go': 'go',
        'javascript': 'js',
        'typescript': 'ts',
        'java': 'java',
        'c': 'c',
        'cpp': 'cpp'
    }
    return extensions.get(language, 'txt')


def test_parser_comparison():
    """Test parser comparison functionality."""
    print("\n⚖️  Testing Parser Comparison")
    print("=" * 50)

    try:
        from ai_agents.tools.parsers.unified_parser import compare_parsers
    except ImportError as e:
        print(f"❌ Failed to import compare_parsers: {e}")
        return

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(TEST_SAMPLES['python_complex'])
        temp_file = f.name

    try:
        result = compare_parsers(temp_file)
        print("🔍 Parser comparison result:")
        print(result)

        if "Parser Comparison" in result and "Recommendation:" in result:
            print("✅ Parser comparison completed successfully")
        else:
            print("❌ Parser comparison failed")

    except Exception as e:
        print(f"❌ Error in parser comparison test: {e}")
    finally:
        try:
            os.unlink(temp_file)
        except OSError:
            pass


def test_file_structure_analysis():
    """Test file structure analysis functionality."""
    print("\n📊 Testing File Structure Analysis")
    print("=" * 50)

    try:
        from ai_agents.tools.parsers.unified_parser import analyze_file_structure
    except ImportError as e:
        print(f"❌ Failed to import analyze_file_structure: {e}")
        return

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(TEST_SAMPLES['python_complex'])
        temp_file = f.name

    try:
        result = analyze_file_structure(temp_file)
        print("🔍 File structure analysis:")
        print(result)

        expected_sections = [
            "File Structure Analysis",
            "Language:",
            "Parser:",
            "Total Elements:",
            "Element Breakdown:",
            "Testing Recommendations:"
        ]

        success_count = sum(1 for section in expected_sections if section in result)
        if success_count >= 4:  # Allow some flexibility
            print("✅ File structure analysis completed successfully")
        else:
            print(f"⚠️  File structure analysis incomplete ({success_count}/{len(expected_sections)} sections found)")

    except Exception as e:
        print(f"❌ Error in file structure analysis test: {e}")
    finally:
        try:
            os.unlink(temp_file)
        except OSError:
            pass


def test_element_type_filtering():
    """Test element type filtering."""
    print("\n🎯 Testing Element Type Filtering")
    print("=" * 50)

    try:
        from ai_agents.tools.parsers.unified_parser import parse_code_elements
    except ImportError as e:
        print(f"❌ Failed to import unified parser: {e}")
        return

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(TEST_SAMPLES['python_complex'])
        temp_file = f.name

    try:
        # Test with only functions
        result_functions = parse_code_elements(temp_file, element_types=['function'])
        print("🔍 Functions only:")
        if "FUNCTION:" in result_functions and "CLASS:" not in result_functions:
            print("✅ Successfully filtered to functions only")
        else:
            print("❌ Function filtering failed")

        # Test with only classes
        result_classes = parse_code_elements(temp_file, element_types=['class'])
        print("\n🔍 Classes only:")
        if "CLASS:" in result_classes and "FUNCTION:" not in result_classes:
            print("✅ Successfully filtered to classes only")
        else:
            print("❌ Class filtering failed")

        # Test with multiple types
        result_mixed = parse_code_elements(temp_file, element_types=['function', 'class'])
        print("\n🔍 Functions and classes:")
        if "FUNCTION:" in result_mixed and "CLASS:" in result_mixed:
            print("✅ Successfully filtered to multiple types")
        else:
            print("❌ Multiple type filtering failed")

    except Exception as e:
        print(f"❌ Error in element type filtering test: {e}")
    finally:
        try:
            os.unlink(temp_file)
        except OSError:
            pass


def test_parsing_options():
    """Test various parsing options."""
    print("\n⚙️  Testing Parsing Options")
    print("=" * 50)

    try:
        from ai_agents.tools.parsers.unified_parser import parse_code_elements
    except ImportError as e:
        print(f"❌ Failed to import unified parser: {e}")
        return

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(TEST_SAMPLES['python_complex'])
        temp_file = f.name

    try:
        # Test without docstrings
        result_no_docs = parse_code_elements(temp_file, include_docstrings=False)
        print("🔍 Without docstrings:")
        if "Documentation:" not in result_no_docs and "Docstring:" not in result_no_docs:
            print("✅ Successfully excluded docstrings")
        else:
            print("❌ Docstrings were included when they shouldn't be")

        # Test without decorators
        result_no_decorators = parse_code_elements(temp_file, include_decorators=False)
        print("\n🔍 Without decorators:")
        if "Decorators:" not in result_no_decorators:
            print("✅ Successfully excluded decorators")
        else:
            print("❌ Decorators were included when they shouldn't be")

        # Test without line numbers
        result_no_lines = parse_code_elements(temp_file, include_line_numbers=False)
        print("\n🔍 Without line numbers:")
        if "Line:" not in result_no_lines and "Lines:" not in result_no_lines:
            print("✅ Successfully excluded line numbers")
        else:
            print("❌ Line numbers were included when they shouldn't be")

    except Exception as e:
        print(f"❌ Error in parsing options test: {e}")
    finally:
        try:
            os.unlink(temp_file)
        except OSError:
            pass


def test_language_detection():
    """Test automatic language detection."""
    print("\n🔍 Testing Language Detection")
    print("=" * 50)

    try:
        from ai_agents.tools.parsers.unified_parser import parse_code_elements
    except ImportError as e:
        print(f"❌ Failed to import unified parser: {e}")
        return

    test_cases = [
        ('.py', TEST_SAMPLES['python_simple'], 'python'),
        ('.go', TEST_SAMPLES['go_sample'], 'go'),
        ('.js', TEST_SAMPLES['javascript_sample'], 'javascript')
    ]

    for ext, code, expected_lang in test_cases:
        with tempfile.NamedTemporaryFile(mode='w', suffix=ext, delete=False) as f:
            f.write(code)
            temp_file = f.name

        try:
            result = parse_code_elements(temp_file)
            print(f"🔍 Testing {ext} file:")

            if f"Language: {expected_lang}" in result:
                print(f"✅ Correctly detected {expected_lang}")
            elif "Language:" in result:
                detected = result.split("Language:")[-1].split("\n")[0].strip()
                print(f"⚠️  Detected '{detected}' instead of '{expected_lang}'")
            else:
                print("❌ Language detection failed")

        except Exception as e:
            print(f"❌ Error testing {ext}: {e}")
        finally:
            try:
                os.unlink(temp_file)
            except OSError:
                pass
