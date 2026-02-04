# CLAUDE.md - Project Instructions

## Project

Butterfly Planner - GIS layers for butterfly abundance and species diversity forecasting in Oregon and Washington. Uses butterfly observation data, environmental data, and flower phenology to predict optimal butterfly viewing locations by week of the year. Isochrone mapping for driving time analysis is a key feature.

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

---

## Cost Optimization

**Every API call costs money. Be efficient.**

1. **Monitor context usage** - Keep under 40% (80K/200K tokens) when possible
   - Check regularly with token counter
   - Summarize, compact & commit work to reset context
   - Use offset/limit when reading large files

2. **Add learnings with references** - Document fixes with file:line references
   - Example: `src/module/file.py:42`
   - Update CLAUDE.md or relevant docs with specific locations

3. **Prefer command line tools** to reduce context
   - Use `jq` for JSON, `grep` for search, `git` for history
   - Avoid reading entire files when possible
   - Never launch interactive CLI tools (use `--no-interactive`, etc.)
   - Prefer language server plugins over grep for go-to-definition, find-references

4. **Fix style issues at the end** - Ignore line length and type errors until done, then use `make ci`

## Python Type Annotations

Use modern style (Python 3.10+):

```python
# ✅ CORRECT - use built-in types and | None
def process(items: list[str], config: dict[str, int] | None = None) -> tuple[str, int]:
    ...

# ❌ WRONG - old style typing imports
from typing import Dict, List, Optional
def process(items: List[str], config: Optional[Dict[str, int]] = None) -> Tuple[str, int]:
    ...
```

**Rules:**
- Use `list`, `dict`, `tuple`, `set` directly (not from `typing`)
- Use `X | None` instead of `Optional[X]`
- Use `X | Y` instead of `Union[X, Y]`

## Think Holistically

Before diving into code:
- What is the **PURPOSE** of this tool?
- Why is it failing on this issue?
- Is this a symptom of a **larger architectural problem**?
- Take a step back and analyze the **root cause**

Don't just fix symptoms. Understand the underlying architecture first.

## Development Best Practices

- **Commit often** - Small, focused commits are easier to review and rollback
- **Use `git add -p`** - Interactive staging to add only relevant changes
- **Use TDD** - Write tests first when possible
- **Keep it simple** - Evaluate alternatives before complex solutions
- **Measure twice, cut once** - Plan before implementing

## Using Subagents

Use subagents to reduce context usage and parallelize work:

**Research Subagent (Sonnet)**
- Search the repo, web research, gathering context
- Report back with file paths, line numbers, and relevant excerpts

**Implementation Subagent (Haiku)**
- Execute small, well-defined chunks of work
- Complete one task, report back for review before continuing

**Pattern:**
1. Research subagent gathers context and reports findings
2. Main agent reviews and plans implementation steps
3. Implementation subagent executes one step at a time
4. Main agent reviews each step before proceeding

## Command Line Shortcuts

```bash
# Quick file inspection with git
git ls-files | wc -l              # Count files
git ls-files | grep "*.sql"       # Find files by pattern
git log --oneline -10             # Recent changes

# JSON inspection with jq
cat file.json | jq .key           # Parse field
cat file.json | jq .              # Pretty print
```

---

## Learnings

*(Add items here as you discover them)*

- Clear settings cache between tests: `get_settings.cache_clear()`
- Use `tmp_path` fixture for temporary test files
- Always run `make ci` before committing - catches lint/format/type issues
- After pushing workflow changes, check Actions tab for actual results

### uv gotchas
- `[project.optional-dependencies]` are extras, NOT dev deps. `uv sync` alone skips them. Use `uv sync --extra dev` (Makefile:36). Only `[tool.uv] dev-dependencies` are installed by default with `uv sync`.
- Never set `UV_SYSTEM_PYTHON=1` alongside `uv sync`. `uv sync` creates a `.venv`; the env var tells `uv run` to bypass it. The two are mutually exclusive. (.github/workflows/test.yml:21)

### mypy vs Pyright (VS Code)
- If mypy flags errors that VS Code doesn't show, it's likely a divergence, not a config problem. Key differences: Pyright handles `try/except ImportError` fallback patterns specially and won't flag redefinitions in the except branch. mypy does. Pyright doesn't enforce `warn_return_any` or `warn_unused_ignores` by default; mypy strict does. (src/butterfly_planner/flows/fetch.py:26)
- `resp.json()` and `json.load()` return `Any`. With `warn_return_any`, assign to a typed local before returning rather than using `cast`. (src/butterfly_planner/flows/fetch.py:70)
- `# type: ignore[no-redef]` vs `[misc]`: mypy uses `no-redef` for the first redefinition in a try/except but `misc` for subsequent ones. Check the actual error code before writing the ignore. (src/butterfly_planner/flows/fetch.py:35)

### Debugging CI failures
- `gh run view --log-failed` can return empty output. Use the API instead: `gh api repos/{owner}/{repo}/actions/runs/{run_id}/jobs` to get job IDs, then `gh api repos/{owner}/{repo}/actions/jobs/{job_id}/logs` for the full log.
- A 12-second CI failure where install passes but the next step fails instantly usually means the tool binary isn't on PATH — check the installed package list in the log before assuming the command itself is wrong.
