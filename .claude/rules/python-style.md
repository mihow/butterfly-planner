---
paths:
  - "src/**/*.py"
  - "tests/**/*.py"
---

# Python Style Rules

## Type Annotations

Use modern Python 3.10+ style:

```python
# CORRECT
def process(items: list[str], config: dict[str, int] | None = None) -> tuple[str, int]:
    ...

# WRONG - don't use typing imports for builtins
from typing import List, Dict, Optional
```

## Imports

- Use absolute imports from package root
- Group: stdlib, third-party, local (separated by blank lines)
- Use `from x import y` for specific items

## Error Handling

- Use specific exception types
- Return `Result` objects for expected failures
- Raise exceptions for unexpected errors

## Documentation

- Docstrings for public functions (Google style)
- Type hints are documentation - skip redundant docstrings
- Comments explain *why*, not *what*
