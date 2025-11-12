#!/usr/bin/env python3
"""
Test script that returns structured JSON responses.
"""
import sys
import json

def main():
    try:
        # Read hook context from stdin
        _ = json.loads(sys.stdin.read())

        response = {
            "decision": "allow",
            "reason": "Post-execution hook completed",
            "additionalContext": "Tool executed successfully",
            "continue": True,
            "suppressOutput": False,
            "output": "Hook execution completed"
        }

        print(json.dumps(response))
        sys.exit(0)

    except Exception as e:
        print(f"JSON response hook error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
