# Action items for you / portal updates

## 1. Registration and profile completion

### 1.1 Require full applicant profile completion before access

* Change registration so users cannot proceed with only email and email confirmation.
* Users registering through this path should receive only the **applicant** role.
* Require full profile completion before applicant access is granted.
* Applicants should still be able to edit their profile later, but the initial profile must be complete before portal use if initial registration was done through the portal. This is not valid for manual entries in the DB or entires done by CLI commands.

### 1.2 Add and enforce applicant profile fields

The applicant profile should include, at minimum:

* full name
* phone number
* contact ID
* organization
* title
* ORCID ID (optional)
* data consent for applications (optional)


### 1.3 Add data consent to the profile and support automatic future consent

* Move the current data consent concept into the applicant profile.
* Use the current consent text from the application step currently at `applications/.../step5/` as the starting point.
* Modify the profile text so it is clear that:

  * this is **data consent for submitting applications**, and
  * by checking it, the user is consenting to **automatic data consent for all future applications**.
* Add a binary field in the user data model, for example:

  * `auto_data_consent = true/false`
* Store this value in the database for all users.

### 1.4 Preserve application as the authoritative submission record

* Keep the current design principle that the **Application** model is the authoritative submission record.
* The application must continue to store:

  * a submission-time snapshot of applicant identity/contact fields
  * `data_consent` alongside the other submission declarations
* If a user has automatic data consent in profile:

  * the application should still store `data_consent = true` at submission time
  * but the user should not need to see or check the consent box in the application UX

### 1.5 Add application logic for profile-based data consent

At the application step currently corresponding to the data consent page:

* Check whether the user has `auto_data_consent = true`
* If **no**:

  * show the checkbox and consent text as currently done
* If **yes**:

  * do not show the checkbox and full consent text
  * instead display a short note such as:

    * **“Data consent provided.”**
* Regardless of UX path, the submitted application must still record `data_consent` in the application record

### 1.6 Redesign organization as its own data model

Organization should no longer be treated as a simple text field or static list. It should become its own database model with fields such as:

* organization name
* VAT
* address
* country
* type

For **type**, use a dropdown with:

* Company / Empresa
* University / Universidad
* Other / Otro

### 1.7 Add organization dropdown with self-extending organization creation flow

* In the profile, organization selection should be via dropdown.
* The last option in the dropdown should always be **Other**.
* If the user selects **Other**, they should be prompted to create a new organization.
* This can be implemented through:

  * redirect to a dedicated page/view,
  * inline page update,
  * or popup/modal
* Exact UX can be chosen during implementation, but the logic should remain the same.

When a new organization is entered:

* create a new organization record in the database
* associate it with the user who entered it
* add it to the internal organization list
* ensure it becomes available in the dropdown for future users

This way, the internal organization list grows naturally over time.


---

## 2. Application auto-fill and profile consistency

### 2.1 Auto-fill applicant profile fields into the application

Ensure that application forms auto-fill from the applicant profile, including:

* full name
* phone number
* organization
* title
* ORCID ID
* other profile-derived fields as appropriate

### 2.2 Fix ORCID auto-fill

* ORCID currently does not auto-fill correctly.
* Update application population logic so ORCID is included.
* Keep ORCID optional.

### 2.3 Show profile-derived fields in the application, but do not let users edit them there

On the first page of the application, users should be able to see profile-derived fields such as:

* name
* phone number
* organization
* title
* ORCID

However:

* these should not be freely editable in the application itself
* if the user wants to change them, they should be redirected to edit their profile
* after updating profile, they should return and restart or refresh the application so the new profile values propagate cleanly

The key goal is to keep profile data authoritative and always up to date.

---

## 3. PDF signature workflow

### 3.1 Remove required PDF signature logic from the application process

Jesús has now approved removal of the PDF signature requirement.

Therefore:

* remove the mandatory workflow requiring applicants to:

  * download a PDF
  * digitally sign it
  * re-upload it

### 3.2 Remove required PDF signature logic from the evaluation process

