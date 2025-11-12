#!/usr/bin/env python3
"""
Test script that returns JSON decisions based on tool input.
"""
import sys
import json

def main():
    try:
        # Read hook context from stdin
        context = json.loads(sys.stdin.read())

        tool_input = context.get('tool_input', {})

        # Make decision based on tool input
        if 'dangerous' in str(tool_input).lower():
            response = {
                "decision": "deny",
                "reason": "Potentially dangerous operation detected",
                "continue": False
            }
        elif 'confirm' in str(tool_input).lower():
            response = {
                "decision": "ask",
                "reason": "User confirmation required",
                "continue": False
            }
        else:
            response = {
                "decision": "allow",
                "reason": "Operation approved",
                "continue": True
            }

        print(json.dumps(response))
        sys.exit(0)

    except Exception as e:
        print(f"Decision hook error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
