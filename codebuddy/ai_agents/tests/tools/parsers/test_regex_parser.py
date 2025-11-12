#!/usr/bin/env python3
"""
Test script for regex parser functionality.

This script tests the regex parser with various programming languages
to ensure it's working correctly as a fallback when Tree-sitter is not available.
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

@property
@staticmethod
class Calculator:
    """A simple calculator class."""

    def __init__(self):
        self.history = []

    @classmethod
    def add(self, x: float, y: float) -> float:
        """Add two numbers."""
        result = x + y
        self.history.append(f"{x} + {y} = {result}")
        return result

    async def async_multiply(self, x: float, y: float) -> float:
        """Multiply two numbers asynchronously."""
        return x * y

class InheritedClass(Calculator, BaseClass):
    """A class that inherits from Calculator."""
    pass
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

    'java': '''
/**
 * User class for managing user data
 */
@Entity
@Table(name = "users")
public class User {
    @Id
    private Long id;

    @Column(name = "name")
    private String name;

    /**
     * Get user name
     * @return user name
     */
    @Override
    public String getName() {
        return this.name;
    }

    /**
     * Set user name
     * @param name the name to set
     */
    public void setName(String name) {
        this.name = name;
    }
}

/**
 * User service interface
 */
public interface UserService {
    /**
     * Find user by ID
     * @param id user ID
     * @return user object
     */
    User findById(Long id);
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
@Component
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
@Injectable()
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
''',

    'c': '''
#include <stdio.h>
#include <stdlib.h>

// User structure definition
struct User {
    int id;
    char name[100];
    char email[100];
};

// Function to create a new user
struct User* create_user(int id, const char* name, const char* email) {
    struct User* user = malloc(sizeof(struct User));
    user->id = id;
    strcpy(user->name, name);
    strcpy(user->email, email);
    return user;
}

// Function to print user information
void print_user(const struct User* user) {
    printf("User: %s (%s)\\n", user->name, user->email);
}

int main() {
    struct User* user = create_user(1, "John Doe", "john@example.com");
    print_user(user);
    free(user);
    return 0;
}
''',

    'cpp': '''
#include <iostream>
#include <string>
#include <vector>

namespace UserManagement {
    // User class definition
    class User {
    private:
        int id;
        std::string name;
        std::string email;

    public:
        // Constructor
        User(int id, const std::string& name, const std::string& email)
            : id(id), name(name), email(email) {}

        // Get user name
        std::string getName() const {
            return name;
        }

        // Get user email
        std::string getEmail() const {
            return email;
        }

        // Static factory method
        static User createGuest() {
            return User(0, "Guest", "guest@example.com");
        }
    };

    // User service class
    class UserService {
    private:
        std::vector<User> users;

    public:
        // Add user to service
        void addUser(const User& user) {
            users.push_back(user);
        }

        // Find user by name
        User* findByName(const std::string& name) {
            for (auto& user : users) {
                if (user.getName() == name) {
                    return &user;
                }
            }
            return nullptr;
        }
    };
}

int main() {
    UserManagement::User user(1, "John Doe", "john@example.com");
    std::cout << "User: " << user.getName() << std::endl;
    return 0;
}
'''
}


def test_regex_parser():
    """Test the regex parser with different languages."""
    print("🧪 Testing Regex Parser")
    print("=" * 50)

    try:
        from ai_agents.tools.parsers.regex_parser import parse_code_with_regex
        print("✅ Successfully imported regex parser")
    except ImportError as e:
        print(f"❌ Failed to import regex parser: {e}")
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
            result = parse_code_with_regex(temp_file)
            print(result)

            # Check if parsing was successful
            if "Regex Analysis" in result and "Elements found:" in result:
                print(f"✅ {language.upper()} parsing successful!")
            elif "not supported" in result:
                print(f"⚠️  {language.upper()} not supported by regex parser")
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


def test_specific_element_types():
    """Test parsing with specific element types."""
    print("\n🎯 Testing Specific Element Types")
    print("=" * 50)

    try:
        from ai_agents.tools.parsers.regex_parser import parse_code_with_regex
    except ImportError as e:
        print(f"❌ Failed to import regex parser: {e}")
        return

    # Test Python with only functions
    python_code = '''
def function1():
    pass

class TestClass:
    def method1(self):
        pass

async def async_function():
    pass
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(python_code)
        temp_file = f.name

    try:
        # Test with only functions
        result = parse_code_with_regex(temp_file, element_types=['function'])
        print("🔍 Python - Functions only:")
        print(result)

        # Test with only classes
        result = parse_code_with_regex(temp_file, element_types=['class'])
        print("\n🔍 Python - Classes only:")
        print(result)

        # Test with async functions
        result = parse_code_with_regex(temp_file, element_types=['async_function'])
        print("\n🔍 Python - Async functions only:")
        print(result)

    except Exception as e:
        print(f"❌ Error in specific element type test: {e}")

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
        from ai_agents.tools.parsers.regex_parser import parse_code_with_regex
    except ImportError as e:
        print(f"❌ Failed to import regex parser: {e}")
        return

    # Test with non-existent file
    try:
        result = parse_code_with_regex("/non/existent/file.py")
        print("❌ Should have raised FileNotFoundError")
    except FileNotFoundError:
        print("✅ Correctly handled non-existent file")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    # Test with empty file path
    try:
        result = parse_code_with_regex("")
        print("❌ Should have raised ValueError")
    except ValueError:
        print("✅ Correctly handled empty file path")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    # Test with unsupported language
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xyz', delete=False) as f:
        f.write("some content")
        temp_file = f.name

    try:
        result = parse_code_with_regex(temp_file)
        if "not supported" in result:
            print("✅ Correctly handled unsupported language")
        else:
            print("❌ Should have indicated unsupported language")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        try:
            os.unlink(temp_file)
        except OSError:
            pass


def test_python_ast_vs_regex():
    """Test Python AST parsing vs regex fallback."""
    print("\n🐍 Testing Python AST vs Regex Fallback")
    print("=" * 50)

    try:
        from ai_agents.tools.parsers.regex_parser import parse_code_with_regex
    except ImportError as e:
        print(f"❌ Failed to import regex parser: {e}")
        return

    # Valid Python code (should use AST)
    valid_python = '''
def valid_function():
    """This is a valid function."""
    return True

class ValidClass:
    """This is a valid class."""
    def method(self):
        pass
'''

    # Invalid Python syntax (should fall back to regex)
    invalid_python = '''
def invalid_function(
    # Missing closing parenthesis
    return True

class InvalidClass:
    def method(self):
        pass
'''

    # Test valid Python
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(valid_python)
        temp_file_valid = f.name

    try:
        result = parse_code_with_regex(temp_file_valid)
        print("🔍 Valid Python (AST parsing):")
        print(result)

        if "docstring" in result.lower():
            print("✅ AST parsing extracted docstrings")
        else:
            print("⚠️  AST parsing may not have extracted docstrings")

    except Exception as e:
        print(f"❌ Error parsing valid Python: {e}")
    finally:
        try:
            os.unlink(temp_file_valid)
        except OSError:
            pass

    # Test invalid Python
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(invalid_python)
        temp_file_invalid = f.name

    try:
        result = parse_code_with_regex(temp_file_invalid)
        print("\n🔍 Invalid Python (Regex fallback):")
        print(result)

        if "Elements found:" in result:
            print("✅ Regex fallback successfully parsed elements")
        else:
            print("❌ Regex fallback failed")

    except Exception as e:
        print(f"❌ Error parsing invalid Python: {e}")
    finally:
        try:
            os.unlink(temp_file_invalid)
        except OSError:
            pass


def test_options():
    """Test various parsing options."""
    print("\n⚙️  Testing Parsing Options")
    print("=" * 50)

    try:
        from ai_agents.tools.parsers.regex_parser import parse_code_with_regex
    except ImportError as e:
        print(f"❌ Failed to import regex parser: {e}")
        return

    python_code = '''
@decorator
def test_function():
    """Test function with decorator."""
    pass

@property
class TestClass:
    """Test class with decorator."""
    pass
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(python_code)
        temp_file = f.name

    try:
        # Test without docstrings
        result = parse_code_with_regex(temp_file, include_docstrings=False)
        print("🔍 Without docstrings:")
        if "docstring" not in result.lower():
            print("✅ Correctly excluded docstrings")
        else:
            print("❌ Docstrings were included when they shouldn't be")

        # Test without decorators
        result = parse_code_with_regex(temp_file, include_decorators=False)
        print("\n🔍 Without decorators:")
        if "decorator" not in result.lower():
            print("✅ Correctly excluded decorators")
        else:
            print("❌ Decorators were included when they shouldn't be")

        # Test without line numbers
        result = parse_code_with_regex(temp_file, include_line_numbers=False)
        print("\n🔍 Without line numbers:")
        if "line:" not in result.lower():
            print("✅ Correctly excluded line numbers")
        else:
            print("❌ Line numbers were included when they shouldn't be")

    except Exception as e:
        print(f"❌ Error testing options: {e}")
    finally:
        try:
            os.unlink(temp_file)
        except OSError:
            pass
