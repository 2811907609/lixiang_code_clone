import pytest
import os
import tempfile
import shutil
from pathlib import Path

from ai_agents.tools.file_ops.file_outliner import get_file_outline


class TestFileOutliner:
    """Test file outlining functionality"""

    def setup_method(self):
        """Setup test environment before each test"""
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)

    def teardown_method(self):
        """Clean up after each test"""
        # Remove the temporary directory
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_python_file_outline(self):
        """Test outlining a Python file"""
        python_content = '''"""
Example Python module for testing
"""

import os
import sys
from pathlib import Path

# Constants
MAX_SIZE = 1000
DEFAULT_ENCODING = "utf-8"

class ExampleClass:
    """Example class for testing"""

    def __init__(self, name):
        """Initialize the class"""
        self.name = name

    def get_name(self):
        """Get the name"""
        return self.name

    def set_name(self, name):
        """Set the name"""
        self.name = name

def example_function():
    """Example function"""
    return "Hello, World!"

def another_function(param1, param2):
    """Another function with parameters"""
    return param1 + param2

if __name__ == "__main__":
    main()
'''

        file_path = self.test_path / "example.py"
        file_path.write_text(python_content)

        result = get_file_outline(str(file_path))

        # Verify outline contains expected sections
        assert "File Outline:" in result
        assert "Type: Python" in result
        assert "📦 IMPORTS:" in result
        assert "🔢 CONSTANTS:" in result
        assert "🏛️  CLASSES:" in result
        assert "⚙️  FUNCTIONS:" in result

        # Verify specific content
        assert "import os" in result
        assert "MAX_SIZE" in result
        assert "class ExampleClass" in result
        assert "example_function" in result

    def test_javascript_file_outline(self):
        """Test outlining a JavaScript file"""
        js_content = '''/**
 * Example JavaScript module
 */

import React from 'react';
import { useState } from 'react';
const axios = require('axios');

// Constants
const API_URL = 'https://api.example.com';
const MAX_RETRIES = 3;

class ComponentClass {
    constructor(props) {
        this.props = props;
    }

    render() {
        return <div>Hello</div>;
    }
}

function myFunction() {
    console.log("Hello from function");
}

const arrowFunction = () => {
    return "Arrow function result";
};

export default ComponentClass;
export { myFunction, arrowFunction };
'''

        file_path = self.test_path / "example.js"
        file_path.write_text(js_content)

        result = get_file_outline(str(file_path))

        # Verify outline contains expected sections
        assert "Type: Javascript" in result
        assert "📦 IMPORTS:" in result
        assert "🏛️  CLASSES:" in result
        assert "⚙️  FUNCTIONS:" in result
        assert "🔢 CONSTANTS:" in result
        assert "📤 EXPORTS:" in result

        # Verify specific content
        assert "import React" in result
        assert "ComponentClass" in result
        assert "myFunction" in result

    def test_markdown_file_outline(self):
        """Test outlining a Markdown file"""
        md_content = '''# Main Title

This is the introduction.

## Section 1

Some content here.

### Subsection 1.1

More content.

## Section 2

Another section.

```python
def example():
    return "code"
```

```javascript
function test() {
    return true;
}
```

[Link to example](https://example.com)
![Image](image.png)
'''

        file_path = self.test_path / "example.md"
        file_path.write_text(md_content)

        result = get_file_outline(str(file_path))

        # Verify outline contains expected sections
        assert "Type: Markdown" in result
        assert "📋 HEADERS:" in result
        assert "💻 CODE BLOCKS:" in result

        # Verify specific content
        assert "# Main Title" in result
        assert "## Section 1" in result
        assert "### Subsection 1.1" in result
        assert "```python" in result

    def test_json_file_outline(self):
        """Test outlining a JSON file"""
        json_content = '''{
    "name": "example",
    "version": "1.0.0",
    "description": "Example package",
    "main": "index.js",
    "scripts": {
        "start": "node index.js",
        "test": "npm test"
    },
    "dependencies": {
        "express": "^4.18.0",
        "lodash": "^4.17.21"
    },
    "keywords": ["example", "test"],
    "author": "Test Author",
    "license": "MIT"
}'''

        file_path = self.test_path / "package.json"
        file_path.write_text(json_content)

        result = get_file_outline(str(file_path))

        # Verify outline contains expected sections
        assert "Type: Json" in result
        assert "📊 JSON STRUCTURE:" in result

        # Verify specific content
        assert "name: str" in result
        assert "scripts: dict" in result
        assert "dependencies: dict" in result

    def test_detail_levels(self):
        """Test different detail levels"""
        python_content = '''import os

class TestClass:
    def method1(self):
        pass
    def method2(self):
        pass

def function1():
    pass
'''

        file_path = self.test_path / "test.py"
        file_path.write_text(python_content)

        # Test brief detail level
        brief_result = get_file_outline(str(file_path), detail_level="brief")
        assert "Type: Python" in brief_result

        # Test detailed detail level
        detailed_result = get_file_outline(str(file_path), detail_level="detailed")
        assert "Type: Python" in detailed_result
        assert len(detailed_result) >= len(brief_result)

        # Test full detail level
        full_result = get_file_outline(str(file_path), detail_level="full")
        assert "Type: Python" in full_result
        assert len(full_result) >= len(detailed_result)

    def test_line_numbers_option(self):
        """Test line numbers inclusion/exclusion"""
        python_content = '''import os

def test_function():
    pass
'''

        file_path = self.test_path / "test.py"
        file_path.write_text(python_content)

        # Test with line numbers
        with_lines = get_file_outline(str(file_path), include_line_numbers=True)
        assert "1:" in with_lines or "   1:" in with_lines

        # Test without line numbers
        without_lines = get_file_outline(str(file_path), include_line_numbers=False)
        assert "1:" not in without_lines and "   1:" not in without_lines

    def test_max_items_per_section(self):
        """Test max items per section limiting"""
        python_content = '''import os
import sys
import json
import re
import pathlib

def func1(): pass
def func2(): pass
def func3(): pass
def func4(): pass
def func5(): pass
'''

        file_path = self.test_path / "test.py"
        file_path.write_text(python_content)

        # Test with small max_items
        result = get_file_outline(str(file_path), max_items_per_section=2)

        # Should contain "... and X more" messages
        assert "more imports" in result or "more functions" in result

    def test_invalid_parameters(self):
        """Test error handling with invalid parameters"""
        file_path = self.test_path / "test.txt"
        file_path.write_text("test content")

        # Test invalid detail level
        with pytest.raises(ValueError, match="detail_level must be one of"):
            get_file_outline(str(file_path), detail_level="invalid")

        # Test invalid max_size_mb
        with pytest.raises(ValueError, match="max_size_mb must be positive"):
            get_file_outline(str(file_path), max_size_mb=0)

        # Test invalid max_items_per_section
        with pytest.raises(ValueError, match="max_items_per_section must be at least 1"):
            get_file_outline(str(file_path), max_items_per_section=0)

        # Test empty file path
        with pytest.raises(ValueError, match="file_path is required"):
            get_file_outline("")

        # Test whitespace only path
        with pytest.raises(ValueError, match="file_path is required"):
            get_file_outline("   ")

    def test_nonexistent_file(self):
        """Test error handling with nonexistent file"""
        with pytest.raises(FileNotFoundError):
            get_file_outline("nonexistent_file.py")

    def test_directory_instead_of_file(self):
        """Test error handling when path is a directory"""
        with pytest.raises(ValueError, match="is not a file"):
            get_file_outline(str(self.test_path))

    def test_file_too_large(self):
        """Test error handling with file too large"""
        large_content = "x" * 1000  # 1KB content
        file_path = self.test_path / "large.txt"
        file_path.write_text(large_content)

        # Set very small max size
        with pytest.raises(ValueError, match="is too large"):
            get_file_outline(str(file_path), max_size_mb=0.0001)  # 0.1KB limit

    def test_encoding_handling(self):
        """Test encoding detection and handling"""
        # Test with UTF-8 content
        utf8_content = "Hello, 世界! 🌍"
        file_path = self.test_path / "utf8.txt"
        file_path.write_text(utf8_content, encoding="utf-8")

        result = get_file_outline(str(file_path), encoding="auto")
        assert "Type: Text" in result

        # Test with explicit encoding
        result = get_file_outline(str(file_path), encoding="utf-8")
        assert "Type: Text" in result

    def test_generic_text_file(self):
        """Test outlining a generic text file"""
        text_content = '''This is a generic text file.
It has multiple lines.
Some lines are longer than others and contain more text to test the long line detection feature.

Empty lines above and below.

The end.
'''

        file_path = self.test_path / "generic.txt"
        file_path.write_text(text_content)

        result = get_file_outline(str(file_path), detail_level="full")

        # Verify outline contains expected sections
        assert "Type: Text" in result
        assert "📊 STATISTICS:" in result
        assert "Total lines:" in result
        assert "Non-empty lines:" in result
        assert "👀 CONTENT PREVIEW:" in result

    def test_yaml_file_outline(self):
        """Test outlining a YAML file"""
        yaml_content = '''# Configuration file
name: example
version: 1.0.0
description: Example configuration

database:
  host: localhost
  port: 5432
  name: example_db

features:
  - feature1
  - feature2
  - feature3

settings:
  debug: false
  environment: development
'''

        file_path = self.test_path / "config.yaml"
        file_path.write_text(yaml_content)

        result = get_file_outline(str(file_path))

        # Verify outline contains expected sections
        assert "Type: Yaml" in result
        assert "🔑 TOP-LEVEL KEYS:" in result

        # Verify specific content
        assert "name" in result
        assert "database" in result
        assert "features" in result

    def test_go_file_outline(self):
        """Test outlining a Go file"""
        go_content = '''package main

import (
    "fmt"
    "os"
    "net/http"
)

const PORT = 8080
const VERSION = "1.0.0"

var server *http.Server
var config Config

type Config struct {
    Host string
    Port int
}

type UserService interface {
    GetUser(id int) User
    CreateUser(user User) error
}

func main() {
    fmt.Println("Hello, World!")
}

func (c *Config) Load() error {
    return nil
}

func handleRequest(w http.ResponseWriter, r *http.Request) {
    fmt.Fprintf(w, "Hello, World!")
}
'''

        file_path = self.test_path / "main.go"
        file_path.write_text(go_content)

        result = get_file_outline(str(file_path))

        # Verify outline contains expected sections
        assert "Type: Go" in result
        assert "📦 PACKAGE: package main" in result
        assert "📦 IMPORTS:" in result
        assert "🏗️  TYPES:" in result
        assert "⚙️  FUNCTIONS:" in result

        # Verify specific content
        assert "import" in result
        assert "Config (struct)" in result
        assert "UserService (interface)" in result
        assert "main()" in result

        # Check for constants and variables if they appear
        if "🔢 CONSTANTS:" in result:
            assert "PORT" in result or "VERSION" in result
        if "📊 VARIABLES:" in result:
            assert "server" in result or "config" in result

    def test_java_file_outline(self):
        """Test outlining a Java file"""
        java_content = '''package com.example.app;

import java.util.List;
import java.util.ArrayList;
import java.io.IOException;

public class UserService {
    private static final String DEFAULT_NAME = "Unknown";
    private static final int MAX_USERS = 1000;

    private List<User> users;
    private DatabaseConnection connection;

    public UserService() {
        this.users = new ArrayList<>();
    }

    public void addUser(User user) throws IOException {
        if (users.size() < MAX_USERS) {
            users.add(user);
        }
    }

    public User getUser(int id) {
        return users.stream()
            .filter(u -> u.getId() == id)
            .findFirst()
            .orElse(null);
    }

    private void validateUser(User user) {
        // validation logic
    }
}

interface UserRepository {
    void save(User user);
    User findById(int id);
}
'''

        file_path = self.test_path / "UserService.java"
        file_path.write_text(java_content)

        result = get_file_outline(str(file_path))

        # Verify outline contains expected sections
        assert "Type: Java" in result
        assert "📦 PACKAGE: package com.example.app;" in result
        assert "📦 IMPORTS:" in result
        assert "🔗 INTERFACES:" in result
        assert "🏛️  CLASSES:" in result
        assert "📊 FIELDS:" in result
        assert "⚙️  METHODS:" in result

        # Verify specific content
        assert "import java.util.List" in result
        assert "class UserService" in result
        assert "interface UserRepository" in result

    def test_c_cpp_file_outline(self):
        """Test outlining a C/C++ file"""
        cpp_content = '''#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_SIZE 1000
#define VERSION "1.0.0"

typedef struct User {
    int id;
    char name[50];
} User;

typedef int callback_t;

struct Config {
    char host[100];
    int port;
};

class UserManager {
private:
    User* users;
    int count;

public:
    UserManager();
    ~UserManager();
    void addUser(const User& user);
    User* getUser(int id);
};

int main(int argc, char* argv[]) {
    printf("Hello, World!\\n");
    return 0;
}

void initialize_system() {
    // initialization code
}

int calculate_sum(int a, int b) {
    return a + b;
}

UserManager::UserManager() {
    users = nullptr;
    count = 0;
}
'''

        file_path = self.test_path / "main.cpp"
        file_path.write_text(cpp_content)

        result = get_file_outline(str(file_path))

        # Verify outline contains expected sections
        assert "Type: Cpp" in result
        assert "📦 INCLUDES:" in result
        assert "🔧 DEFINES:" in result
        assert "🏗️  STRUCTS:" in result
        assert "🏛️  CLASSES:" in result
        assert "⚙️  FUNCTIONS:" in result

        # Verify specific content
        assert "#include <stdio.h>" in result
        assert "MAX_SIZE" in result
        assert "struct Config" in result
        assert "class UserManager" in result
        assert "main()" in result

        # Check for typedefs if they appear
        if "🏷️  TYPEDEFS:" in result:
            assert "User" in result or "callback_t" in result

    def test_toml_file_outline(self):
        """Test outlining a TOML file"""
        toml_content = '''[package]
name = "example"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = "1.0"
tokio = { version = "1.0", features = ["full"] }

[dev-dependencies]
criterion = "0.3"

[features]
default = ["std"]
std = []

[[bin]]
name = "main"
path = "src/main.rs"
'''

        file_path = self.test_path / "Cargo.toml"
        file_path.write_text(toml_content)

        result = get_file_outline(str(file_path))

        # Verify outline contains expected sections
        assert "Type: Toml" in result
        assert "📂 SECTIONS:" in result
        assert "🔑 KEYS:" in result

        # Verify specific content
        assert "[package]" in result
        assert "[dependencies]" in result
        assert "name" in result
        assert "version" in result

    def test_empty_file(self):
        """Test outlining an empty file"""
        file_path = self.test_path / "empty.txt"
        file_path.write_text("")

        result = get_file_outline(str(file_path))

        # Verify basic outline structure
        assert "File Outline:" in result
        assert "Type: Text" in result
        assert "Lines: 0" in result
        assert "Size: 0 bytes" in result

    def test_file_with_only_comments(self):
        """Test outlining a file with only comments"""
        python_content = '''# This is a comment
# Another comment
"""
This is a docstring
"""
# More comments
'''

        file_path = self.test_path / "comments.py"
        file_path.write_text(python_content)

        result = get_file_outline(str(file_path))

        # Should still identify as Python but with minimal content
        assert "Type: Python" in result
        assert "Lines:" in result

    def test_malformed_json_file(self):
        """Test outlining a malformed JSON file"""
        malformed_json = '''{
    "name": "example",
    "version": "1.0.0"
    "missing_comma": true
}'''

        file_path = self.test_path / "malformed.json"
        file_path.write_text(malformed_json)

        result = get_file_outline(str(file_path))

        # Should handle JSON parse error gracefully
        assert "Type: Json" in result
        assert ("JSON PARSE ERROR" in result or "📊 STATISTICS:" in result)

    def test_mixed_content_file(self):
        """Test outlining a file with mixed content"""
        mixed_content = '''#!/usr/bin/env python3
"""
Mixed content file for testing
"""

import os
import sys

# Some configuration
CONFIG = {
    "debug": True,
    "version": "1.0.0"
}

class MixedClass:
    """A class with various elements"""

    CLASS_VAR = "constant"

    def __init__(self):
        self.instance_var = None

    def method_one(self):
        """First method"""
        pass

    def method_two(self, param):
        """Second method with parameter"""
        return param * 2

    @staticmethod
    def static_method():
        """Static method"""
        return "static"

    @classmethod
    def class_method(cls):
        """Class method"""
        return cls.CLASS_VAR

def standalone_function():
    """Standalone function"""
    return "standalone"

def function_with_params(a, b, c=None):
    """Function with parameters"""
    return a + b + (c or 0)

if __name__ == "__main__":
    print("Running as main")
'''

        file_path = self.test_path / "mixed.py"
        file_path.write_text(mixed_content)

        result = get_file_outline(str(file_path), detail_level="full")

        # Verify comprehensive analysis
        assert "Type: Python" in result
        assert "📦 IMPORTS:" in result
        assert "🏛️  CLASSES:" in result
        assert "⚙️  FUNCTIONS:" in result

        # Verify specific elements are captured
        assert "MixedClass" in result
        assert "method_one" in result
        assert "standalone_function" in result
        assert "function_with_params" in result

    @pytest.mark.parametrize("file_extension,expected_type", [
        (".py", "Python"),
        (".js", "Javascript"),
        (".ts", "Javascript"),
        (".go", "Go"),
        (".java", "Java"),
        (".c", "C"),
        (".cpp", "Cpp"),
        (".rs", "Rust"),
        (".rb", "Ruby"),
        (".php", "Php"),
        (".md", "Markdown"),
        (".json", "Json"),
        (".yaml", "Yaml"),
        (".yml", "Yaml"),
        (".toml", "Toml"),
        (".html", "Html"),
        (".xml", "Xml"),
        (".sh", "Shell"),
        (".txt", "Text"),
    ])
    def test_file_type_detection(self, file_extension, expected_type):
        """Test file type detection for various extensions"""
        content = "# Sample content\nprint('hello')"
        file_path = self.test_path / f"test{file_extension}"
        file_path.write_text(content)

        result = get_file_outline(str(file_path))

        assert f"Type: {expected_type}" in result
