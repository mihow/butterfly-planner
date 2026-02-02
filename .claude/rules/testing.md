---
paths:
  - "tests/**/*.py"
---

# Testing Rules

## Test Organization

- One test file per module: `test_<module>.py`
- Group related tests in classes: `class TestFeatureName`
- Use fixtures from `conftest.py` for shared setup

## Naming

- Test functions: `test_<behavior>` or `test_<scenario>_<expected>`
- Fixtures: descriptive nouns (`sample_user`, `mock_api`)

## Markers

Use pytest markers for categorization:

```python
@pytest.mark.slow        # Long-running tests
@pytest.mark.integration # Requires external services
@pytest.mark.unit        # Fast, isolated tests
```

## Best Practices

- Test behavior, not implementation
- One assertion concept per test (multiple asserts OK if related)
- Use `tmp_path` for file operations
- Clear caches: `get_settings.cache_clear()`