* Remove the same requirement from the evaluation workflow as well, if still present.
* It may already have been removed there, so first confirm the current implementation and delete any remaining related logic.

### 3.3 Do not retain PDFs as official records

* PDFs are no longer required as part of official workflow tracking.
* There is no need to keep PDFs in the system as submission records.
* The database should remain the system of record.

### 3.4 Keep optional applicant PDF download for personal records

* At the end of the application process, allow the applicant to download a PDF copy for personal record-keeping.
* Reuse the existing PDF generation logic and tools already in the system.
* This download should be optional only.

---

## 4. Funding section logic

All items below apply to the funding step currently corresponding to application step 2.

### 4.1 Keep the funding step, but make the funding details conditional

Do **not** add a standalone yes/no funding question on a separate page.

Instead:

* keep the funding step in the wizard
* use the existing checkbox (currently at the bottom but move to the top of the funding page) as the gating logic:

**Has competitive funding**
*Check if this project has competitive funding from external agencies*

Behavior:

* if checked = yes
* if unchecked = no (default)

If unchecked:

* all other funding-related fields on that page should be grayed out or disabled
* in the database, those funding-related fields can be stored as `NA` / null-equivalent values as appropriate

### 4.2 Move “Project Name” to Step 1

Because the funding section is now conditional, the general project name should no longer live in the funding step.

Update as follows:

* move **Project Name** from the current funding page to:

  * **Step 1: Basic Information**
* place it just above **Project Summary**

### 4.3 Rename the funding-step project field

On the funding step:

* change **Project Name** to **Funded Project Name**

This keeps the general project identity separate from the name of the funded project, where applicable.

### 4.4 Add internal funding-agency list with extensible dropdown

Funding agency should use an internal database-backed list.

Behavior:

* show known funding agencies in dropdown
* always include **Other** as the final option
* if user selects **Other**, require them to enter a new agency name in a text field
* when a new agency is entered:

  * create it in the internal funding-agency list
  * make it available for future users

This should work the same way conceptually as the organization list but currently funding agencies have no additional fields of their own.

### 4.5 Replace “Project type” with “Origin of funds”

* Change the label **Project type *** to **Origin of funds ***

Use this dropdown list:

* National (Spain)
* Regional (Autonomous Communities)
* European Union (EU)
* International (non-EU)
* Internal / Institutional
* Private
* Other

For this dropdown:

* if **Other** is selected, no extra explanatory text is required

---

## 5. Animal ethics logic

### 5.1 Remove ethics approval as a hard requirement for animal studies at application time

* Animal studies should not require ethics approval to already exist at the time of submission.
* Applicants should still be able to indicate that the project involves animals.

### 5.2 Preserve ethics-status capture in the application

* Capture whether:

  * animals are involved, and
  * ethics approval is already in place or not
* If not yet approved, that should still be reflected in the application record.
* This allows the system and reviewers to recognize that ethics support or follow-up may still be needed.

---

## 6. Clinical long-term request

* This section is no longer relevant.

---

## 7. Feasibility review workflow

### 7.1 Add a third feasibility-review outcome: reopen for edits

Currently node coordinators can approve or reject. Add a third option:

* approve
* reject
* reopen for edits

### 7.2 Preserve comment rules, with required comments for rejection and reopen

* Keep comments required for **reject**
* Keep comments optional for **approve**
* Make comments required for **reopen for edits**

### 7.3 Add explicit reviewer guidance on the feasibility-review page

* Add a note on the review page making it very clear that if the application is reopened for edits, the node coordinator must provide enough information for the applicant to know what needs to be changed.

### 7.4 Return reopened applications to editable draft state

When the coordinator selects **reopen for edits**:

* the application should return to draft/editable state
* the applicant should be able to log back in and continue editing
* prior entered content should be preserved
* the coordinator’s comments should be visible to the applicant

### 7.5 Update automated emails for reopened applications

* Extend the email notification logic beyond approval/rejection to include **edits requested**
* Update the email template so it:

  * clearly states that edits are requested
  * includes the coordinator comments or directs the user to them
  * includes a link back to the application

