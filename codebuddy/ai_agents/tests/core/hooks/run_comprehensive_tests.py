#!/usr/bin/env python3
"""
Comprehensive test runner for the hook system.
Runs all test suites and provides a summary report.
"""
import subprocess
import sys
import time
from pathlib import Path


def run_test_suite(test_file: str, description: str) -> tuple[bool, float, str]:
    """Run a test suite and return results."""
    print(f"\n{'='*60}")
    print(f"Running {description}")
    print(f"{'='*60}")

    start_time = time.time()

    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent.parent)

        end_time = time.time()
        duration = end_time - start_time

        success = result.returncode == 0

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        return success, duration, result.stdout

    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"Error running test suite: {e}")
        return False, duration, str(e)


def main():
    """Run all comprehensive tests."""
    print("Starting Comprehensive Hook System Test Suite")
    print(f"{'='*80}")

    test_suites = [
        ("tests/core/hooks/test_end_to_end_integration.py", "End-to-End Integration Tests"),
        ("tests/core/hooks/test_performance.py", "Performance Tests"),
        ("tests/core/hooks/test_error_scenarios.py", "Error Scenario Tests"),
        ("tests/core/hooks/test_configuration_integration.py", "Configuration Integration Tests"),
        ("tests/core/hooks/test_backward_compatibility.py", "Backward Compatibility Tests"),
        ("tests/core/hooks/test_documentation.py", "Documentation Tests"),
    ]

    results = []
    total_start_time = time.time()

    for test_file, description in test_suites:
        success, duration, output = run_test_suite(test_file, description)
        results.append((description, success, duration, output))

    total_end_time = time.time()
    total_duration = total_end_time - total_start_time

    # Print summary
    print(f"\n{'='*80}")
    print("COMPREHENSIVE TEST SUMMARY")
    print(f"{'='*80}")

    passed = 0
    failed = 0

    for description, success, duration, output in results:
        status = "PASSED" if success else "FAILED"
        print(f"{description:<50} {status:<8} ({duration:.2f}s)")

        if success:
            passed += 1
        else:
            failed += 1

    print(f"\n{'='*80}")
    print(f"Total Test Suites: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total Duration: {total_duration:.2f}s")
    print(f"{'='*80}")

    # Extract test counts from outputs
    total_tests = 0
    total_passed_tests = 0
    total_failed_tests = 0

    for description, success, duration, output in results:
        # Parse pytest output for test counts
        lines = output.split('\n')
        for line in lines:
            if 'passed' in line and 'failed' in line:
                # Format: "5 failed, 4 passed in 1.95s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'failed,':
                        total_failed_tests += int(parts[i-1])
                    elif part == 'passed':
                        total_passed_tests += int(parts[i-1])
            elif line.endswith('passed'):
                # Format: "1 passed in 1.80s"
                parts = line.split()
                if len(parts) >= 2 and parts[1] == 'passed':
                    total_passed_tests += int(parts[0])

    total_tests = total_passed_tests + total_failed_tests

    if total_tests > 0:
        print("\nIndividual Test Results:")
        print(f"Total Individual Tests: {total_tests}")
        print(f"Passed Individual Tests: {total_passed_tests}")
        print(f"Failed Individual Tests: {total_failed_tests}")
        print(f"Success Rate: {(total_passed_tests/total_tests)*100:.1f}%")

    # Exit with appropriate code
    if failed == 0:
        print("\n🎉 ALL TEST SUITES PASSED!")
        sys.exit(0)
    else:
        print(f"\n❌ {failed} TEST SUITE(S) FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main()
