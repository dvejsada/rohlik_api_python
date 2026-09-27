# Publishing to PyPI

Releases are published to [PyPI](https://pypi.org/project/rohlik-api/) by the
`Publish to PyPI` workflow (`.github/workflows/publish.yml`). It runs when a
GitHub Release is **published**, builds the sdist and wheel, checks them with
`twine`, and uploads them using PyPI Trusted Publishing (OIDC), so no API token
is stored anywhere.

## Releasing a new version

1. **Bump the version** in `rohlik_api/__init__.py` (`__version__`). It is the
   single source of truth; `pyproject.toml` reads it dynamically. Follow
   semantic versioning: patch (`0.3.1`) for fixes, minor (`0.4.0`) for new
   features, and major for breaking changes. Merge the bump to `main`.
2. **Make sure CI is green on `main`** (ruff, black, mypy, pytest).
3. **Create a GitHub Release** (Releases → Draft a new release):
   - Tag: `v<version>`, e.g. `v0.3.0`, created from `main`. It must match
     `__version__`; PyPI rejects a version that was already uploaded.
   - Title: `v<version> - <short headline>`.
   - Notes: `## Added` / `## Changed` / `## Fixed` sections as needed, plus a
     `## Compatibility` note on breaking changes and the minimum Python version.
4. **Publish the release.** The workflow uploads the package. Watch it under
   Actions → Publish to PyPI; the `publish` job runs in the `pypi` environment.

## Verifying a release

```bash
pip install --upgrade rohlik-api
python -c "import rohlik_api; print(rohlik_api.__version__)"
```

## Building locally

To check the distribution without publishing:

```bash
pip install build twine
python -m build
python -m twine check dist/*
```

This creates `dist/rohlik_api-<version>-py3-none-any.whl` and
`dist/rohlik_api-<version>.tar.gz`. To try an upload without touching the real
index, use [TestPyPI](https://test.pypi.org/):

```bash
python -m twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ rohlik-api
```

## One-time setup (already done)

- PyPI project → Publishing: a trusted publisher for this repository, the
  `publish.yml` workflow and the `pypi` environment.
- GitHub repository → Settings → Environments: an environment named `pypi`.
