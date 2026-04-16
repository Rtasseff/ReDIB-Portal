# Plan: `setup_localtest3_database` — One-Shot Manual-Test Sandbox

> **Historical note (2026-04-16):** This is the original design doc for `setup_localtest3_database`. It frequently references the older `setup_localtest2_database` command, which has since been **removed** from the codebase (`localtest3` superseded it). The references below are kept for design-rationale context only.

## Context

`setup_localtest2_database` produces only **3 sample applications** (one draft, one in feasibility review, one evaluated). That covers a tiny slice of the workflow. To run the full manual-test pass — every phase, with options at each branch — the tester ends up creating data by hand or chaining several seed commands.

`seed_test_applicants` produces 17 apps but assumes `setup_base_database` (TSV-driven) ran first, uses 7 applicants, and dumps everything into a single open call, so the tester can't see "post-resolution" workflow (access tracking, publications, completed report) without manually advancing apps.

The user wants **one self-contained command** that:
- Creates a *small* user set (~10 accounts), all with password `testpass123` and verified email so allauth lets them log in immediately.
- Creates **two calls**: one **resolved** call (terminal-state apps + active access tracking + one completed/with-publication app) and one **open** call (apps strewn across every live phase with options at each branch).
- Lets the tester step through every phase end-to-end without hand-crafting data, and choose between "happy path" and alternative flows (multi-node, waitlist, reject, decline, edits-requested, competitive-funding protection).
- Prints a tester cheat-sheet at the end mapping each app code to "what to test with it."

The existing patterns in `setup_localtest2_database.py` (reset → nodes → equipment → orgs → users → funding agencies → calls → applications → summary) are the right scaffolding; the new command extends the application-creation step heavily, leaves the rest mostly intact, and rewrites `print_summary` as a structured cheat-sheet.

## Approach

Create `core/management/commands/setup_localtest3_database.py`. Copy the structure of `setup_localtest2_database.py` (steps 1–7) verbatim, then **replace** step 8 (`create_sample_applications`) with a richer generator and **rewrite** `print_summary` as a tester cheat-sheet. Same flags (`--reset`, `--yes`), same atomic-transaction wrapper, same `seed_email_templates` invocation.

All applicant-facing emails use `application.applicant_email`; pre-fill that field in the snapshot for every seeded app so the console-email backend shows the right `To:` line.

For terminal-state apps (PAST-*), write `Application.status` and resolution fields directly — do **not** route through `NodeResolutionService.apply_node_resolution`, which validates that the caller is a node coordinator. For the one mid-flight resolution scenario, create `NodeResolution` rows directly + invoke `aggregate_application_resolution` to exercise the aggregator.

Do **not** create `AccessGrant` (deprecated as of Phase 7).

---

## Users (~10 accounts, password `testpass123`, email verified)

| Role | Email | Notes |
|------|-------|-------|
| ReDIB Coordinator | `coordinator@test.redib.net` | Full access |
| Node Coordinator (CICbiomaGUNE) | `nc.cicbio@test.redib.net` | Node A |
| Node Coordinator (CNIC) | `nc.cnic@test.redib.net` | Node B |
| Evaluator (preclinical) | `eval.preclinical@test.redib.net` | area=`preclinical` |
| Evaluator (clinical) | `eval.clinical@test.redib.net` | area=`clinical` |
| Evaluator (radiochemistry+clinical) | `eval.radio@test.redib.net` | areas=`radiochemistry;clinical` (gives COI flexibility) |
| Applicant 1 | `applicant1@test.redib.net` | Full profile, Universidad de Barcelona |
| Applicant 2 | `applicant2@test.redib.net` | Full profile, Instituto de Investigacion Sanitaria |
| Applicant 3 | `applicant3@test.redib.net` | Full profile, Universidad de Barcelona (same org as eval.preclinical → COI) |
| Applicant 4 | `applicant4@test.redib.net` | **Incomplete profile** (no phone/org) — tests profile-completion middleware |

All accounts get an `EmailAddress` row with `verified=True, primary=True`.

## Reference data (carried over from localtest2)

- **3 nodes** — CICbiomaGUNE (A), BioImaC (B-skeleton), CNIC (C)
- **6 equipment** — 2 per node
- **2 organizations** — Universidad de Barcelona, Instituto de Investigacion Sanitaria
- **7 funding agencies** — same hardcoded list (AEI, ISCIII, ERC, Horizon Europe, NIH, La Caixa, "Other")

## Calls

| Code | Status | Submission | Evaluation deadline | Execution | Purpose |
|------|--------|------------|---------------------|-----------|---------|
| `COA-LIVE-2026` | `open` | started 7d ago, ends in 30d | now+45d | now+60d → now+150d | Apps at every **live** phase |
| `COA-PAST-2025` | `resolved` | -120d → -90d | -60d | -45d → +30d (active access window) | Terminal states + active access tracking + completed |