The applicant should be able to reopen the application, view comments, revise, and resubmit.

---

## 8. Email and wizard navigation / cancellation improvements

### 8.1 Fix step-2 back navigation

* When filling out an application and moving to step two, the bottom button currently allows the user to **Go back to my applications**
* This should instead allow them to go back to **step one**
* All wizard steps should behave consistently by allowing navigation to the previous step

### 8.2 Add cancel button throughout the application wizard

* There should always be a **Cancel** button at the bottom of the wizard

### 8.3 Add confirmation popup for cancel

If the user clicks cancel:

* show a popup confirming whether they are sure
* make it clear that all application data will be deleted if they continue

### 8.4 Delete cancelled application records completely

If the user confirms cancel:

* fully delete the application record from the database
* do not leave partial drafts or orphaned objects behind

---

## 9. Application guidance text

* Do **not** update the scientific project guidance text yet.
* Leave the current text as-is for now.
* Note that example text is still pending from Ángel.
* This remains an open future update, but not for current implementation.

---

## 10. External inputs / confirmations

### 10.1 Items now resolved

* Jesús approval for removing PDF signature logic: **resolved**
* Country as separate profile issue: **resolved by organization model design**
* ORCID optionality: **confirmed**

### 10.2 Still pending from Ángel

Still waiting on:

* ministry-required profile information list, if there are any remaining specifics beyond what is already defined
* any curated organization seed list, if he still plans to provide one
* funding agency list, if he provides one to initialize the internal DB
* example scientific-field guidance text

---

# ReDIB Open Call Portal — updated GitHub-style issues list

Below is a revised issue backlog that includes the newer implementation strategies, not just problem statements.

---

## Epic 1 — Registration, applicant profile, and consent

### Issue 1 — Require full applicant profile completion before portal access

**Labels:** `enhancement`, `auth`, `profile`, `priority:high`

**Description**
New users should no longer gain functional access with only email registration. They should receive the applicant role only and must complete a full applicant profile before using the portal.

**Implementation strategy**

* Gate applicant access behind profile completeness
* Assign only `applicant` role at registration
* Treat profile as authoritative source for reusable applicant metadata

**Acceptance criteria**

* Email-only registration is insufficient for applicant portal use
* Newly registered normal users receive only `applicant`
* Required profile fields must be complete before application creation is allowed

---

### Issue 2 — Add required applicant profile fields including title and optional ORCID

**Labels:** `enhancement`, `profile`, `data-model`, `priority:high`

**Description**
Expand the applicant profile to include the full required set of reusable applicant metadata.

**Implementation strategy**

* Add/confirm fields for:

  * full name
  * phone number
  * contact ID
  * title
  * organization
  * ORCID
* Keep ORCID optional

**Acceptance criteria**

* Title appears after Organization in profile flow
* ORCID exists and is optional
* Required non-optional fields are validated before profile completion

---

### Issue 3 — Add profile-level application data consent with automatic future consent

**Labels:** `enhancement`, `profile`, `compliance`, `priority:high`

**Description**
Move the data consent concept into profile so users can authorize automatic consent for future applications.

**Implementation strategy**

* Add binary user field such as `auto_data_consent`
* Reuse current application consent text as basis
* Rewrite text to clarify:

  * consent applies to application submission
  * checking it enables automatic consent for future applications

**Acceptance criteria**

* Profile contains a consent checkbox with updated text
* Consent value is stored in DB for the user
* Consent field is available for application logic checks

---

### Issue 4 — Preserve application record as authoritative submission record while honoring auto-consent

**Labels:** `enhancement`, `application`, `data-model`, `priority:high`

**Description**
Even if the user has profile-level auto-consent, the application must still store submission-time declarations.

**Implementation strategy**

* Keep submission-time snapshot fields in Application model
* Continue storing `data_consent` in each application
* If user has auto-consent, silently write `data_consent=true` without forcing UX checkbox display

**Acceptance criteria**

