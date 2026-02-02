---
paths:
  - "**/*"
---

# Verification Rules

**Verify what you changed. Use your judgment.**

## The Principle

If you changed something, verify that specific thing works. Don't just run tests and hope.

| You changed... | Verify by... |
|----------------|--------------|
| Python code | `make ci` |
| A GitHub workflow | Push, then check the Actions tab |
| Pre-commit hooks | `pre-commit run --all-files` |
| Dockerfile or compose | `docker compose build` |
| CLI commands | Run the actual CLI command |
| Configuration files | Use what consumes the config |
| Dependencies | `make install-dev && make ci` |

## Quick Reference

```bash
make ci       # Full CI locally (lint, format, typecheck, test)
make verify   # Full verification (imports, tests, smoke, CLI)
make help     # See all available commands
```

## Red Flags

Don't say "done" if you only:
- Wrote tests (tests can be wrong)
- Read the code (reading ≠ running)
- Assumed it works (verify, don't assume)

## Common Mistakes

- Committing without running `make ci` → lint/format/type errors in CI
- Changing workflows without checking Actions tab → broken CI
- Adding pre-commit hooks without running them → hooks fail on commit
- Changing Docker without building → broken builds