Both calls allocate all 6 equipment (`CallEquipmentAllocation` rows).

## Applications

### Open call `COA-LIVE-2026` (10 apps — every live phase)

| Code | Status | Applicant | Nodes | Special setup | What to test with it |
|------|--------|-----------|-------|----------------|----------------------|
| LIVE-001 | `draft` | applicant1 | 1 (A) | Wizard step 2 partially filled | Resume draft, finish & submit |
| LIVE-002 | `under_feasibility_review` | applicant1 | 1 (A) | FeasibilityReview pending for Node A | Single-node approve → goes to `pending_evaluation` |
| LIVE-003 | `under_feasibility_review` | applicant2 | 2 (A+B) | A=approved, B=pending | Node B decides; multi-node aggregation |
| LIVE-004 | `pending_evaluation` | applicant3 | 1 (A) | Past feasibility, no evaluators yet | Coordinator assigns evaluators (auto + manual) |
| LIVE-005 | `under_evaluation` | applicant1 | 1 (A) | 2 evaluators assigned, **0 scores** | Both evaluators submit scores; auto-transitions to `evaluated` |
| LIVE-006 | `under_evaluation` | applicant2 | 1 (A) | 2 evaluators assigned, **1 of 2 done** | Second evaluator submits |
| LIVE-007 | `evaluated` | applicant3 | 2 (A+B) | High final_score=10.5/12 | Multi-node resolution; tester can pick accept/waitlist/reject per node |
| LIVE-008 | `evaluated` | applicant1 | 1 (A) | Low final_score=4.0/12, **competitive funding** | Demonstrates reject-protected (NC cannot reject) |
| LIVE-009 | `accepted` | applicant2 | 1 (A) | `accepted_by_applicant=None`, deadline = now+8d | Applicant accepts or declines; handoff email fires |
| LIVE-010 | `pending` | applicant3 | 1 (A) | Waitlist, deadline = now+8d, `accepted_by_applicant=None` | Applicant accepts → NC promotes via Access Tracking |

### Resolved call `COA-PAST-2025` (6 apps — terminal & post-resolution)

| Code | Status | Applicant | Special setup | What to test with it |
|------|--------|-----------|---------------|----------------------|
| PAST-001 | `accepted` | applicant1 | `accepted_by_applicant=True`, `accepted_at=-30d`, `hours_approved` set, **no actual_hours_used** | Access tracking dashboard, mark equipment complete, log actual hours |
| PAST-002 | `completed` | applicant2 | All RequestedAccess `is_completed=True`, `actual_hours_used` set, **1 Publication attached** | Completion view, view existing publication, add another |
| PAST-003 | `declined_by_applicant` | applicant3 | `accepted_by_applicant=False`, `accepted_at=-40d` | Terminal-state display |
| PAST-004 | `rejected` | applicant2 | `final_score=3.5/12`, `resolution='rejected'` | Terminal-state display |
| PAST-005 | `rejected_feasibility` | applicant1 | FeasibilityReview status=`rejected` | Terminal-state display |
| PAST-006 | `expired` | applicant3 | Was accepted, applicant never responded, deadline = -2d | Terminal-state display, expired-acceptance flow |

**Total: 16 applications, 4 applicants, 2 calls.**

---

## Implementation outline — `core/management/commands/setup_localtest3_database.py`

### Structure (mirrors localtest2)

```python
class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true')
        parser.add_argument('--yes', action='store_true')

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts['reset']:
            self.reset_database(opts['yes'])
        nodes      = self.create_nodes()
        equipment  = self.create_equipment(nodes)
        orgs       = self.create_organizations()
        self.configure_site()
        call_command('seed_email_templates', verbosity=0)
        self.create_funding_agencies()
        users      = self.create_users(nodes, orgs)
        calls      = self.create_calls(nodes, equipment)
        apps       = self.create_live_applications(users, calls['open'], nodes, equipment)
        apps      += self.create_past_applications(users, calls['resolved'], nodes, equipment)
        self.print_cheatsheet(users, calls, apps)
```

### `reset_database` — clear in dependency order

Same list as localtest2 plus `Publication`, `NodeResolution`, `Evaluation`, `FeasibilityReview`, `RequestedAccess`, `Application`, `CallEquipmentAllocation`, `Call`, `FundingAgency`, `UserRole`, `User` (preserve superuser), `Equipment`, `Node`, `Organization`, `EmailAddress`. Skip if `--reset` not passed.

### `create_users` — set `EmailAddress.verified=True`

