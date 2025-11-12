#!/usr/bin/env python3
"""
Test script that times out to test timeout handling.
"""
import sys
import time

def main():
    # Sleep for a long time to trigger timeout
    time.sleep(120)  # 2 minutes
    print("This should not be reached")
    sys.exit(0)

if __name__ == "__main__":
    main()
