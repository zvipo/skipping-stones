#!/usr/bin/env python3
"""
Test runner for Skipping Stones application
"""

import sys
import os
import subprocess
import importlib.util

def run_test_file(test_file):
    """Run a single test file"""
    print(f"\n{'='*50}")
    print(f"Running {test_file}")
    print(f"{'='*50}")
    
    try:
        # Add the parent directory to sys.path so we can import app modules
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, parent_dir)
        
        # Import and run the test
        spec = importlib.util.spec_from_file_location("test_module", test_file)
        test_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test_module)
        
        print(f"✓ {test_file} completed successfully")
        return True
    except Exception as e:
        print(f"✗ {test_file} failed: {e}")
        return False

def main():
    """Run all tests in the tests directory"""
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("Running Skipping Stones Tests")
    print("=" * 50)
    
    # Find all test files
    test_files = []
    for file in os.listdir(tests_dir):
        if file.endswith('.py') and file.startswith('test_') and file != '__init__.py':
            test_files.append(os.path.join(tests_dir, file))
    
    if not test_files:
        print("No test files found!")
        return
    
    print(f"Found {len(test_files)} test files:")
    for test_file in test_files:
        print(f"  - {os.path.basename(test_file)}")
    
    # Run tests
    passed = 0
    failed = 0
    
    for test_file in test_files:
        if run_test_file(test_file):
            passed += 1
        else:
            failed += 1
    
    # Summary
    print(f"\n{'='*50}")
    print("Test Summary")
    print(f"{'='*50}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n❌ {failed} test(s) failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 