#!/usr/bin/env python3
"""
Test script for error logging hooks.
"""
import sys
import json

def main():
    try:
        # Read hook context from stdin
        context = json.loads(sys.stdin.read())

        # Log error information
        error_info = context.get('tool_response', {}).get('error', 'Unknown error')
        tool_name = context.get('tool_name', 'Unknown tool')

        log_entry = f"ERROR in {tool_name}: {error_info}\n"

        # Write to a test log file
        log_file = "/tmp/hook_error_test.log"
        with open(log_file, "a") as f:
            f.write(log_entry)

        print(f"Error logged to {log_file}")
        sys.exit(0)

    except Exception as e:
        print(f"Error logger hook failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
