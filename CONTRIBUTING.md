# Contributing to Sekha Proxy

Thank you for your interest in contributing to Sekha Proxy! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.11 or 3.12
- Docker and Docker Compose (for integration testing)
- Git

### Local Development

1. **Clone the repository**

```bash
git clone https://github.com/sekha-ai/sekha-proxy.git
cd sekha-proxy
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment**

```bash
cp .env.example .env
# Edit .env with your settings
```

5. **Run tests**

```bash
pytest tests/ -v
```

6. **Start the proxy**

```bash
python proxy.py
```

## Code Style

### Python Code

- Follow PEP 8 style guide
- Use type hints for function signatures
- Document functions with docstrings
- Keep lines under 100 characters when practical

### Example

```python
def process_message(content: str, metadata: Dict[str, Any]) -> str:
    """
    Process a message with metadata.
    
    Args:
        content: The message content
        metadata: Additional metadata
    
    Returns:
        Processed message string
    """
    # Implementation
    pass
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_proxy.py -v

# Run with specific marker
pytest -m unit
```

### Writing Tests

- Write tests for all new features
- Aim for >80% code coverage
- Use descriptive test names
- Group related tests in classes
- Use fixtures for common setup

### Test Structure

```python
import pytest

@pytest.fixture
def sample_data():
    """Provide sample data for tests."""
    return {"key": "value"}

def test_feature_behavior(sample_data):
    """Test that feature behaves correctly."""
    result = process_feature(sample_data)
    assert result == expected_value
```

## Pull Request Process

1. **Create a feature branch**

```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes**

- Write clear, concise commit messages
- Keep commits focused and atomic
- Add tests for new functionality

3. **Run tests and linting**

```bash
pytest
ruff check .
mypy .
```

4. **Push and create PR**

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

5. **PR Requirements**

- ✅ All tests pass
- ✅ Code coverage maintained or improved
- ✅ Clear description of changes
- ✅ Documentation updated if needed
- ✅ No merge conflicts

## Commit Message Format

Use clear, descriptive commit messages:

```
Add context injection for multi-turn conversations

- Implement context assembly from controller
- Add tests for context formatting
- Update documentation
```

Good commit messages:
- Start with a verb (Add, Fix, Update, Remove)
- Keep first line under 50 characters
- Provide details in body if needed

## Documentation

### Code Documentation

- Add docstrings to all public functions/classes
- Use Google-style docstrings
- Include type hints
- Explain complex logic with comments

### README Updates

- Update README.md for user-facing changes
- Add examples for new features
- Keep instructions clear and concise

## Issue Reporting

### Bug Reports

Include:
- Description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version)
- Relevant logs/error messages

### Feature Requests

Include:
- Clear description of the feature
- Use case / motivation
- Example of how it would work
- Any implementation ideas

## Code Review

When reviewing PRs:

- Be constructive and respectful
- Focus on code quality, not personal preferences
- Test the changes locally if possible
- Approve when all concerns are addressed

## Release Process

1. Update version in `proxy.py`
2. Update CHANGELOG.md
3. Create release tag: `git tag v1.0.0`
4. Push tag: `git push origin v1.0.0`
5. Create GitHub release with notes

## Getting Help

- Open an issue for bugs or feature requests
- Check existing issues before creating new ones
- Join discussions in issue threads
- Reach out to maintainers if needed

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (AGPL-3.0).
