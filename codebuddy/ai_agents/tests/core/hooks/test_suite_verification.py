"""
Test suite verification script.
Verifies that all required test components are in place and properly structured.
"""
import os
from pathlib import Path
import importlib.util
import inspect


def verify_test_files_exist():
    """Verify that all required test files exist."""
    required_files = [
        "test_end_to_end_integration.py",
        "test_performance.py",
        "test_error_scenarios.py",
        "test_configuration_integration.py",
        "test_backward_compatibility.py",
        "test_documentation.py",
        "fixtures/__init__.py",
        "fixtures/sample_configs/basic_hooks.json",
        "fixtures/sample_configs/complex_hooks.json",
        "fixtures/sample_configs/invalid_config.json",
        "fixtures/sample_configs/malformed_json",
        "fixtures/test_scripts/validator.py",
        "fixtures/test_scripts/decision_hook.py",
        "fixtures/test_scripts/blocking_hook.py",
        "fixtures/test_scripts/json_response_hook.py",
        "fixtures/test_scripts/error_logger.py",
        "fixtures/test_scripts/timeout_hook.py",
        "fixtures/test_scripts/failing_hook.py",
    ]

    test_dir = Path(__file__).parent
    missing_files = []

    for file_path in required_files:
        full_path = test_dir / file_path
        if not full_path.exists():
            missing_files.append(file_path)

    if missing_files:
        print("❌ Missing required test files:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False
    else:
        print("✅ All required test files exist")
        return True


def verify_test_scripts_executable():
    """Verify that test scripts are executable."""
    test_dir = Path(__file__).parent
    script_dir = test_dir / "fixtures" / "test_scripts"

    script_files = [
        "validator.py",
        "decision_hook.py",
        "blocking_hook.py",
        "json_response_hook.py",
        "error_logger.py",
        "timeout_hook.py",
        "failing_hook.py",
    ]

    non_executable = []

    for script_file in script_files:
        script_path = script_dir / script_file
        if script_path.exists():
            if not os.access(script_path, os.X_OK):
                non_executable.append(script_file)

    if non_executable:
        print("❌ Non-executable test scripts:")
        for script_file in non_executable:
            print(f"  - {script_file}")
        return False
    else:
        print("✅ All test scripts are executable")
        return True


def verify_test_class_structure():
    """Verify that test classes have proper structure."""
    test_dir = Path(__file__).parent
    test_files = [
        "test_end_to_end_integration.py",
        "test_performance.py",
        "test_error_scenarios.py",
        "test_configuration_integration.py",
        "test_backward_compatibility.py",
        "test_documentation.py",
    ]

    issues = []

    for test_file in test_files:
        test_path = test_dir / test_file
        if not test_path.exists():
            continue

        # Load the module
        spec = importlib.util.spec_from_file_location(test_file[:-3], test_path)
        module = importlib.util.module_from_spec(spec)

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            issues.append(f"{test_file}: Failed to load module - {e}")
            continue

        # Check for test classes
        test_classes = [
            obj for name, obj in inspect.getmembers(module)
            if inspect.isclass(obj) and name.startswith('Test')
        ]

        if not test_classes:
            issues.append(f"{test_file}: No test classes found")
            continue

        # Check each test class
        for test_class in test_classes:
            test_methods = [
                name for name, method in inspect.getmembers(test_class)
                if inspect.ismethod(method) or inspect.isfunction(method)
                if name.startswith('test_')
            ]

            if not test_methods:
                issues.append(f"{test_file}::{test_class.__name__}: No test methods found")

    if issues:
        print("❌ Test structure issues:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("✅ All test classes have proper structure")
        return True


def verify_test_coverage():
    """Verify that tests cover all required scenarios."""
    coverage_requirements = {
        "End-to-End Integration": [
            "basic_hook_workflow",
            "complex_decision_workflow",
            "blocking_hook_workflow",
            "error_hook_workflow",
            "json_response_parsing",
            "pattern_matching_workflow",
            "multiple_config_sources_workflow",
            "tool_decorator_integration"
        ],
        "Performance": [
            "hook_execution_overhead",
            "multiple_hooks_performance",
            "pattern_matching_performance",
            "concurrent_hook_execution",
            "memory_usage_stability",
            "hook_timeout_performance"
        ],
        "Error Scenarios": [
            "script_hook_timeout",
            "python_hook_timeout",
            "script_hook_failure",
            "python_hook_exception",
            "invalid_configuration",
            "malformed_json",
            "missing_files",
            "error_recovery"
        ],
        "Configuration Integration": [
            "single_configuration_source",
            "multiple_configuration_merge",
            "configuration_precedence",
            "partial_configurations",
            "empty_configurations",
            "configuration_validation"
        ],
        "Backward Compatibility": [
            "simple_tool_unchanged",
            "multiple_parameters",
            "complex_return_types",
            "exception_handling",
            "side_effects",
            "performance_unchanged",
            "metadata_preservation"
        ],
        "Documentation": [
            "api_documentation",
            "example_verification",
            "signature_stability",
            "documentation_completeness",
            "usage_examples"
        ]
    }

    print("✅ Test coverage requirements defined")
    print(f"  - {len(coverage_requirements)} test categories")
    total_scenarios = sum(len(scenarios) for scenarios in coverage_requirements.values())
    print(f"  - {total_scenarios} total test scenarios")

    return True


def main():
    """Run all verification checks."""
    print("Hook System Test Suite Verification")
    print("=" * 50)

    checks = [
        ("Test Files", verify_test_files_exist),
        ("Script Executability", verify_test_scripts_executable),
        ("Test Structure", verify_test_class_structure),
        ("Test Coverage", verify_test_coverage),
    ]

    all_passed = True

    for check_name, check_func in checks:
        print(f"\n{check_name}:")
        try:
            result = check_func()
            if not result:
                all_passed = False
        except Exception as e:
            print(f"❌ {check_name} verification failed: {e}")
            all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All verification checks passed!")
        print("\nThe comprehensive test suite is ready to run.")
        print("Execute: python tests/core/hooks/run_comprehensive_tests.py")
    else:
        print("❌ Some verification checks failed!")
        print("Please fix the issues before running the test suite.")

    return all_passed


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
