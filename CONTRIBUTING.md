# Contributing to Rohlik API Python Client

Thank you for your interest in contributing to the Rohlik API Python Client!

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/dvejsada/rohlik_api_python.git
   cd rohlik_api_python
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the package in development mode with all dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

## Running Tests

Run the test suite:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=rohlik_api --cov-report=html
```

## Code Style

This project uses:
- **black** for code formatting
- **ruff** for linting
- **mypy** for type checking

Format your code:

```bash
black rohlik_api tests
```

Lint your code:

```bash
ruff check rohlik_api tests
```

Type check your code:

```bash
mypy rohlik_api
```

## Pull Request Process

1. Fork the repository
2. Create a new branch for your feature:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. Make your changes and write tests
4. Ensure all tests pass and code is formatted
5. Commit your changes with clear commit messages
6. Push to your fork and submit a pull request

## Commit Messages

Follow conventional commit format:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `test:` for test additions or changes
- `refactor:` for code refactoring
- `chore:` for maintenance tasks

Example: `feat: add support for order history endpoint`

## Adding New Features

When adding new API methods:

1. Add the method to the `RohlikAPI` class in `rohlik_api/client.py`
2. Include proper type hints
3. Add comprehensive docstrings with examples
4. Write tests in `tests/test_client.py`
5. Update the README.md if needed

## Testing Guidelines

- Write tests for all new functionality
- Maintain or improve code coverage
- Use descriptive test names
- Test both success and failure cases

## Questions?

Feel free to open an issue for any questions or suggestions!
