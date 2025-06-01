# MyDrive Backend Tests

This directory contains the test suite for the MyDrive backend application. The tests cover various aspects of the application including authentication, file operations, sharing functionality, version control, and user management.

## Test Structure

- `conftest.py`: Contains pytest fixtures and test configuration
- `test_auth.py`: Tests for authentication endpoints
- `test_files.py`: Tests for file operations
- `test_sharing.py`: Tests for file sharing functionality
- `test_versions.py`: Tests for version control
- `test_users.py`: Tests for user management

## Running Tests

1. Install test dependencies:
```bash
pip install -r requirements-test.txt
```

2. Run all tests:
```bash
pytest
```

3. Run specific test file:
```bash
pytest test_auth.py
```

4. Run tests with verbose output:
```bash
pytest -v
```

5. Run tests with coverage report:
```bash
pytest --cov=app
```

## Test Coverage

The test suite covers:

- User authentication and authorization
- File upload, download, and management
- Folder creation and management
- File sharing and permissions
- Version control
- User management (CRUD operations)
- Error handling and edge cases

## Test Database

Tests use an in-memory SQLite database to ensure isolation and prevent interference with the production database. The database is created fresh for each test and destroyed afterward.

## Fixtures

The test suite provides several fixtures:

- `client`: FastAPI TestClient instance
- `db_session`: Database session
- `test_user`: Regular user for testing
- `test_user2`: Second regular user for testing
- `test_admin`: Admin user for testing
- `test_user_token`: JWT token for test_user
- `test_admin_token`: JWT token for test_admin

## Writing New Tests

When writing new tests:

1. Use existing fixtures when possible
2. Follow the naming convention: `test_<functionality>_<scenario>`
3. Test both success and failure cases
4. Test authentication and authorization
5. Clean up any resources created during tests
6. Use descriptive assertions
7. Add comments for complex test scenarios 