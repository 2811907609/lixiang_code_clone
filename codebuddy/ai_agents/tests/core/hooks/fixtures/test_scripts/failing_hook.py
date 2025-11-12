#!/usr/bin/env python3
"""
Test script that fails with various error conditions.
"""
import sys
import os

def main():
    # Check environment variable to determine failure mode
    failure_mode = os.environ.get('HOOK_FAILURE_MODE', 'exit_code')

    if failure_mode == 'exit_code':
        print("Hook failed with exit code", file=sys.stderr)
        sys.exit(1)
    elif failure_mode == 'exception':
        raise Exception("Hook failed with exception")
    elif failure_mode == 'invalid_json':
        print('{"invalid": json}')  # Invalid JSON
        sys.exit(0)
    else:
        print("Unknown failure mode", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
