#!/usr/bin/env python3
"""
Test script that blocks operations by returning exit code 2.
"""
import sys
import json

def main():
    try:
        # Read hook context from stdin
        _ = json.loads(sys.stdin.read())

        print("Operation blocked by hook", file=sys.stderr)
        sys.exit(2)  # Block operation

    except Exception as e:
        print(f"Blocking hook error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