* Application stores `data_consent` regardless of whether checkbox is shown
* Submission record remains complete and auditable
* Profile consent does not replace application declarations; it only streamlines UX

---

### Issue 5 — Update application consent step to conditionally hide/show checkbox based on profile consent

**Labels:** `enhancement`, `application`, `conditional-logic`, `priority:high`

**Description**
The current consent step should branch based on whether the user already has automatic consent on profile.

**Implementation strategy**

* If `auto_data_consent=false`, show current checkbox and full text
* If `auto_data_consent=true`, suppress checkbox and show short note such as “Data consent provided.”
* Still record application-level consent in either case

**Acceptance criteria**

* Users without auto-consent see current consent UX
* Users with auto-consent do not need to re-check a box
* Application submission stores valid `data_consent` in both paths

---

### Issue 6 — Redesign organization as a first-class database model

**Labels:** `enhancement`, `profile`, `data-model`, `priority:high`

**Description**
Organization is no longer just a text field. It should become a structured DB object.

**Implementation strategy**
Create organization model with fields such as:

* name
* VAT
* address
* country
* type

Organization type dropdown:

* Company / Empresa
* University / Universidad
* Other / Otro

**Acceptance criteria**

* Organization is stored as structured object
* Organization record supports country and type
* User profile references an organization object rather than only raw text

---

### Issue 7 — Add self-extending organization dropdown with “Other” creation flow

**Labels:** `enhancement`, `profile`, `ux`, `priority:high`

**Description**
Users should select from known organizations but still be able to add new ones.

**Implementation strategy**

* Use dropdown populated from organization table
* Always show `Other` as final option
* If `Other` selected, prompt user to create new organization via modal, inline form, or separate page
* Save created organization and associate it with submitting user
* Reuse new organization in future dropdowns

**Acceptance criteria**

* Dropdown is DB-backed and dynamically updated
* New organization can be created when missing
* New organization is saved and reusable for future users

---

### Issue 8 — Derive country from selected organization rather than separate profile entry

**Labels:** `enhancement`, `profile`, `data-model`, `priority:medium`

**Description**
Country no longer needs to be a separate profile field if organization includes country.

**Implementation strategy**

* Use organization.country as authoritative source
* Require country during new organization creation flow

**Acceptance criteria**

* User country does not need separate manual profile entry
* Country is available through organization association
* New organizations cannot be created without country

---

## Epic 2 — Profile-to-application synchronization

### Issue 9 — Auto-fill profile-derived fields into application including title and ORCID

**Labels:** `enhancement`, `application`, `profile`, `priority:high`

**Description**
Applicant profile fields should flow automatically into the application.

**Implementation strategy**
Auto-fill:

* full name
* phone number
* organization
* title
* ORCID
* any other profile-derived identity/contact fields

**Acceptance criteria**

* All relevant profile data appears in new application
* ORCID now auto-fills correctly
* Title appears as expected

---

### Issue 10 — Make profile-derived application fields visible but not editable in the application

**Labels:** `enhancement`, `application`, `ux`, `priority:high`

**Description**
Profile-derived fields should be shown in the application but must be changed through profile only.

**Implementation strategy**

* Render these fields as read-only or non-editable display fields
* Add clear guidance/link to edit profile
* After profile update, require refresh/restart of application flow so data rehydrates cleanly

**Acceptance criteria**

* Users can see the fields in the application
* Users cannot directly edit them there
* Editing path redirects to profile

---

## Epic 3 — Remove required PDF signature workflow

### Issue 11 — Remove signed-PDF workflow from application submission

**Labels:** `enhancement`, `application`, `workflow`, `priority:high`

**Description**
Remove the legacy requirement to download, sign, and re-upload a PDF during application submission.

**Implementation strategy**

* Remove signed-PDF upload logic
* Use DB record as authoritative submission
* Delete any obsolete validation or UI dependencies tied to signed PDFs

**Acceptance criteria**

* Submission works with no signed PDF step
* Application remains valid and complete in DB
* No signed PDF artifacts are required or stored

---

### Issue 12 — Remove signed-PDF workflow from evaluation submission if still present

