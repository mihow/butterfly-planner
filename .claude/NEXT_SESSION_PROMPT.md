# Continuation Prompt

## Project
Claude-first Python project template: https://github.com/mihow/project-template-claude

## What Was Done
- Created full template with .claude/ directory (CLAUDE.md, rules, skills, agents)
- MCP server config for chrome-devtools (headless) and Python LSP
- Verification-first approach with smoke tests and `/verify` skill
- Python 3.12+, uv, pytest, ruff, mypy, Docker, GitHub Actions
- Weekly docs checker workflow (.github/workflows/check-docs.yml)
- Best practices documentation in .claude/docs/

## CI Failures to Fix

### 1. Mypy error in models.py:50
```
src/my_project/models.py:50:11: error: Missing type parameters for generic type "dict"
    data: dict | None = None
```
Fix: Change to `data: dict[str, str] | None = None` or similar

### 2. Ruff PLC0415 errors in conftest.py
Imports inside functions - move to top or add `# noqa: PLC0415` comments

### 3. check-docs.yml permissions
Added `permissions: contents: write, issues: write` but not pushed yet

## Files Modified (not yet pushed)
- `.github/workflows/check-docs.yml` - added permissions block

## Commands to Fix & Push
```bash
conda activate py11
cd /Users/michael/Projects/mikes-meta-agent

# Fix mypy error
# Edit src/my_project/models.py:50 - add type params to dict

# Fix ruff errors in conftest.py
# Either move imports to top or add noqa comments

# Verify
PYTHONPATH=src ruff check src tests
PYTHONPATH=src mypy src
PYTHONPATH=src pytest -q

# Push fixes
git add -A && git commit -m "fix: resolve mypy and ruff CI errors" && git push
```

## Key Files
- `src/my_project/models.py:50` - dict type needs params
- `tests/conftest.py:29,53` - imports inside functions
- `.github/workflows/check-docs.yml` - permissions added
- `.claude/docs/claude-code-best-practices.md` - reference doc
- `.claude/rules/verification.md` - verification requirements
- `tests/test_smoke.py` - smoke tests that run CLI