After each `User.objects.create_user(...)`, follow with:

```python
EmailAddress.objects.update_or_create(
    user=user, email=user.email,
    defaults={'verified': True, 'primary': True},
)
```

(import from `allauth.account.models`).

Set `phone`, `organization`, `position` on applicants 1–3; leave applicant 4 with no phone/org.

Evaluators get `UserRole(role='evaluator', areas=...)`; node coordinators get `UserRole(role='node_coordinator', node=...)`; coordinator gets `UserRole(role='coordinator')`; applicants get `UserRole(role='applicant')`.

### `create_live_applications` — helper signatures

Build a small `_make_app(code, applicant, status, nodes, equipment, **overrides)` helper that:

- Fills snapshot fields (`applicant_name`, `applicant_email`, `applicant_phone`, `applicant_entity`)
- Fills required content (`project_name`, `brief_description`, all 6 scientific fields, declarations)
- Sets `funding_agency_obj` to a random funding agency, `project_type='spanish_government'`
- Creates `RequestedAccess` for the listed equipment with `hours_requested=24`
- Sets `submitted_at = now - timedelta(days=7)` for non-draft

Then per-status add-ons:

- `under_feasibility_review`: `FeasibilityReview` per node, `status='pending'`, `is_feasible=None`. For LIVE-003, mark Node A's review `status='approved'`, `is_feasible=True`, `reviewed_at=-3d`.
- `pending_evaluation`: `FeasibilityReview` per node `status='approved'`, `is_feasible=True`.
- `under_evaluation`: feasibility approved + create N `Evaluation` rows. For LIVE-005, both evaluators have all 6 scores=`None`. For LIVE-006, evaluator 1 has full scores (sum=8), evaluator 2 has scores=`None`.
- `evaluated`: feasibility approved + 2 completed evaluations + `final_score=avg`. For LIVE-008, `has_competitive_funding=True` and pick a low-score evaluator distribution (sum=4).
- `accepted` (LIVE-009): all the evaluated setup + write `resolution='accepted'`, `resolution_date=-2d`, `acceptance_deadline=now+8d`, `accepted_by_applicant=None`. Also create `NodeResolution(resolution='accept')` for the involved node.
- `pending` (LIVE-010): same but `resolution='pending'`, `NodeResolution(resolution='waitlist')`, `acceptance_deadline=now+8d`.