**Labels:** `enhancement`, `evaluation`, `workflow`, `priority:medium`

**Description**
Remove any remaining PDF signature requirements from the evaluation process.

**Implementation strategy**

* Confirm whether evaluation still includes PDF-signature logic
* Remove if present
* Keep evaluation record database-native

**Acceptance criteria**

* No evaluation step requires PDF signature or upload
* Evaluation decisions remain fully captured in DB

---

### Issue 13 — Add optional applicant PDF export for personal records only

**Labels:** `enhancement`, `application`, `pdf`, `priority:medium`

**Description**
Applicants should still be able to download a PDF copy for themselves.

**Implementation strategy**

* Reuse existing PDF generation tooling
* Expose optional PDF download at the end of application flow
* Do not store PDFs as required records

**Acceptance criteria**

* Applicant can download PDF copy
* Download is optional only
* PDF matches submission content

---

## Epic 4 — Funding step redesign

### Issue 14 — Move general Project Name to Step 1 and rename funding-step field to Funded Project Name

**Labels:** `enhancement`, `application`, `priority:high`

**Description**
Because funding is conditional, the general project name should be separated from funding metadata.

**Implementation strategy**

* Move `Project Name` to Step 1 above `Project Summary`
* Rename funding-step `Project Name` to `Funded Project Name`

**Acceptance criteria**

* Step 1 contains general project name
* Funding step contains `Funded Project Name`
* Form structure clearly distinguishes general project identity from funding-specific project identity

---

### Issue 15 — Make funding details conditional using the existing “Has competitive funding” checkbox

**Labels:** `enhancement`, `application`, `conditional-logic`, `priority:high`

**Description**
Do not add a separate earlier yes/no page. Use the existing checkbox at the top of the funding step to control all downstream fields.

**Implementation strategy**

* Keep funding step in place
* Use existing checkbox as yes/no gate
* If unchecked, disable/gray-out all other funding fields
* Store downstream fields as `NA` or null when not applicable

**Acceptance criteria**

* Users without competitive funding can pass through step without completing downstream funding fields
* Users with funding must complete those fields
* Disabled state is visually clear

---

### Issue 16 — Add extensible DB-backed funding agency dropdown with “Other” option

**Labels:** `enhancement`, `application`, `data-model`, `priority:medium`

**Description**
Funding agencies should be managed similarly to organizations.

**Implementation strategy**

* Maintain funding-agency table in DB
* Show all agencies in dropdown
* Always include `Other` at bottom
* If `Other`, require free-text new agency entry
* Save new agency to DB for future reuse

**Acceptance criteria**

* Dropdown is populated from internal agency list
* New agency can be added when missing
* Newly added agency becomes available for future selections

---

### Issue 17 — Replace “Project type” with “Origin of funds” and update dropdown values

**Labels:** `enhancement`, `application`, `content`, `priority:medium`

**Description**
The funding terminology should be clearer and standardized.

**Implementation strategy**
Rename field to `Origin of funds` and use:

* National (Spain)
* Regional (Autonomous Communities)
* European Union (EU)
* International (non-EU)
* Internal / Institutional
* Private
* Other

No extra text required if `Other` is selected.

**Acceptance criteria**

* Field label updated
* Dropdown values updated exactly as specified
* No extra explanatory field required for `Other`

---

## Epic 5 — Animal ethics logic

### Issue 18 — Remove ethics approval as a hard submission prerequisite for animal studies

**Labels:** `enhancement`, `application`, `ethics`, `priority:high`

**Description**
Animal studies should not be blocked just because approval is not yet in place at application time.

**Implementation strategy**

* Keep animal-use declaration
* Keep ethics-status declaration
* Remove validation rule that blocks submission if ethics approval is absent

**Acceptance criteria**

* Animal-use application can be submitted without existing approval
* Application still captures ethics status clearly

---

## Epic 6 — Feasibility review and edit-request workflow

### Issue 19 — Add “reopen for edits” as a third coordinator decision state

