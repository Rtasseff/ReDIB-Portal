# tests/

The portal's automated test suite. The full guide (how to run it, how the
files are grouped, the manual-testing sandboxes) is
[docs/TESTING.md](../docs/TESTING.md).

```bash
python manage.py test tests reports     # the whole suite, from the repo root
```

Two things specific to this directory:

- **There is no `__init__.py`.** A bare `python manage.py test` therefore
  does not look in here; always name `tests`.
- **Every `test_*.py` here is a Django `TestCase` module.** The seven
  phase-era standalone scripts that used to sit alongside them were deleted on
  2026-09-29 (#90).

Shared helper: `core/test_utils.py` (`create_complete_user`), for any test that
logs a user in and drives a real view.
