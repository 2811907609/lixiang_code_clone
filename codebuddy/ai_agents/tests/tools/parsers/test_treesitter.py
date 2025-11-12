#!/usr/bin/env python3
"""
Test script for Tree-sitter parser functionality.

This script tests the Tree-sitter parser with various programming languages
to ensure it's working correctly.
"""

import os
import tempfile

# Test code samples for different languages
TEST_SAMPLES = {
    'python': '''
def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two integers."""
    return a + b

async def fetch_data(url: str) -> dict:
    """Fetch data from a URL asynchronously."""
    # Simulate async operation
    return {"status": "success"}

class Calculator:
    """A simple calculator class."""

    def __init__(self):
        self.history = []

    def add(self, x: float, y: float) -> float:
        """Add two numbers."""
        result = x + y
        self.history.append(f"{x} + {y} = {result}")
        return result

    async def async_multiply(self, x: float, y: float) -> float:
        """Multiply two numbers asynchronously."""
        return x * y
''',

    'go': '''
package main

import "fmt"

// User represents a user in the system
type User struct {
    ID   int    `json:"id"`
    Name string `json:"name"`
    Email string `json:"email"`
}

// UserService provides user-related operations
type UserService interface {
    GetUser(id int) (*User, error)
    CreateUser(user *User) error
}

// GetFullName returns the full name of the user
func (u *User) GetFullName() string {
    return u.Name
}

// CreateUser creates a new user
func CreateUser(name, email string) *User {
    return &User{
        Name:  name,
        Email: email,
    }
}

func main() {
    user := CreateUser("John Doe", "john@example.com")
    fmt.Println(user.GetFullName())
}
''',

    'javascript': '''
/**
 * Calculate the area of a circle
 * @param {number} radius - The radius of the circle
 * @returns {number} The area of the circle
 */
function calculateArea(radius) {
    return Math.PI * radius * radius;
}

/**
 * Fetch user data asynchronously
 * @param {string} userId - The user ID
 * @returns {Promise<Object>} User data
 */
async function fetchUser(userId) {
    const response = await fetch(`/api/users/${userId}`);
    return response.json();
}

// Arrow function example
const multiply = (a, b) => a * b;

// Async arrow function
const asyncProcess = async (data) => {
    return await processData(data);
};

/**
 * User class for managing user data
 */
class User {
    constructor(name, email) {
        this.name = name;
        this.email = email;
    }

    /**
     * Get user's display name
     * @returns {string} Display name
     */
    getDisplayName() {
        return this.name;
    }

    /**
     * Update user email asynchronously
     * @param {string} newEmail - New email address
     * @returns {Promise<boolean>} Success status
     */
    async updateEmail(newEmail) {
        this.email = newEmail;
        return true;
    }

    static createGuest() {
        return new User("Guest", "guest@example.com");
    }
}
''',

    'typescript': '''
/**
 * User interface definition
 */
interface User {
    id: number;
    name: string;
    email: string;
    isActive?: boolean;
}

/**
 * API response type
 */
type ApiResponse<T> = {
    data: T;
    status: 'success' | 'error';
    message?: string;
};

/**
 * User service class
 */
class UserService {
    private users: User[] = [];

    /**
     * Get user by ID
     * @param id User ID
     * @returns User or undefined
     */
    getUser(id: number): User | undefined {
        return this.users.find(user => user.id === id);
    }

    /**
     * Create a new user
     * @param userData User data
     * @returns Promise with API response
     */
    async createUser(userData: Omit<User, 'id'>): Promise<ApiResponse<User>> {
        const newUser: User = {
            id: Date.now(),
            ...userData,
            isActive: true
        };

        this.users.push(newUser);

        return {
            data: newUser,
            status: 'success'
        };
    }

    static getInstance(): UserService {
        return new UserService();
    }
}

// Function type definition
type ProcessorFunction = (input: string) => Promise<string>;

// Arrow function with type
const processText: ProcessorFunction = async (text: string) => {
    return text.toUpperCase();
};
'''
}


def test_treesitter_parser():
    """Test the Tree-sitter parser with different languages."""
    print("🧪 Testing Tree-sitter Parser")
    print("=" * 50)

    try:
        from ai_agents.tools.parsers.treesitter_parser import parse_code_with_treesitter
        print("✅ Successfully imported Tree-sitter parser")
    except ImportError as e:
        print(f"❌ Failed to import Tree-sitter parser: {e}")
        return

    # Test each language
    for language, code in TEST_SAMPLES.items():
        print(f"\n🔍 Testing {language.upper()} parsing...")
        print("-" * 30)

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{_get_extension(language)}', delete=False) as f:
            f.write(code)
            temp_file = f.name

        try:
            # Parse the code
            result = parse_code_with_treesitter(temp_file)
            print(result)

            # Check if parsing was successful
            if "Tree-sitter Analysis" in result and "Elements found:" in result:
                print(f"✅ {language.upper()} parsing successful!")
            elif "not available" in result or "not supported" in result:
                print(f"⚠️  {language.upper()} parser not available (expected for some languages)")
            else:
                print(f"❌ {language.upper()} parsing failed")

        except Exception as e:
            print(f"❌ Error parsing {language}: {e}")

        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file)
            except OSError:
                pass


def test_fallback_mechanism():
    """Test the fallback mechanism to regex parsing."""
    print("\n🔄 Testing Fallback Mechanism")
    print("=" * 50)

    try:
        from ai_agents.tools.parsers import parse_code_elements
        print("✅ Successfully imported fallback parser")
    except ImportError as e:
        print(f"❌ Failed to import fallback parser: {e}")
        return

    # Test with Python code (should work with both parsers)
    python_code = '''
def test_function():
    """A test function."""
    return "Hello, World!"

class TestClass:
    """A test class."""
    def method(self):
        return 42
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(python_code)
        temp_file = f.name

    try:
        result = parse_code_elements(temp_file, prefer_treesitter=True)
        print(result)

        if "Tree-sitter" in result:
            print("✅ Using Tree-sitter parser (preferred)")
        elif "regex patterns" in result:
            print("✅ Using regex fallback parser")
        else:
            print("❌ Parsing failed")

    except Exception as e:
        print(f"❌ Error in fallback test: {e}")

    finally:
        try:
            os.unlink(temp_file)
        except OSError:
            pass


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
