# Development instructions

## Pre-commit hooks

This repository uses [pre-commit hooks](https://pre-commit.com/). Run `pre-commit install` before you make your first commit locally.

## Testing

This project uses [`pytest`][pt] for testing Python code. Run:

```shell
PYTHONPATH=. uv run pytest --cov=web/ --cov=kernel/engine/ ; uv run coverage-badge -f -o coverage.svg
```

[pt]: https://docs.pytest.org/en/stable/
