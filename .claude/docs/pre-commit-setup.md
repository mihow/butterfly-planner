# Pre-commit Hooks Setup

## What Was Fixed

### Linting Issues
1. **SIM117**: Combined nested `with` statements in tests (3 occurrences)
2. **PLC0415**: Moved import to top-level in `test_core.py`
3. **Type errors**: Added proper type annotations and null checks

### Files Modified
- `tests/test_cli.py`: Combined nested `with` statements
- `tests/test_core.py`: Moved import, added null checks
- `tests/test_models.py`: Fixed enum value comparisons
- `tests/conftest.py`: Added type annotations
- `tests/test_smoke.py`: Fixed truthy checks

## Pre-commit Hooks

Pre-commit hooks now run automatically before each commit to catch issues locally.

### Installed Hooks

1. **Ruff** - Fast Python linter and formatter
2. **Mypy** - Static type checking
3. **Basic checks** - Trailing whitespace, EOF, YAML/TOML/JSON validation

### Usage

```bash
# Hooks run automatically on git commit
git commit -m "Your message"

# Run manually on all files
pre-commit run --all-files

# Run on staged files only
pre-commit run

# Update hook versions
pre-commit autoupdate
```

### Bypass (Not Recommended)

```bash
# Skip hooks (only in emergencies!)
git commit -m "Message" --no-verify
```

## Why Weren't These Caught Before?

The `.pre-commit-config.yaml` file didn't exist. Even though `pre-commit` was listed as a dev dependency, it wasn't configured or installed.

Now:
1. Configuration exists in `.pre-commit-config.yaml`
2. Hooks are installed in `.git/hooks/pre-commit`
3. They run automatically before every commit

## CI/CD Integration

The GitHub workflow already runs these same checks, but now you'll catch them locally first, saving CI time and avoiding failed builds.

## Troubleshooting

### Import Errors

Make sure you're using the Python 3.12 environment:

```bash
source .venv312/bin/activate
uv pip install -e ".[dev]"
```

### Hooks Not Running

Reinstall hooks:

```bash
pre-commit uninstall
pre-commit install
```

### Hook Failures

Fix the issues and commit again:

```bash
# Hooks auto-fix most issues
git add .
git commit -m "Message"  # Hooks run and fix issues
git add .  # Stage the fixes
git commit -m "Message"  # Commit the fixes
```
