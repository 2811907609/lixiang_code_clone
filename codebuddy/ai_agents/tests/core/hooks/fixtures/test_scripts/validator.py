#!/usr/bin/env python3
"""
Test script that validates tool input and returns appropriate exit codes.
"""
import sys
import json

def main():
    try:
        # Read hook context from stdin
        context = json.loads(sys.stdin.read())

        # Simple validation: check if tool_input has required fields
        tool_input = context.get('tool_input', {})

        if not tool_input:
            print("No tool input provided", file=sys.stderr)
            sys.exit(1)

        # Allow execution
        print("Validation passed")
        sys.exit(0)

    except json.JSONDecodeError:
        print("Invalid JSON input", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Validation error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
