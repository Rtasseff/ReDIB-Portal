# ReDIB COA Portal - Issue Action Plan (Final)

## Prioritized Implementation Order

### Tier 1: Must Fix Before Launch

**Issue #9 - Evaluator email incorrect info**
Effort: 30 min | Type: Content fix

Fix the evaluator assignment email template in `seed_email_templates` command. Currently says "5 criteria (1-5 scale)", should say "6 criteria (0-2 scale)" to match the actual evaluation form. The evaluation system uses 6 scoring criteria on a 0-2 scale (max total score: 12). Verify by cross-referencing the email text with the evaluator form view (`evaluations/forms.py`) and template (`templates/evaluations/evaluation_form.html`) to ensure the language matches what evaluators actually see. Re-run `seed_email_templates` after updating. Audit all other email templates for similar inaccuracies while you're in there.

---

**Issue #10 - Profile page broken (includes /profile/ 404 fix)**
Effort: 2-4 hrs | Type: Bug fix

The base template navbar links to `/profile/` but no view or URL route exists -- every logged-in user hits a 404 when clicking "Profile". Create a profile view at `/profile/` with URL route in `core/urls.py`. The profile page should display and allow editing of: name, phone, ORCID, organization. Email should be displayed but **not editable** (it is tied to the user's login identity). User roles and their associated area/specialization should be **displayed but not editable** (roles are managed by coordinators via admin). These user fields pre-fill application forms, so accuracy matters for applicants.

---

**Issue #5 - Call did not auto close**
Effort: 2-3 hrs | Type: Bug fix

No automatic call closure mechanism currently exists. Implement a two-layer fix:

*Primary mechanism:* Add a new Celery Beat periodic task (`check-call-deadlines`) that runs daily alongside the existing scheduled tasks. It should check for any call with `status='open'` whose `submission_end` date is in the past, and update the status to `closed`. Register this task in `redib/celery.py` beat schedule.

*Fallback mechanism:* Add a defensive check in call list and detail views: any call with a submission deadline in the past should display as closed regardless of the database status field. Optionally update the DB status when this is detected (self-heal). This ensures correct behavior even if Celery Beat is not running.

---

**Issue #3 - Specialization options mismatch**
Effort: 2-3 hrs | Type: Bug fix + migration

The specialization/area options are inconsistent across the codebase and incomplete relative to the reference application form:

- `UserRole.AREAS` in `core/models.py`: `preclinical`, `clinical`, `radiotracers` (3 options + blank)
- `Application.SPECIALIZATION_AREAS` in `applications/models.py`: `clinical`, `preclinical`, `radiotracers` (with label "Radiotracers and Biomarkers")

Per the reference application form, both should offer 4 options: **Clinic, Preclinic, Radiotracers, Radiochemistry Lab**.

Changes required:
1. Update `Application.SPECIALIZATION_AREAS` to include all 4 options with consistent labels.
2. Update `UserRole.AREAS` to match the same 4 options (plus the existing blank option for roles where area is not applicable -- area is mandatory only for evaluators).
3. Create a data migration to handle the label changes and new option.
4. Each user/applicant selects one specialization: "which of the following ReDIB areas of specialization your proposal (or you) best fits into."
5. The profile page (Issue #10) should display the user's role area.
6. Verify the automatic evaluator assignment logic still works correctly. The assignment rules are: (a) no evaluators from the same organization as the applicant, (b) balance application load across evaluators as evenly as possible, (c) after that, prefer evaluators whose specialization matches the application's specialization area.

---

**Issue #12 - Evaluated At field empty/unclear**
Effort: 1 hr | Type: Bug fix

Templates reference `evaluated_at` and `application.evaluated_at` but neither field exists on the models. The `Evaluation` model has a `completed_at` field that tracks when an evaluator submits their scores. Update templates to use the correct field path (`eval.completed_at`). Specifically check:
- `templates/applications/detail.html` (references `application.evaluated_at`)
- `templates/applications/node_resolution/review.html` (references `eval.evaluated_at`)

Rename the column label to "Completed On" for clarity.

---

**Issue #4 - Back button wrong destination**
Effort: 30 min | Type: Bug fix

The back buttons use `{% url %}` tags (valid named routes) but the destination is wrong contextually -- e.g., "Back to My Applications" appears even when navigating from the coordinator view. Remove back buttons from page footers entirely. Users have the browser back button and the sidebar for navigation. Back buttons that go to the wrong place are worse than no back button. Avoid `javascript:history.back()` as it is unreliable with form submissions.

---

**Issue #11 - Overdue evaluations: 1-week grace period**
Effort: 4-6 hrs | Type: Feature

Implement a 1-week grace period after the evaluation deadline:

*Evaluator experience:*
- Dashboard shows overdue evaluations with a warning banner
- For 1 week past deadline: evaluators can still submit, but see a "past due" warning
- After 1 week past deadline: submission form is locked, evaluator sees message that the deadline has passed and they should contact the coordinator

*Automatic emails (3 triggers):*
1. **To evaluators** - Sent when evaluation deadline passes and they have pending evaluations. "Your evaluation is overdue, please submit within one week."
2. **To ReDIB coordinator** - Sent when evaluation deadline passes AND there are pending evaluations. Content: which evaluations are still pending, which evaluators are assigned, that the evaluators have been notified, that evaluators have 1 week before lockout, and that the coordinator can extend the deadline by editing the call dates directly from Dashboard > Manage Call.
3. **To ReDIB coordinator** - Sent 1 week after evaluation deadline IF evaluations are still pending. Same info as email #2 but stating that evaluators are now locked out and the coordinator must extend the call evaluation deadline to unlock them.

*Coordinator action:* The coordinator already has the ability to edit call dates. When they extend the evaluation deadline, evaluators are automatically unlocked (the 1-week grace window resets relative to the new deadline). No new UI needed for the coordinator.

*Implementation:* These should be Celery Beat periodic tasks that check daily. Integrate with the existing `check-evaluation-reminders` task in the beat schedule -- ensure the new overdue/lockout logic does not duplicate the existing reminder logic. Check if evaluation reminder templates already exist in the DB and extend them, or create new templates for the coordinator notification.

---

**Issue #6 - Multi-node feasibility status visibility**
Effort: 3-5 hrs | Type: Feature

On the application detail view (coordinator perspective), add a "Feasibility Review Status" section showing a table:

| Node | Equipment | Status | Reviewer | Date | Comments |
|------|-----------|--------|----------|------|----------|
| CIC biomaGUNE | MRI 7T | Feasible | node_cic | 2025-01-15 | "Confirmed available" |
| TRIMA@CNIC | MRI 3T | Pending | - | - | - |

This tells the coordinator at a glance which nodes have responded and which haven't, so they know who to follow up with.

---

**Repo housekeeping (do anytime)**
Effort: 10 min | Type: Cleanup

```bash
# Remove Word temp file
git rm "~\$DIB-APP-application-form-coa-redib.docx"
echo "~\$*" >> .gitignore

# Move loose script
mkdir -p scripts
git mv add_feasibility_test_apps.py scripts/
# Or delete if no longer needed:
# git rm add_feasibility_test_apps.py

git commit -m "Repo cleanup: remove temp file, organize scripts"
```

---

### Tier 2: Should Fix Before Launch

**Issue #13 - Multi-node resolution results visibility**
Effort: 3-5 hrs | Type: Feature

Show per-node resolution status on the call management view for multi-node applications. Similar to #6 but for the resolution phase. Lower priority since multi-node applications are very uncommon. Can be a simple table showing which node coordinators have submitted resolution decisions.

---

**Issue #7 - Return application for revision**
Effort: 4-6 hrs | Type: Feature (workflow change)

Add a "Request Revision" action available to node coordinators and the ReDIB coordinator. When triggered:
- Application status changes to a new `revision_requested` state
- Coordinator provides a note explaining what needs to change
- Applicant receives email with the note
- Applicant can edit and resubmit
- Application returns to `submitted` status and re-enters feasibility review

Defer this until after Tier 1 is complete and stable. This changes the user workflow and needs careful testing.

---

### Tier 3: Post-Launch

**Issue #8 - Entity/agency dropdown lists**
Effort: 6-10 hrs | Type: Feature

Add autocomplete/typeahead for entity and funding agency fields that suggests from previously submitted values. Allows free text entry for new values. Self-populating over time, no maintenance. Not a launch blocker since free text works fine.

---

## Summary

| Priority | Issues | Total Effort |
|----------|--------|--------------|
| Tier 1 | #9, #10, #5, #3, #12, #4, #11, #6, housekeeping | ~3-4 days |
| Tier 2 | #13, #7 | ~1-2 days |
| Tier 3 | #8 | ~1 day |

Start with #9 (quickest win, 30 minutes), then work down the Tier 1 list in order. Each issue can be a separate branch and commit. Test after each fix before moving on.
