---
name: tdd
description: Test-driven development workflow
---

# Test-Driven Development

Use this skill when implementing new features or fixing bugs.

## Red-Green-Refactor Cycle

1. **Red**: Write a failing test that defines the expected behavior
2. **Green**: Write minimal code to make the test pass
3. **Refactor**: Clean up while keeping tests green
4. **VERIFY**: Actually run the code (not just tests)

## Verification Checklist

After Green phase, ALWAYS:
```bash
# 1. Tests pass
pytest -x

# 2. Imports work
python -c "from my_project import *; print('ok')"

# 3. Actually run the code path you changed
my-project info  # or relevant command

# 4. Smoke tests pass
pytest tests/test_smoke.py -v
```

## CRITICAL

Unit tests can be written to pass. They prove you wrote code that satisfies your test, NOT that the code actually works.

After implementing, you MUST:
- Run the actual code path (not through tests)
- Verify the output is correct
- Check for warnings/errors

## Example Usage

```
/tdd Add a function to validate email addresses
```

Then:
1. Write test for valid email → RED (fails)
2. Implement validation → GREEN (passes)
3. Refactor if needed
4. **VERIFY**: Run actual validation with real inputs
