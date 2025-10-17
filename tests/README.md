# Backend Tests

This directory contains all test files for the Shining Light backend API.

## Structure

```
tests/
├── conftest.py          # Pytest fixtures and configuration
├── api/
│   ├── test_auth.py     # Authentication endpoint tests
│   └── ...              # Other API tests
└── README.md
```

## Running Tests

### Run all tests
```bash
poetry run pytest
```

### Run specific test file
```bash
poetry run pytest tests/api/test_auth.py
```

### Run with verbose output
```bash
poetry run pytest -v
```

### Run specific test class
```bash
poetry run pytest tests/api/test_auth.py::TestLogin
```

### Run specific test method
```bash
poetry run pytest tests/api/test_auth.py::TestLogin::test_login_success
```

### Run tests by marker
```bash
poetry run pytest -m auth          # Run only auth tests
poetry run pytest -m unit          # Run only unit tests
poetry run pytest -m integration   # Run only integration tests
```

### Run with coverage
```bash
poetry run pytest --cov=api --cov-report=html
```

## Test Markers

- `@pytest.mark.auth` - Authentication related tests
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests

## Fixtures Available

- `api_client` - DRF API client for making requests
- `create_user` - Factory fixture for creating users
- `test_user` - Default test user (student)
- `admin_user` - Admin user
- `staff_user` - Staff user
- `authenticated_client` - API client with authenticated user

## Writing New Tests

1. Create test file in appropriate directory: `tests/api/test_feature.py`
2. Import pytest and required models
3. Use `@pytest.mark.django_db` for tests that access database
4. Use fixtures from `conftest.py`
5. Follow naming convention: `test_description`

Example:
```python
import pytest

@pytest.mark.django_db
class TestFeature:
    def test_something(self, api_client, test_user):
        # Your test code
        pass
```

