---
name: verify
description: Verify code actually works (run this before declaring done)
disable-model-invocation: true
---

# Verification Checklist

Run this skill before declaring any task complete.

## Commands to Run

```bash
# Level 1: Imports
python -c "from my_project import *; print('imports ok')"

# Level 2: Unit tests
pytest -x

# Level 3: Smoke tests (actually run the code)
pytest tests/test_smoke.py -v

# Level 4: CLI execution
my-project info
my-project run --name verify-test

# Level 5: Lint and type check
ruff check src tests
mypy src
```

## MCP Server Verification

```bash
# Chrome DevTools MCP
npx @anthropic/mcp-server-chrome-devtools --version 2>/dev/null && echo "OK" || echo "NOT INSTALLED"

# Python LSP
which pylsp && pylsp --version 2>/dev/null && echo "OK" || echo "NOT INSTALLED"
```

## What "Done" Means

- [ ] All imports work (no ImportError)
- [ ] Unit tests pass (pytest -x)
- [ ] Smoke tests pass (tests/test_smoke.py)
- [ ] CLI commands execute successfully
- [ ] No lint errors (ruff check)
- [ ] Type check passes (mypy)
- [ ] Actually ran the code path that changed
- [ ] Verified output is correct

## NOT Done If

- Only wrote tests (tests can fake success)
- Only read the code (reading != running)
- Assumed it works (verify, don't assume)
- Got "no errors" but didn't check output
