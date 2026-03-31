"""
Test Running Guide for langfuse-custom-tracer

This script helps run tests with various options.
"""

import subprocess
import sys


def run_all_tests():
    """Run all tests."""
    print("Running all tests...\n")
    result = subprocess.run(
        ["python", "-m", "pytest", "-v"],
        cwd="."
    )
    return result.returncode


def run_unit_tests():
    """Run only unit tests."""
    print("Running unit tests...\n")
    result = subprocess.run(
        ["python", "-m", "pytest", "-v", "-m", "not integration"],
        cwd="."
    )
    return result.returncode


def run_with_coverage():
    """Run tests with coverage report."""
    print("Running tests with coverage...\n")
    result = subprocess.run(
        ["python", "-m", "pytest", "-v", "--cov=langfuse_custom_tracer", "--cov-report=html"],
        cwd="."
    )
    if result.returncode == 0:
        print("\n✓ Coverage report generated in htmlcov/index.html")
    return result.returncode


def run_specific_test(test_path):
    """Run a specific test or test file."""
    print(f"Running {test_path}...\n")
    result = subprocess.run(
        ["python", "-m", "pytest", "-v", test_path],
        cwd="."
    )
    return result.returncode


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == "all":
            exit_code = run_all_tests()
        elif command == "unit":
            exit_code = run_unit_tests()
        elif command == "coverage":
            exit_code = run_with_coverage()
        else:
            # Assume it's a test path
            exit_code = run_specific_test(command)
    else:
        # Default: run all tests
        exit_code = run_all_tests()
    
    sys.exit(exit_code)