**Labels:** `enhancement`, `workflow`, `feasibility-review`, `priority:high`

**Description**
Node coordinators need a middle path between accept and reject.

**Implementation strategy**

* Add `reopen for edits` status
* Preserve current approve/reject logic
* Update status model, UI, and notifications accordingly

**Acceptance criteria**

* Coordinator can choose approve, reject, or reopen for edits
* New status is stored and handled correctly throughout workflow

---

### Issue 20 — Require comments for reject and reopen-for-edits outcomes

**Labels:** `enhancement`, `workflow`, `feasibility-review`, `priority:high`

**Description**
Applicants need actionable feedback whenever an application is not approved as-is.

**Implementation strategy**

* Keep comments optional for approve
* Require comments for reject
* Require comments for reopen for edits
* Add visible reviewer note reminding coordinators to explain what must be changed

**Acceptance criteria**

* Reject cannot be submitted without comment
* Reopen cannot be submitted without comment
* Guidance note is visible on page

---

### Issue 21 — Return reopened applications to editable draft state with preserved content and comments

**Labels:** `enhancement`, `workflow`, `application`, `priority:high`

**Description**
Applications reopened for edits should behave like editable drafts, not new submissions.

**Implementation strategy**

* Preserve prior application content
* Change status to editable draft-like state
* Make coordinator comments visible to applicant
* Allow resubmission after edits

**Acceptance criteria**

* Applicant can edit reopened application
* Prior content is preserved
* Coordinator feedback is visible
* Applicant can resubmit successfully

---

### Issue 22 — Add “edits requested” email notification with return link

**Labels:** `enhancement`, `email`, `workflow`, `priority:high`

**Description**
Email logic must support the new reopen-for-edits workflow.

**Implementation strategy**

* Add new notification template/state for edits requested
* Include link back to application
* Clearly distinguish from rejection
* Surface or reference coordinator comments

**Acceptance criteria**

* Applicant receives clear edits-requested email
* Email includes direct return path to application
* Email wording is distinct from rejection

---

## Epic 7 — Wizard UX and destructive actions

### Issue 23 — Fix Step 2 back button so it returns to Step 1 instead of My Applications

**Labels:** `bug`, `wizard`, `ux`, `priority:medium`

**Description**
Wizard navigation is inconsistent at step two.

**Implementation strategy**

* Change bottom button behavior at step two to return to step one
* Keep wizard navigation consistent across all steps

**Acceptance criteria**

* From step two, back returns to step one
* Wizard behaves consistently across steps

---

### Issue 24 — Add persistent Cancel button throughout application wizard with destructive-action confirmation

**Labels:** `enhancement`, `wizard`, `ux`, `priority:medium`

**Description**
Users should be able to abandon an in-progress application intentionally and clearly.

**Implementation strategy**

* Add Cancel button on every wizard page
* Open confirmation popup explaining all application data will be deleted
* If confirmed, fully remove application record from DB

**Acceptance criteria**

* Cancel button exists on every wizard step
* Confirmation popup appears before deletion
* Confirmed cancel removes application record completely

---

## Epic 8 — Deferred content updates

### Issue 25 — Defer scientific-field example text update until Ángel provides approved examples

**Labels:** `deferred`, `content`, `application`, `priority:low`

**Description**
Guidance-text improvements are postponed for now.

**Implementation strategy**

* Leave current text unchanged
* Track dependency on Ángel’s example text

**Acceptance criteria**

* No text changes applied yet
* Issue remains open pending provided examples

---

## Epic 9 — External dependencies / initialization data

### Issue 26 — Gather and seed external reference lists needed for DB-backed dropdowns

**Labels:** `external-dependency`, `data`, `priority:medium`

**Description**
Several dropdowns can begin with seed data but must also support growth over time.

**Implementation strategy**
Collect or initialize:

* organization seed list
* funding agency seed list
* remaining ministry-required profile fields if any
* future example guidance text

**Acceptance criteria**

* Seed data can be imported or entered
* System remains functional even if lists start small
* New entries can expand the DB over time

---


