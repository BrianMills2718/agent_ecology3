# Tests Directory

The pytest suite is flat under `tests/`.

## Running Tests

```bash
# All tests
uv run pytest tests/ -v

# Single test
uv run pytest tests/test_runtime_smoke.py
```

## Conventions

1. Prefer real boundary checks over stand-in behavior.
2. Keep provider-free fixtures visibly separate from authentic runs.

## Adding Tests

Run the focused file for the changed behavior, then `uv run pytest tests/ -v` before
claiming full-suite verification.
