# Developer Notes

A running collection of design decisions, deferred improvements, and gotchas
that don't belong in a specific issue plan or batch progress doc. Add a new
section when you make a deliberate design choice that future-you (or another
contributor) might need to understand.

Each section should briefly explain **what was done**, **why**, and **what to do
next** when the time comes.

---

## Node ↔ Organization linking (deferred FK)

**Status:** Design intent only — not yet implemented.

**What was done.** In `data/nodes.tsv`, the column that holds the host
organization's name is called `organization_name`. The
`populate_redib_nodes` loader reads this column and stores the value in the
existing `Node.name` model field for now.

**Why.** The original column was just called `name`, which was ambiguous —
it actually contained the host organization's name (e.g., "BioImaC Biomedical
Imaging Center", "CIC biomaGUNE"). Renaming the TSV column makes the intent
explicit and sets up a clean future migration to a real FK relationship.
The model field rename was deferred because `Node.name` is referenced in ~16
files (6 Python, 10 templates) and a coordinated rename wasn't urgent.

**What to do next** (when ready to wire up the FK):

1. Add a new field on `Node`:
   ```python
   organization = models.ForeignKey(
       Organization,
       on_delete=models.PROTECT,
       null=True,
       blank=True,
       related_name='hosted_nodes',
       help_text='The host organization for this node',
   )
   ```
   Use `null=True` so existing rows survive the migration.

2. Update `populate_redib_nodes.handle()` to look up and assign the FK:
   ```python
   from core.models import Organization
   org = Organization.objects.filter(name=node_data['organization_name']).first()
   if not org:
       self.stdout.write(self.style.WARNING(
           f'  ⚠ Organization "{node_data["organization_name"]}" not found '
           f'for node {code}. Add it to data/organizations.tsv and re-run '
           f'populate_redib_organizations first.'
       ))
   defaults['organization'] = org
   ```
   Make sure `populate_redib_organizations` is called before
   `populate_redib_nodes` in `setup_base_database.py` (currently the order is
   nodes → organizations → users → equipment → funding agencies, so this
   would need to be flipped to organizations → nodes → users → equipment →
   funding agencies).

3. Decide whether to deprecate `Node.name` in favor of
   `node.organization.name`. If yes, that's a separate refactor that touches
   the 16 files mentioned above. If no, keep `Node.name` as a denormalized
   convenience field synced from the FK on save.

4. Populate `data/organizations.tsv` with the four ReDIB host organizations
   (BioImaC, CIC biomaGUNE, Imaging La Fe, TRIMA-CNIC) before running the new
   loader, otherwise all FKs will be null.

**Files involved (when implementing):**
- `core/models.py` (add FK on `Node`)
- `core/management/commands/populate_redib_nodes.py` (FK lookup in `handle()`)
- `core/management/commands/setup_base_database.py` (reorder steps)
- `data/organizations.tsv` (seed with the 4 host orgs)
- `data/README.md` (update nodes.tsv schema description)
- New migration: `core/migrations/000X_node_organization_fk.py`

---

## Editing Call dates after publication is safe (verified 2026-04-15)

**Status:** No change needed — documented to avoid re-investigation.

A coordinator can edit `submission_end` and `evaluation_deadline` on a
published `Call` and every downstream behaviour picks up the new values on
the next check. Specifically:

- `Call.is_open` reads `submission_end` live (`calls/models.py:63-70`).
- `application_submit` checks `call.submission_end > now()` live
  (`applications/views.py`).
- Scheduled tasks filter on current values every run —
  `check_call_deadlines` (`calls/tasks.py:22`),
  `send_evaluation_reminders` and `notify_overdue_evaluators` and
  `notify_coordinator_overdue_evaluations` all join through
  `application__call__evaluation_deadline` (`evaluations/tasks.py:29,87,145`).
- Assignment emails read `application.call.evaluation_deadline` live
  (`evaluations/tasks.py:345`).

`execution_start` and `execution_end` are cosmetic — no runtime code
branches on them.

**The one gotcha:** `Application.acceptance_deadline` is snapshotted from
`resolution_date + 10 days` when a resolution aggregates, not derived
from the call. Editing Call dates therefore has no effect on
already-resolved applications' acceptance clocks (which is the right
behaviour — those clocks belong to the applicant response, not the call
window).

No migration or code change is needed.
