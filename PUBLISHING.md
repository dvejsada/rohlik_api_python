# Publishing to PyPI

This document provides instructions for publishing the `rohlik-api` package to PyPI.

## Prerequisites

1. Create accounts on:
   - PyPI: https://pypi.org/account/register/
   - TestPyPI (for testing): https://test.pypi.org/account/register/

2. Install required tools:
   ```bash
   pip install build twine
   ```

## Building the Package

Build the package distributions:

```bash
python -m build
```

This creates:
- `dist/rohlik_api-0.1.0-py3-none-any.whl` (wheel distribution)
- `dist/rohlik_api-0.1.0.tar.gz` (source distribution)

## Testing on TestPyPI (Recommended)

Test your package on TestPyPI first:

```bash
python -m twine upload --repository testpypi dist/*
```

Then test installation:

```bash
pip install --index-url https://test.pypi.org/simple/ rohlik-api
```

## Publishing to PyPI

Once you've tested on TestPyPI, publish to the real PyPI:

```bash
python -m twine upload dist/*
```

You'll be prompted for your PyPI username and password.

## Using API Tokens (Recommended)

Instead of username/password, use API tokens:

1. Generate an API token on PyPI:
   - Go to Account Settings → API tokens
   - Create a new token

2. Configure in `~/.pypirc`:
   ```ini
   [pypi]
   username = __token__
   password = pypi-AgEIcHlwaS5vcmc...your-token-here...
   
   [testpypi]
   username = __token__
   password = pypi-AgENdGVzdC5weXBpLm9yZw...your-token-here...
   ```

## Automated Publishing with GitHub Actions

You can automate publishing using GitHub Actions. Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.x'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    - name: Build package
      run: python -m build
    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: python -m twine upload dist/*
```

Store your PyPI API token as a GitHub secret named `PYPI_API_TOKEN`.

## Version Updates

When releasing a new version:

1. Update version in `pyproject.toml`
2. Update version in `rohlik_api/__init__.py`
3. Update CHANGELOG in README.md
4. Create a git tag:
   ```bash
   git tag v0.1.1
   git push origin v0.1.1
   ```
5. Build and publish the new version

## Verification

After publishing, verify the package:

1. Check it appears on PyPI: https://pypi.org/project/rohlik-api/
2. Install in a fresh environment:
   ```bash
   pip install rohlik-api
   ```
3. Test the installation:
   ```bash
   python -c "from rohlik_api import RohlikAPI; print('Success!')"
   ```
