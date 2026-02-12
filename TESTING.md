# Testing Guide for Sekha Proxy

This document provides comprehensive testing instructions for the sekha-proxy repository.

## Table of Contents

- [Setup](#setup)
- [Running Tests](#running-tests)
- [Test Organization](#test-organization)
- [Test Types](#test-types)
- [Writing Tests](#writing-tests)
- [Coverage](#coverage)
- [CI/CD Testing](#cicd-testing)

## Setup

### Prerequisites

- Python 3.11 or 3.12
- pip or Poetry for dependency management

### Installation

#### Using pip

```bash
# Clone the repository
git clone https://github.com/sekha-ai/sekha-proxy.git
cd sekha-proxy

# Install the package in editable mode with dev dependencies
pip install -e ".[dev]"
```

#### Using Poetry

```bash
# Clone the repository
git clone https://github.com/sekha-ai/sekha-proxy.git
cd sekha-proxy

# Install dependencies
poetry install

# Activate the virtual environment
poetry shell
```

## Running Tests

### All Tests

Run the complete test suite:

```bash
pytest
```

### Unit Tests Only

Run unit tests (excludes integration tests):

```bash
pytest -m "not integration"
```

### Integration Tests Only

Run integration tests (requires full stack):

```bash
pytest -m integration
```

### Specific Test File

Run a specific test file:

```bash
pytest tests/test_config.py
```

### Specific Test Function

Run a specific test:

```bash
pytest tests/test_config.py::test_config_from_env
```

### Verbose Output

Run tests with detailed output:

```bash
pytest -v
```

### Short Traceback

Run tests with concise error output:

```bash
pytest --tb=short
```

## Test Organization

The test suite is organized in the `tests/` directory:

```
tests/
├── __init__.py
├── test_api_endpoints.py      # API endpoint tests
├── test_config.py              # Configuration tests
├── test_context_injection.py   # Context injection tests
├── test_health.py              # Health monitoring tests
├── test_integration.py         # Full stack integration tests
├── test_proxy.py               # Core proxy functionality tests
├── test_proxy_errors.py        # Error handling tests
└── test_vision_detection.py    # Vision/image detection tests
```

### Test Modules

#### `test_config.py`
- Configuration loading from environment variables
- Configuration validation
- Default values
- Invalid configuration handling

#### `test_context_injection.py`
- Context retrieval from controller
- Message formatting with context
- Citation handling
- Token budget enforcement

#### `test_api_endpoints.py`
- FastAPI endpoint tests
- Request/response validation
- Health endpoint checks
- Root endpoint tests

#### `test_health.py`
- Health monitor functionality
- Service availability checks
- Status reporting

#### `test_proxy.py`
- Core proxy forwarding logic
- Bridge routing integration
- Context injection integration
- Metadata handling

#### `test_proxy_errors.py`
- Error handling and recovery
- Bridge connection failures
- Controller unavailability
- Malformed responses
- Fallback behavior

#### `test_vision_detection.py`
- Image URL detection in messages
- OpenAI multimodal format support
- Base64 data URI detection
- Multiple image handling
- False positive prevention

#### `test_integration.py`
- Full stack integration tests
- End-to-end workflows
- Real service interactions
- **Note**: Requires full sekha-ai stack to be running

## Test Types

### Unit Tests

Unit tests are marked with `pytest.mark.asyncio` and test individual components in isolation using mocks:

```python
@pytest.mark.asyncio
async def test_example():
    # Test implementation
    pass
```

### Integration Tests

Integration tests are marked with `@pytest.mark.integration` and test the full system:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_stack():
    # Integration test implementation
    pass
```

## Writing Tests

### Test Structure

Follow this structure for new tests:

```python
"""Description of what this test module covers."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from sekha_proxy.config import Config
from sekha_proxy.proxy import SekhaProxy


@pytest.fixture
def mock_config() -> Config:
    """Create a test configuration."""
    return Config(
        # Configuration parameters
    )


@pytest.mark.asyncio
async def test_something(mock_config: Config) -> None:
    """Test description."""
    # Arrange
    proxy = SekhaProxy(mock_config)
    
    # Act
    result = await proxy.some_method()
    
    # Assert
    assert result == expected_value
    
    # Cleanup
    await proxy.close()
```

### Mocking External Services

Always mock external dependencies in unit tests:

```python
@pytest.mark.asyncio
async def test_with_mocks(mock_config: Config) -> None:
    """Test with mocked dependencies."""
    proxy = SekhaProxy(mock_config)
    
    # Mock the bridge client
    proxy.bridge_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = MagicMock(return_value={"key": "value"})
    proxy.bridge_client.post = AsyncMock(return_value=mock_response)
    
    # Run test
    result = await proxy.forward_chat({"messages": [...]})
    
    # Verify
    assert proxy.bridge_client.post.called
    await proxy.close()
```

### Async Test Guidelines

- Use `@pytest.mark.asyncio` for async tests
- Use `AsyncMock` for async mocks
- Always clean up resources with `await proxy.close()`

## Coverage

### Generate Coverage Report

Run tests with coverage:

```bash
pytest --cov=src/sekha_proxy --cov-report=term-missing
```

### HTML Coverage Report

Generate an HTML coverage report:

```bash
pytest --cov=src/sekha_proxy --cov-report=html
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Coverage Requirements

- Minimum coverage target: 80%
- New code should include tests
- Critical paths require comprehensive testing

### Viewing Coverage in CI

Coverage reports are automatically uploaded to Codecov on CI runs. View them at:
- https://codecov.io/gh/sekha-ai/sekha-proxy

## CI/CD Testing

### GitHub Actions

Tests run automatically on:
- Pull requests to `main`
- Pushes to `main`

### CI Test Matrix

- **Python versions**: 3.11, 3.12
- **Test types**: Unit tests, linting, type checking
- **Coverage**: Uploaded to Codecov

### Local CI Simulation

Run the same checks as CI locally:

```bash
# Linting
ruff check . --select E,F,W,C90 --ignore E501

# Type checking
mypy . --ignore-missing-imports

# Unit tests with coverage
pytest tests/ -v --tb=short -m "not integration" \
  --cov=src/sekha_proxy --cov-report=term-missing
```

### CI Configuration

See `.github/workflows/ci.yml` for the complete CI configuration.

## Debugging Tests

### Print Debugging

Use `-s` flag to see print statements:

```bash
pytest -s tests/test_config.py
```

### Debug on Failure

Drop into debugger on test failure:

```bash
pytest --pdb
```

### Run Last Failed Tests

Re-run only failed tests:

```bash
pytest --lf
```

## Common Issues

### ModuleNotFoundError: No module named 'sekha_proxy'

**Solution**: Install the package in editable mode:

```bash
pip install -e .
```

### Integration Tests Failing

**Solution**: Integration tests require the full Sekha AI stack. Either:
1. Start the required services (controller, bridge, etc.)
2. Run unit tests only: `pytest -m "not integration"`

### Async Test Warnings

**Solution**: Ensure `pytest-asyncio` is installed and tests use `@pytest.mark.asyncio`

## Best Practices

1. **Isolation**: Each test should be independent
2. **Clarity**: Use descriptive test names and docstrings
3. **AAA Pattern**: Arrange, Act, Assert
4. **Mocking**: Mock external dependencies in unit tests
5. **Cleanup**: Always clean up resources (close connections, etc.)
6. **Fixtures**: Use fixtures for common test setup
7. **Marks**: Use appropriate pytest marks (`integration`, `asyncio`)

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)

## Contributing

When adding new features:

1. Write tests for new functionality
2. Ensure all tests pass locally
3. Verify coverage doesn't decrease
4. Update this document if adding new test categories

For more details, see [CONTRIBUTING.md](CONTRIBUTING.md).