# Handoff — `feature/resolution-report`

> **Merged 2026-08-21 (PR #40).** Record only — the branch and its worktree are
> gone. #20 shipped with no deviations from this brief, which makes it the one
> bucket of six where the brief's claims all held. **One item still open:** the
> Spanish column headers in `COLUMN_HEADERS` are this brief's proposal
> (Question 1), not something ReDIB has published — Ryan confirms or corrects.


<!-- Copy of docs/developer/handoff-template.md, seeded by scripts/new-worktree.sh.
     Lives at docs/handoffs/resolution-report.md on the branch. Keep "Status" current. -->

| | |
|---|---|
| Branch | `feature/resolution-report` |
| Worktree dir | `/home/rtasseff/projects/ReDIB-Portal-wt/resolution-report` |
| Base | `main` @ `0cae2d5` |
| Created | 2026-08-21 |
| Runserver port | 8002 |
| Handoff session | `main` checkout at `~/projects/ReDIB-Portal/` |

Read this first, then `CLAUDE.md`, then `docs/README.md`. This directory is
a git worktree: it *is* this branch — do not `git checkout` another branch
here (see `docs/developer/worktrees.md`).

**Development document.** These are instructions for the agent session working
in this worktree. Once the branch merges, this file lands on `main` as a
record — on the production VPS it is history, not a task list.

## Goal

Produce the per-call **resolution table** ReDIB publishes once a call is
resolved — in English and Spanish, as two separate tables — from the portal
instead of by hand.

There is no way to generate this today. On **2026-07-23** the REDIB-2601 table
was assembled by hand out of `manage.py shell`, one query at a time, and
pasted into a document. That is backlog **#20**, and it is the last bucket of
the October 2026 round.

It is wanted before REDIB-2601's successor publishes results (~2027-01/02),
so there is no schedule pressure — but it is also the **most isolated** bucket
of the six: `reports/` only, no migration, no email, no beat task, no state
change. Treat that isolation as a constraint to protect, not a coincidence.

## Scope

**In:**

- A coordinator-only **resolution table page**, per call, rendering the EN and
  ES tables one above the other, in HTML that survives copy-paste into a
  document or a CMS.
- A **CSV download** per language (two URLs, or one with a `lang` argument).
- A **call picker** so the page is reachable — a link/section on the existing
  reports dashboard listing calls newest-first.
- The **node public display-name map** (#20 notes it "doesn't exist anywhere in
  code yet and needs a home"). Its home is `reports/`; see decision 4.
- Tests in `tests/test_resolution_report.py`.

**Out** (do not do here — belongs on `main` or another bucket):

- **#21**, the public past-calls archive. Deferred, confirmed 2026-08-18.
  Everything you build here is **coordinator-only**; no anonymous surface.
- **#44**, the declined-vs-unfilled `hours_approved=0` ambiguity. The round
  plan calls this table "the natural moment to fix it" — on inspection it
  isn't: this table has **no hours column**, so there is nothing in it to
  disambiguate. Fixing #44 means a new explicit state on `RequestedAccess`,
  which is a migration and a different bucket. Leave it alone.
- **XLSX export.** `openpyxl` is already a dependency and `reports/utils.py`
  already builds a workbook, so it would be easy — and it is still two more
  code paths to test for no gain, because CSV opens in Excel. Not this round.
- **A `ReportGeneration` row.** `export_call_report` writes one; this report
  must not. See decision 9 — it is what keeps "read-only" literally true.
- **Any Django i18n / gettext infrastructure.** See decision 3.
- **Any migration.** See decision 10.

## Acceptance

1. For a seeded call, the page renders **both** tables, and both match the
   underlying `NodeResolution` rows exactly — same row count, same order, same
   resolutions, differing only in the label language.
2. **Read-only.** Loading the page or downloading either CSV writes nothing.
   Assert it in a test, not just by inspection: wrap the request in a check
   that no row was created/updated in `Application`, `NodeResolution`,
   `ReportGeneration`, or any `Historical*` table.
3. The four edge cases in decision 7 each render without an exception and
   without inventing data: a submitted application with no node resolution, a
   `NodeResolution` with `resolution=''`, an applicant with no profile
   organization, and a call with zero non-draft applications.
4. A **multi-node** application renders correctly (decision 6). REDIB-2601 has
   none, so this one only exists in your fixtures — build it deliberately.
5. `python manage.py check` and `python manage.py makemigrations --check` clean.
   `makemigrations --check` failing means you added a model change; see
   decision 10.
6. Suite not worse than the baseline: **`python manage.py test tests` = 351**
   and **`python manage.py test` = 11**. Take those counts yourself before you
   start and record them in Status. (Two commands because `tests/` has no
   `__init__.py` and default discovery skips it — that is #46, not your bug.)

**The REDIB-2601 regression numbers are not checkable here.** #20 records the
real answer — **24 rows, 16 accepted / 7 wait list / 1 rejected**, from 27
applications of which 3 were drafts — but that call exists only on production.
The dev sandbox has `COA-LIVE-2026` and `COA-PAST-2025` and nothing else. So:
build fixtures that reproduce the *shape* (a call with drafts to exclude and a
mix of all three resolutions), and leave the 24/16/7/1 check to the production
session. It is safe for prod to run precisely because of acceptance item 2.

## Context & decisions already made

These are **settled**. Do not reopen them; if one looks wrong, park it in
"Questions" and keep going with the rest.

**1. The resolution comes from `NodeResolution.resolution`.** Not
`Application.status`, not `Application.resolution`. The published resolution is
the node coordinator's decision, and it is independent of what the applicant did
afterwards: REDIB-2601-026 publishes as *Accepted* even though the application
later went `expired` because the applicant never answered. Reading the status
field instead would silently republish a different fact.

**2. Rows are every non-draft application, ordered by code.**

```python
Application.objects.filter(call=call).exclude(status='draft').order_by('code')
```

Drafts are excluded because they were never submitted (and have no code —
`reports/utils.py` prints `app.code or 'DRAFT'` for exactly this reason).
Everything else that was submitted appears, including anything rejected at
feasibility.

**3. Two static label maps. No gettext, no `.po` files, no `LOCALE_PATHS`.**
This project has none of that infrastructure — `USE_I18N = True` and
`LANGUAGE_CODE = 'en-us'` in `redib/settings.py:134` are the whole of it, there
is not a single `gettext` call in the codebase, and standing one up for eight
strings would be the tail wagging the dog. The mechanism is a dict:

```python
RESOLUTION_LABELS = {
    'en': {'accept': 'Accepted', 'waitlist': 'Wait List', 'reject': 'Rejected'},
    'es': {'accept': 'Aceptada',  'waitlist': 'En espera', 'reject': 'Rechazada'},
}
```

Those exact strings come from #20 and are what ReDIB published in July. Do not
adjust them. Column headers are **not** in #20, so use these and see Questions:

| | EN | ES |
|---|---|---|
| col 1 | Application | Solicitud |
| col 2 | Organization | Organización |
| col 3 | Node | Nodo |
| col 4 | Resolution | Resolución |

**4. Node public display names live in a `reports/` dict, not on the model.**
The published names are **BioImaC / biomaGUNE / TRIMA / IIS La Fe**, and no
existing field gives them: `Node` has no `name` column at all (`Node.name` is a
read-only property returning `organization.name`), and the host organizations'
`short_name`s are `BioImaC`, `CIC biomaGUNE`, `TRIMA-CNIC` and `''` — right for
one node out of four.

```python
NODE_PUBLIC_NAMES = {
    'BioImaC':       'BioImaC',
    'CIC-biomaGUNE': 'biomaGUNE',
    'TRIMA@CNIC':    'TRIMA',
    'IIS-LaFe':      'IIS La Fe',
}
```

Look it up **defensively** — an unknown node code must degrade, never raise:
`NODE_PUBLIC_NAMES.get(node.code) or node.organization.short_name or node.organization.name`.

Why a dict and not a `Node.public_name` field: a field means a migration and a
new column in `data/nodes.tsv`, and that TSV is **coordinator-owned** — it feeds
the ReDIB website and other reporting, not just the portal. Adding portal-only
columns to it is exactly the TSV↔DB tangle **#43** exists to sort out, and #43
is deliberately parked. Promoting the map to a model field later is a one-hour
job once #43 has a design; doing it now drags this bucket into that fight.

**5. The organization cell is the applicant's profile organization.**
`application.applicant.organization`, rendered `short_name · name` with that
`·` separator, falling back to `name` alone when `short_name` is blank or equal
to `name`. Four of REDIB-2601's 24 rows take that fallback (Universidad de
Navarra, Hospital Universitario La Paz, Hospital Universitario de Guadalajara,
Imaging La Fe). It is **not** the free-text `Application.applicant_entity`,
which is what a lazier query would reach for.

`User.organization` is nullable (`on_delete=SET_NULL`), so it *can* be absent.
When it is, fall back to `application.applicant_entity`, then to an empty cell —
and flag the row in the on-page warnings (decision 8) so the coordinator can fix
the profile before publishing. Never leave a row out because its organization is
missing.

**6. A multi-node application is one row, with stacked cells.** Every REDIB-2601
application requested equipment at exactly one node, so this is future-proofing —
but #20 explicitly leaves the choice open, and the choice is: **one row per
application**, with the node cell and the resolution cell each listing that
application's nodes in the same order, one per line. Two reasons. A reader
counts rows to count applications, and splitting one application across rows
makes that count wrong. And an application accepted at one node and rejected at
another is a real thing the table has to be able to say out loud, which a single
aggregated cell cannot.

**7. Missing data is shown as missing. Never inferred.**

| Case | Renders as |
|---|---|
| Submitted application with **no** `NodeResolution` at all | `—` in both languages, row still present |
| `NodeResolution.resolution == ''` (the "Not Decided" choice) | `—`, treated the same as no resolution |
| Applicant with no profile organization | `applicant_entity`, else empty cell |
| Call with zero non-draft applications | An empty-state message, not an empty `<table>` |

The temptation is to fill a missing resolution from `Application.status` —
"it's `rejected_feasibility`, so print Rejected". Don't. This table reports what
the nodes recorded; a feasibility rejection is a different decision by a
different person, and quietly relabelling it as a node resolution puts a
sentence in a published document that nobody at the node ever said.

**8. Not gated on `resolutions_released` — but say so.** `release-gate` (merged
2026-08-21) added `Call.resolutions_released`; do **not** refuse to render for a
call where it is `False`. This page is coordinator-only and read-only, and Ryan
wants to watch the table form. Instead show a banner above the tables when the
call has not released resolutions, saying the table is provisional.

Three warnings belong **above** the tables, in the page chrome:

- the call has not released resolutions to nodes yet;
- these application codes have no recorded node resolution;
- these application codes have an applicant with no profile organization.

They must never appear **inside** a table or in a CSV. The tables are the
publishable artifact and have to stay clean enough to copy straight out.

**9. No `ReportGeneration` row, for either the page or the CSVs.** The round
plan's acceptance line for this bucket is "Read-only: it must not mutate
anything", and writing an audit row would make that false. The existing xlsx
export writes one (`reports/views.py:export_call_report`) — that is a precedent
to notice and not follow. `ReportGeneration.REPORT_TYPES` has no matching choice
anyway, so adding tracking would also mean a migration.

**10. No migration in this bucket.** Nothing here needs a schema change, and
`makemigrations --check` is an acceptance item so that stays honest. If you
reach a point where you believe you need one, **stop and ask in Questions**
rather than adding it — a migration would change this bucket's whole risk
profile and its review tier.

## The shape of the thing

Suggested, not mandated — deviate if the code reads better, but keep the
separation between *computing rows* and *rendering them*:

- `reports/resolution_table.py` (new) — the label maps, the node map, and one
  function `build_resolution_table(call, lang)` returning plain row dicts plus
  the warning lists. No HTML, no HttpResponse. This is the piece the tests
  should mostly hit.
- `reports/views.py` — a `@coordinator_required` view rendering both languages,
  plus the CSV view(s). `get_object_or_404` for the call.
- `reports/urls.py` — append; the app is namespaced `reports:`.
- `templates/reports/` — the page. There is no shared table partial yet;
  a small one used twice beats two near-identical blocks.
- Add the entry point to `templates/reports/statistics_dashboard.html`.

Query notes: `select_related('applicant__organization')` and
`prefetch_related('node_resolutions__node__organization')` — the naive version
is N+1 across four joins on 24 rows.

Fixture note that will bite you otherwise: **`Node` has no settable `name`** —
`Node.objects.create(name=...)` raises `AttributeError: property 'name' of
'Node' object has no setter`. Build them as
`Node.objects.create(code='TEST-NODE', organization=org, location='Testville')`,
and note `Organization` requires `country` and `organization_type`.

## Conflict watchlist

Genuinely short — this is the most isolated bucket of the round:

- `reports/` — **nothing else on `main` or in any other bucket touches this
  app.** All five earlier buckets are merged and their worktrees are gone; you
  are the only live branch besides parked marketing.
- `templates/reports/statistics_dashboard.html` — same, but it is the one file
  where a `main`-side copy tweak could land while you work. Rebase before you
  open the PR.
- The three shared files the round plan makes every brief name —
  `redib/celery.py`'s beat schedule, `seed_email_templates.py`, and
  `TEMPLATE_TYPES` in `communications/models.py` — **you touch none of them.**
  No email, no beat task. If you find yourself editing one, you have left scope.
- `feature/marketing-site` is parked and will conflict with a lot at *its*
  merge next year, including any app's `urls.py`. That is its problem to solve,
  not a reason to shape this bucket differently.

## Status

- [x] Baseline counts recorded: `python manage.py test tests` = 351 OK, `python manage.py test` = 11 OK (both match expected baseline)
- [x] `build_resolution_table` + label/node maps — `reports/resolution_table.py`
- [x] Page view, both languages, warnings — `reports/views.py:resolution_report`, `templates/reports/resolution_report.html` + `_resolution_table_block.html`
- [x] CSV export — `reports/views.py:resolution_report_csv`, one URL with a `lang` path segment (`en`/`es`); unknown lang 404s
- [x] Entry point from the reports dashboard — new "Resolution Tables" card in `templates/reports/statistics_dashboard.html`, calls newest-first by `submission_start`
- [x] Tests, including multi-node and all four edge cases — `tests/test_resolution_report.py` (22 tests)
- [x] Read-only assertion test — `ResolutionReportReadOnlyTests`, counts `Application`/`NodeResolution`/`ReportGeneration`/`HistoricalApplication`/`HistoricalNodeResolution` before and after
- [x] `check` + `makemigrations --check` + full suite — all clean; `python manage.py test tests` = 373 (351 + 22 new), `python manage.py test` = 11 (unchanged — new tests live in `tests/`, not `reports/tests.py`, so default discovery per #46 doesn't pick them up)
- [x] PR opened — https://github.com/Rtasseff/ReDIB-Portal/pull/40

**Note:** the dev sqlite DB in this worktree hadn't had `calls.0004_call_resolutions_released_and_more` (release-gate) applied yet, even though `main` has it merged. Ran `python manage.py migrate` to catch it up before doing manual rendering checks — unrelated to this bucket, no migration was added here (`makemigrations --check` reports "No changes detected").

## Questions for the handoff session

Park answers here; don't block on them — every one has a stated default you can
build on.

1. **Spanish column headers** (decision 3) — Solicitud / Organización / Nodo /
   Resolución is my proposal, not something ReDIB has published. Ryan is the
   authority. Build with it; expect it may be corrected before merge.
2. **Does the table need a date or call title header line** above it, for the
   published document? #20 doesn't say. Default: render the call code and title
   above each table, outside the table element.
3. Anything in #20's recipe that turns out not to match the code — say so
   loudly. The `release-gate` brief listed four call sites and there were five;
   a brief's claims are things to check, not facts.

## Return protocol

1. Keep **Status** current; note anything you deviated from and why.
2. `python manage.py check`; `python manage.py makemigrations --check`;
   `python manage.py test tests` **and** `python manage.py test` — record both
   counts against the 351 + 11 baseline.
3. Push the branch and open a PR against `main`. PR body = the review packet:
   what changed, deviations from this brief, both test counts, the EN and ES
   tables **quoted as rendered** for a small fixture call so the wording can be
   reviewed without running anything, and any pre-existing bug you noticed but
   did not fix.
4. **Review tier for this bucket: targeted read + suite** — the handoff session
   reads the diff and runs the suite. **Do not run `/code-review`.** It is a
   read-only, coordinator-only, migration-free, email-free report; the round
   plan assigns it the lighter tier and paying for both layers is explicitly
   against `docs/developer/worktrees.md` § Review policy.

## Running locally (this worktree)

```bash
cd /home/rtasseff/projects/ReDIB-Portal-wt/resolution-report
source venv/bin/activate
python manage.py runserver 8002
```

`.env`, `db.sqlite3` and `media/` were copied from the `main` checkout at
creation time — that sandbox currently holds `COA-LIVE-2026` and
`COA-PAST-2025` left over from the `release-gate` walkthrough, which is a
usable starting point but has no resolved multi-node call. To rebuild:
`python manage.py setup_localtest3_database` (see `docs/DEVELOPMENT.md`).

**WSL note:** if `localhost:8002` doesn't reach runserver from the Windows
browser, bind `0.0.0.0:8002` and use the WSL IP with `ALLOWED_HOSTS` set —
see [worktrees.md](../developer/worktrees.md) for the full write-up.
