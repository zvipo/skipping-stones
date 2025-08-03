#!/usr/bin/env python3
"""
Simple test runner for Skipping Stones application
Run this from the project root to execute all tests
"""

import subprocess
import sys
import os

def main():
    """Run all tests in the tests directory"""
    tests_dir = os.path.join(os.path.dirname(__file__), 'tests')
    
    if not os.path.exists(tests_dir):
        print("Tests directory not found!")
        sys.exit(1)
    
    # Run the test runner
    test_runner = os.path.join(tests_dir, 'run_tests.py')
    
    if not os.path.exists(test_runner):
        print("Test runner not found!")
        sys.exit(1)
    
    print("Running Skipping Stones Tests...")
    print("=" * 50)
    
    try:
        result = subprocess.run([sys.executable, test_runner], 
                              cwd=tests_dir, 
                              capture_output=False, 
                              text=True)
        
        if result.returncode == 0:
            print("\n✅ All tests completed successfully!")
        else:
            print(f"\n❌ Tests failed with exit code {result.returncode}")
            sys.exit(result.returncode)
            
    except Exception as e:
        print(f"Error running tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 