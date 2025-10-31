# Development instructions

## Pre-commit hooks

This repository uses [pre-commit hooks](https://pre-commit.com/). Run `pre-commit install` before you make your first commit locally.

## Testing

This project uses [`pytest`][pt] for testing Python code. Run `just test` to run all tests and update coverage badge image.

## Puzzle Creation Feature (Security & Validation)

When adding or modifying the "create a puzzle" feature, keep these invariants and safety constraints:

1. Filename restrictions: `puzzleName` must match `^[\w\- ]{1,80}$` (ASCII word chars, dash, underscore, space). Reject anything else before touching the filesystem.
2. Path traversal defense: Always resolve the target path and assert it remains inside the `puzzles/` directory before writing.
3. No overwrite: Reject save if a puzzle with the same name already exists.
4. Size limits (defense-in-depth): Max 50 species and 50 reactions per puzzle to avoid resource abuse; adjust cautiously if raising.
5. Internal consistency checks:
   - `speciesIfReactants` / `speciesEnergies` lengths must equal `speciesNames` length.
   - Each reaction must have exactly 4 slots (reactant1, reactant2, product1, product2) — blanks allowed.
   - Every non-blank species referenced in reactions must appear in `speciesNames`.
   - Each `reagentPERs[reagent]` boolean list length must equal the number of reactions.
   - Species names must be unique; energies must be finite numbers.
6. Atomic write: Write to a temporary file in `puzzles/` then `os.replace` it into place to avoid partial files on crash.
7. Backwards compatibility: The saved JSON includes `reagents` (list of reagent keys) plus `reagentPERs` mapping. Keep both until older clients are deprecated.
8. Rate limiting & auth: The `/save` endpoint is limited to `5 per minute` and gated by the `CKWATSON_PUZZLE_AUTH_CODE` env var. Tests disable the limiter (`limiter.enabled = False`).
9. Schema validation: JSON Schema (`puzzles/schema.json`) is enforced before the deeper semantic validations run in `save_a_puzzle` (defense-in-depth layering).
10. Error responses: Always return a JSON object `{status: 'danger'|'success', message: <human-readable>}` for frontend toast handling.

See `web/save_a_puzzle.py` and `tests/test_save_endpoint.py` for the authoritative logic and test coverage.

Future hardening ideas:

- Add per-user ownership & authentication beyond a shared code.
- Support puzzle versioning instead of outright duplicate rejection.
- Persist puzzles in a database with audit logs.
- Add optional transition state energies to saved format.
- Implement edit / delete operations with similar safety checks.

[pt]: https://docs.pytest.org/en/stable/
