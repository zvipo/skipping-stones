# Tests Directory

This directory contains all test files for the Skipping Stones application.

## Test Files

- `test_logout.py` - Tests the logout functionality and session management
- `test_compression.py` - Tests the data compression functionality
- `test_google_login.py` - Tests Google OAuth login functionality

## Running Tests

### From the project root:
```bash
python3 run_tests.py
```

### From the tests directory:
```bash
cd tests
python3 run_tests.py
```

### Running individual tests:
```bash
cd tests
python3 test_logout.py
python3 test_compression.py
python3 test_google_login.py
```

## Test Requirements

- The Flask application must be running on `http://localhost:5000` for `test_logout.py` and `test_google_login.py`
- All required dependencies must be installed (see `requirements.txt` in the project root)
- Google OAuth credentials are optional for `test_google_login.py` (tests will skip if not configured)

## Adding New Tests

1. Create a new test file with the prefix `test_`
2. Import any required modules from the project root
3. Add your test functions
4. The test runner will automatically discover and run your new test file 