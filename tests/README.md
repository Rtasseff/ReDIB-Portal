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
- **Seven files are not part of the suite.** `test_application_form_spec.py`,
  `test_phase1_phase2_workflow.py`, `test_phase3_feasibility_review.py`,
  `test_phase4_evaluator_assignment.py`, `test_phase5_evaluation_submission.py`,
  `test_phase6_node_resolution.py` and `test_phase6_resolution.py` are
  phase-era standalone scripts. They write to your real dev database, and
  most of them no longer pass. See
  [docs/TESTING.md](../docs/TESTING.md#legacy-standalone-scripts-not-part-of-the-suite).

Shared helper: `core/test_utils.py` (`create_complete_user`), for any test that
logs a user in and drives a real view.
