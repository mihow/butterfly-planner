# CLAUDE.md - Project Instructions

## Project

A Claude-first Python project template. See @README.md for full documentation.

## IMPORTANT: Verify What You Change

**Code is not "done" until you've run it and seen it work.**

Use your judgment. If you changed it, verify it:

- Changed code? → `make ci` (runs lint, format, typecheck, tests)
- Changed a workflow? → Push and check the workflow output
- Added a pre-commit hook? → `pre-commit run --all-files`
- Changed Docker? → `docker compose build`
- Changed the CLI? → Run the CLI command you changed

Don't just run tests. Tests can pass while the code is broken.

## Commands

```bash
make install-dev  # Install with dev deps
make ci           # Full CI: lint, format-check, typecheck, test with coverage
make verify       # Full verification: imports, tests, smoke tests, CLI
make lint         # Just linting
make test         # Just tests
make docker-build # Build Docker image
```

Run `make help` to see all available commands.

## Learnings

- Clear settings cache between tests: `get_settings.cache_clear()`
- Use `tmp_path` fixture for temporary test files
- Always run `make ci` before committing - catches lint/format/type issues
- After pushing workflow changes, check Actions tab for actual results