For LIVE-005 / LIVE-006, evaluator assignment must respect COI (don't assign an evaluator from the same org as the applicant). Implementation: pick from evaluators whose `user.organization != applicant.organization` and whose `UserRole.areas` includes the app's `specialization_area`. Hardcode the assignments to keep this deterministic — no randomness.

### `create_past_applications`

Same `_make_app` helper. Per-status add-ons:

- `accepted` (PAST-001): full evaluation+resolution chain, `accepted_by_applicant=True`, `accepted_at=-30d`, `acceptance_deadline=-20d`, `hours_approved` set on each `RequestedAccess` (= `hours_requested`), `actual_hours_used=None`, `is_completed=False`.
- `completed` (PAST-002): same as PAST-001 + mark each `RequestedAccess.is_completed=True`, `actual_hours_used=hours_approved-2`, `completed_at=-10d`. Then create `Publication(application=app, title=..., authors=..., doi=..., publication_date=-5d, redib_acknowledged=True)`.
- `declined_by_applicant` (PAST-003): full chain + `accepted_by_applicant=False`, `accepted_at=-40d`.
- `rejected` (PAST-004): evaluations with low scores, `final_score=3.5`, `resolution='rejected'`, `resolution_date=-50d`. Create `NodeResolution(resolution='reject')`.
- `rejected_feasibility` (PAST-005): `FeasibilityReview(status='rejected', is_feasible=False, reviewed_at=-60d)`.
- `expired` (PAST-006): full chain + `accepted_by_applicant=None`, `acceptance_deadline=-2d`, `status='expired'`.

### `print_cheatsheet` — tester quick-reference

Print four sections:

1. **Login table** — every user, their role/areas, the test password, login URL.
2. **Calls** — code, status, submission window, execution window.
3. **Open call apps (LIVE-*)** — code, status, applicant, "what to test with it" column from the table above.
4. **Resolved call apps (PAST-*)** — same columns.
5. **Quick-start hint** — one line: "Open http://127.0.0.1:8000/, log in as `coordinator@test.redib.net` to see the dashboard, or as any applicant to see their applications."

Use `self.style.SUCCESS` / `self.style.WARNING` to color-code the section headers. Mirror the format of localtest2's `print_summary` so it feels familiar.

---

## Critical files

- **Create:** `core/management/commands/setup_localtest3_database.py`
- **Reuse (no edits):** `core/management/commands/setup_localtest2_database.py` — copy patterns from `reset_database`, `create_nodes`, `create_equipment`, `create_organizations`, `create_funding_agencies`, `configure_site`, `create_users`, `create_calls`
- **Reuse (no edits):** `applications/management/commands/seed_test_applicants.py` — copy the multi-status application/evaluation/feasibility patterns
- **Reuse (no edits):** `applications/services/node_resolution.py` — call `aggregate_application_resolution(app)` if needed (only for the one resolution-aggregation scenario, optional)
- **Update:** `CLAUDE.md` — add a row to the Management Commands table for `setup_localtest3_database`

---

## Manual testing instructions (what to give the user after running the command)

> Run once: `python manage.py setup_localtest3_database --reset --yes && python manage.py runserver`. Then open http://127.0.0.1:8000/ and walk the phases below in order. Every account uses password `testpass123`.

**Phase 1 — Browse calls** *(any user, or anonymous)*
Visit `/calls/` → confirm `COA-LIVE-2026` shows as Open and `COA-PAST-2025` as Resolved.

**Phase 2 — Application submission** *(applicant1)*
Log in → "My Applications" → open **LIVE-001** (draft) → walk steps 2–5, declarations, submit → confirm status flips to **Submitted**. Optional: try logging in as **applicant4** (incomplete profile) → confirm middleware redirects you to `/profile/`.

**Phase 3 — Feasibility review** *(nc.cicbio, then nc.cnic)*
- nc.cicbio: feasibility queue shows **LIVE-002** (single-node) and **LIVE-003** (multi-node, A side). Approve LIVE-002 → status moves to `pending_evaluation`. On LIVE-003, A is already approved.
- nc.cnic: queue shows **LIVE-003** (B side). Approve to test "all-approved → pending_evaluation". Or click "Request edits" on a fresh test app to exercise the edits flow.

**Phase 4 — Evaluator assignment** *(coordinator)*
Coordinator dashboard → call management → COA-LIVE-2026 → assign evaluators to **LIVE-004**. Try the auto-assign button (verify it skips evaluators in the applicant's organization), then add one manually.

**Phase 5 — Evaluation** *(eval.preclinical / eval.clinical / eval.radio)*
Each evaluator's "My Evaluations" shows their assignments. Submit scores for both evaluators of **LIVE-005** → app auto-transitions to `evaluated`. Submit the missing evaluation on **LIVE-006** to do the same.

**Phase 6 — Node resolution** *(nc.cicbio, nc.cnic)*
- nc.cicbio: open **LIVE-007** → submit a node decision (accept/waitlist/reject + per-equipment hours). nc.cnic does the same on the B side. When both decided, aggregator picks final state — try a mixed (one accept + one waitlist) combination first to see the waitlist path.
- nc.cicbio: open **LIVE-008** (low score, competitive funding) → confirm the "Reject" option is disabled / blocked.

**Phase 7 — Acceptance** *(applicant2 then applicant3)*
- applicant2: open **LIVE-009** (`accepted`, awaiting response) → click Accept (or Decline). Watch the console for the handoff email.
- applicant3: open **LIVE-010** (`pending` waitlist) → click Accept. App stays `pending` until promoted.

**Phase 8 — Waitlist promotion** *(nc.cicbio)*
Access Tracking → find LIVE-010 → click "Mark as Accepted" → confirms transition + handoff email.

**Phase 9 — Access tracking** *(nc.cicbio or applicant1)*
Open **PAST-001** access tracking → mark each equipment block complete with actual hours used.

**Phase 10 — Publications** *(applicant2)*
Open **PAST-002** → see existing publication → add a new publication with DOI + ReDIB acknowledgment ticked.

**Phase 11 — Reports** *(coordinator)*
Statistics dashboard → review counts per status, per call. Export Excel for COA-PAST-2025 → confirm download.

---

## Verification

```bash
# One-shot setup
python manage.py setup_localtest3_database --reset --yes

# Sanity checks
python manage.py shell -c "
from applications.models import Application
from django.db.models import Count
print(Application.objects.values('status').annotate(n=Count('id')).order_by('status'))
"

# Run server
python manage.py runserver
```

Expected: 10 LIVE-* apps spread across `draft`, `under_feasibility_review`(2), `pending_evaluation`, `under_evaluation`(2), `evaluated`(2), `accepted`, `pending`. 6 PAST-* apps spread across `accepted`, `completed`, `declined_by_applicant`, `rejected`, `rejected_feasibility`, `expired`. Login at http://127.0.0.1:8000/ as `coordinator@test.redib.net` / `testpass123` succeeds without email-confirmation prompt.
