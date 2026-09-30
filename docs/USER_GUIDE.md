<!--
This file is the single source of truth for the end-user guide. It is
rendered live in the portal at /help/user-guide/ (core.views.user_guide),
so keep it self-contained: only `#anchor` links and absolute URLs -- no
images, no relative links to other docs.
-->

# ReDIB COA Portal - User Guide

**Version 1.4** | **Last Updated: September 2026**

---

## Table of Contents

1. [Introduction](#introduction)
2. [What is the ReDIB COA Portal?](#what-is-the-redib-coa-portal)
3. [Understanding the COA Workflow](#understanding-the-coa-workflow)
4. [Getting Started](#getting-started-phase-0)
5. [User Roles and Permissions](#user-roles-and-permissions)
6. [Email Notifications](#email-notifications)
7. [Using the Portal](#using-the-portal)
    - [Your Profile](#your-profile)
    - [For Applicants](#for-applicants-researchers)
    - [For Node Coordinators](#for-node-coordinators)
    - [For Evaluators](#for-evaluators)
    - [For ReDIB Coordinators](#for-redib-coordinators)
    - [For Administrators](#for-administrators)
8. [Getting Help](#getting-help)

---

## Introduction

This guide explains how to use the ReDIB COA Portal to apply for, review,
evaluate and manage Competitive Open Access (COA) to the imaging equipment of
the ReDIB network. It is written for everyone who uses the portal —
applicants, node coordinators, evaluators, the ReDIB coordinator and
administrators — and assumes no technical background.

Read the workflow overview first, then go to the section for your role under
[Using the Portal](#using-the-portal).

---

## What is the ReDIB COA Portal?

The **ReDIB COA Portal** runs the whole Competitive Open Access process on the
web, from publishing a call to following up on the publications that result.
It replaces the email-based process ReDIB used before.

### What does the portal do?

For researchers, the portal is where you:

- **Apply** for time on specialised imaging equipment (MRI, PET, CT and more)
- **Follow** your application from submission to decision
- **Accept** the access you are granted and get put in touch with the node
- **Report** the publications that come out of the work

For ReDIB staff, it is where they:

- **Publish** calls for applications
- **Review** the technical feasibility of each request
- **Evaluate** the scientific merit of each application
- **Decide**, node by node, which applications get equipment time, and how many hours
- **Report** on each call, including the published resolution table

### The ReDIB Network

The portal serves the **4 ReDIB nodes** in Spain:

1. **CIC biomaGUNE** (San Sebastián)
2. **BioImaC** (Madrid)
3. **Imaging La Fe** (Valencia)
4. **TRIMA@CNIC** (Madrid)

Each node offers its own imaging equipment and expertise in preclinical,
clinical and radiochemistry research.

---

## Understanding the COA Workflow

A call moves through the phases below, from setting up the portal (phase 0)
to reporting (phase 10). Knowing them tells you where an application is and
who has to act next.

### Phase 0: Foundation and Setup

**Who:** Administrators

- User accounts, roles, nodes, equipment and email templates are set up in the
  admin panel.

### Phase 1: Call Management

**Who:** ReDIB coordinator

- The ReDIB coordinator creates each call as a **Draft**, with its dates and
  the equipment on offer.
- **Announce** lists the call publicly under *Upcoming Calls* before it opens;
  it then opens by itself on its submission start date. **Publish** opens a
  call straight away.
- The portal does not send a mass email when a call is announced or opens. The
  ReDIB coordinator announces the call through ReDIB's own channels and links
  people to its public page.
- While a call is announced or open, anyone can ask a node about equipment on
  it with **Request a Consult**, without an account.
- The call closes by itself when its submission deadline passes.

A call's status goes **Draft → Announced → Open → Closed → Resolved**.

### Phase 2: Application Submission

**Who:** Applicants (researchers)

- Applicants fill in a 5-step application form for an open call: basic
  information, funding and project, equipment and hours, scientific content,
  and declarations.
- A draft can be saved at any point and finished later. Applicants who still
  hold a draft are reminded 7 days and 2 days before the submission deadline.
- On submission the application gets a code built from the call code, for
  example `REDIB-2602-APP-001`.

### Phase 3: Feasibility Review

**Who:** Node coordinators

- Each node whose equipment is requested checks that the work is
  **technically feasible** there. This is not a judgement of scientific merit.
- **Every** node must approve for the application to go on to evaluation. One
  rejection ends it. A request for edits sends it back to the applicant as a
  draft; when it is resubmitted, every node reviews it again.

### Phase 4: Evaluator Assignment

**Who:** ReDIB coordinator

- The ReDIB coordinator assigns evaluators — normally two per application —
  automatically or one by one. Automatic assignment never picks an evaluator
  from the applicant's own organization, prefers evaluators whose
  specialization matches the application, and spreads the work across the
  pool.
- Evaluators are emailed as soon as they are assigned.

### Phase 5: Evaluation Process

**Who:** Evaluators

- Evaluation is **blind**: evaluators do not see who applied.
- Each application is scored on **6 criteria**, 0–2 points each (maximum 12):
    - **Category 1: Scientific and Technical Relevance** — quality and
      originality; methodology, design and work plan; expected
      scientific–technical contributions
    - **Category 2: Timeliness and Impact** — advancement of knowledge;
      social, economic and/or industrial impact; exploitation, translation
      and/or dissemination
- Each evaluator also gives an **Access Decision**: **Approved** or
  **Denied**. A Denied decision must be explained in a comment.
- The application's final score is the average of its evaluators' totals.
  When the last evaluation is in, the application becomes **Evaluated**.
- Evaluations can still be submitted for 7 days after the evaluation
  deadline. After that the form locks.

### Phase 6: Release and Resolution

**Who:** ReDIB coordinator (release), then node coordinators (decisions)

- Evaluated applications wait until the ReDIB coordinator **releases** the
  call's results to the nodes, all at once. Each node then weighs the whole set
  of applications against its capacity instead of deciding them one at a time
  as the scores trickle in.
- Each node coordinator decides for the equipment at their node: **Accept**,
  **Waitlist** or **Reject**. They also set the approved hours for each piece
  of equipment and, when accepting, the date the project's access ends.
- The node decisions combine into the application's outcome:
    - **all nodes accept** → **Accepted**
    - **any node rejects** → **Rejected**
    - **no rejection, but at least one waitlist** → **Pending (Waiting List)**
- **Competitive funding rule:** an application with competitive funding cannot
  be rejected at this stage unless at least one evaluator recommended
  **Denied**. Rejection at feasibility, and an evaluator's Denied, are not
  affected by funding.
- When every node has decided, the applicant is emailed the outcome.

### Phase 7: Acceptance and Handoff

**Who:** Applicants, then node coordinators

- Accepted and waitlisted applicants have **10 days** to accept or decline.
  Reminders go out 7, 3 and 1 days before the deadline.
- When an applicant accepts an accepted application, one **hand-off email**
  goes to the applicant with the node coordinator(s) copied, so they can
  arrange the work by replying to all.
- Accepting a **waitlist** offer keeps the application in the queue. If a slot
  opens, a node coordinator clicks **Promote to Accepted** and the applicant
  gets the acceptance and hand-off emails. If no slot opens, the node closes it
  out as **Not Reached This Call**.
- **Nothing expires by itself.** If the 10 days pass without an answer, the
  applicant can no longer respond in the portal, and the node coordinator is
  reminded (with the ReDIB coordinator copied) until they either **Expire** the
  application or **Accept on Behalf** of the applicant. An expired application
  can be reinstated if that was a mistake.

### Phase 8: Execution and Completion

**Who:** Node coordinators and applicants

- Node coordinators and applicants arrange the equipment time directly, by
  email or phone, outside the portal.
- Each accepted project has an **execution period end**: the call's date
  unless the node coordinator sets a different one.
- The applicant and the node coordinators are reminded to close the project
  out, starting 60 days after the hand-off and then every 30 days, plus once
  after the execution period ends.
- When the work is done, the applicant or a node coordinator marks the
  application complete and records the actual hours used.

### Phase 9: Publication Follow-up

**Who:** Applicants

- About six months after the hand-off, applicants who have not yet reported a
  publication get a follow-up email.
- Publications must acknowledge ReDIB. The publication form shows the required
  text:
  > *"This work acknowledges the use of ReDIB ICTS, supported by the Ministry of Science, Innovation and Universities (MICIU) at [NODE NAME]."*

### Phase 10: Close-out and Reporting

**Who:** ReDIB coordinator

- Once every application on the call has an outcome, the ReDIB coordinator
  marks the call **Resolved**.
- Reports include a statistics page, an Excel workbook for the current call,
  and a per-call resolution table in English and Spanish, ready to publish.

### Application statuses

These are the status labels you will see on applications, and what each one
means:

| Status | What it means |
|--------|---------------|
| Draft | Being written, or sent back by a node for edits. Not submitted. |
| Under Feasibility Review | Submitted; the nodes are checking technical feasibility. |
| Rejected - Not Feasible | A node found the work technically infeasible. Final. |
| Pending Evaluation | Passed feasibility; waiting for evaluators to be assigned. |
| Under Evaluation | Evaluators are scoring it. |
| Evaluated | All scores are in; waiting for the node decisions. |
| Accepted — Awaiting Applicant | Access granted; the applicant has not answered yet. |
| Accepted | The applicant has accepted. Shown as **Active** once the hand-off email has gone out. |
| Waitlist — Awaiting Applicant | On the waiting list; the applicant has not answered yet. |
| Waitlist — Accepted by Applicant | The applicant accepted the waitlist offer and is waiting for a slot. |
| Rejected | Not granted at the decision stage. Final. |
| Declined | The applicant declined. Final. |
| Expired | Nobody answered within the 10 days and a coordinator expired it. Can be reinstated. |
| Not Reached This Call | Waitlisted, but no slot opened. Final. |
| Completed | The work is done and the actual hours are recorded. |

---

## Getting Started (Phase 0)

### Accessing the Portal

The portal is at `https://portal.redib.net`.

**Pages you can read without logging in:**

- `/calls/` — the open calls and the upcoming (announced) ones, with their
  dates and the equipment on offer. Each call has its own page, with a
  **Request a Consult** button while it is announced or open.
- `/newsletters/` — ReDIB newsletters, reachable from the **Newsletters**
  button on the calls page. Each one opens as a full newsletter inside the
  portal; links inside a newsletter open in a new tab.
- `/help/user-guide/` — this guide, also linked from the **Need help?** menu
  at the top of every page.

### Creating an account and logging in

- **Register:** click **Register** at the top right (or go to
  `/accounts/signup/`), enter your email address twice and a password twice,
  then click the confirmation link that is emailed to you. Confirming gives your
  account the **Applicant** role, so you can start an application straight
  away. The registration page needs JavaScript switched on in your browser.
- **Log in:** click **Login** and sign in with your email address and password.
  **Forgot password?** on the login page emails you a link to set a new one.
- **First login:** the portal takes you to your **Profile** until the required
  fields are filled in — see [Your Profile](#your-profile).

Every other role — node coordinator, evaluator, ReDIB coordinator,
administrator — is assigned by an administrator.

---

## User Roles and Permissions

What you see and can do depends on your role. You can hold several roles —
for example Applicant and Evaluator — and then see everything each of them
gives you. Your roles are listed under **My Roles** on your profile page.

| Role | Dashboard panels | Menu entries (left side) |
|------|------------------|--------------------------|
| Applicant | My Applications | My Applications, My Active Access, Publications, Open Calls |
| Node Coordinator | Pending Feasibility Reviews, Pending Resolution Decisions | Feasibility Reviews, Resolution Queue, Scheduling, Access Tracking |
| Evaluator | My Pending Evaluations | My Evaluations |
| ReDIB Coordinator | Active Calls, Quick Stats, Recent Applications | Call Management, Assign Evaluators, Resolution, Reports |
| Administrator | — | Admin Panel |

Everyone also has **Dashboard** at the top of the menu and **Public Calls**
under *General*.

### The roles

- **Applicant** — a researcher applying for equipment time. You see only your
  own applications.
- **Node Coordinator** — staff at a ReDIB node. You review the technical
  feasibility of requests for your node's equipment, decide which evaluated
  applications your node accepts, waitlists or rejects, and look after
  accepted projects until they are complete. You see only applications that
  request equipment at your node; one that requests equipment at several nodes
  appears in each of those nodes' lists.
- **Evaluator** — an expert reviewer who scores the applications assigned to
  you. The review is blind: you never see the applicant's name, organization,
  contact details, project title, project code or funding agency.
- **ReDIB Coordinator** — runs the calls: creates and announces them, assigns
  evaluators, releases each call's results to the nodes, follows the process
  to the end, and produces the reports. Only ReDIB coordinators can create
  calls. The feasibility and resolution decisions belong to the node
  coordinators, and the scores to the evaluators.
- **Administrator** — maintains accounts, roles, nodes, equipment and email
  templates in the admin panel. See
  [For Administrators](#for-administrators).

### How roles are assigned

Registering through `/accounts/signup/` gives you the Applicant role. Every
other role is assigned by an administrator.

### What happens if you have no roles assigned

An account with no active role — one created by ReDIB whose roles are not set
yet, for example — sees a *"You don't have any roles assigned yet"* notice on
the dashboard and can browse the public calls, but cannot apply, review or
evaluate. Contact the ReDIB administrator to have the right role added.

---

## Email Notifications

The portal emails you whenever something needs your attention. Every subject
starts with **ReDIB COA**. Each role section under
[Using the Portal](#using-the-portal) ends with a list of the emails that role
receives.

- **Reminders are grouped.** An evaluator with several pending evaluations gets
  one email listing all of them, and node coordinators get one digest covering
  their node's projects rather than one email per project.
- **No call announcement emails.** The portal does not email users when a call
  is announced or opens. ReDIB announces each call itself and links to the
  call's public page.
- **Turning emails off.** There is no email setting on your profile. If you
  want to stop a kind of email — reminders, for example — ask the ReDIB
  administrator, who can change your notification preferences in the admin
  panel.

---

## Using the Portal

This section walks through what each role sees and does, screen by screen.
After you log in, your dashboard and the menu down the left side are tailored
to your roles; with several roles, the panels combine.

Every page has:

- A **navigation bar** at the top with **Need help?** — **User guide** (this
  page) and **Contact us**, which opens an email to ReDIB support — plus
  **Dashboard**, **Calls**, and your name, which opens **Profile** and
  **Logout**.
- A **footer** with the same support email address.

If your profile is missing a required field, every page sends you to your
**Profile** until you complete it. This guide stays readable in the meantime.

---

### Your Profile

Every user has a profile page. Completing it is the first thing to do after
you log in for the first time.

#### Navigating to your profile

Click your **name** in the top-right corner of any page and choose
**Profile**, or go to `portal.redib.net/profile/`.

#### Required fields

Until these are filled in, the portal keeps bringing you back to this page:

- **First Name** and **Last Name**
- **Phone** — the number node coordinators will use to reach you
- **Title / Position** — for example Principal Investigator, Researcher,
  Technician
- **Organization** — pick your institution from the list. If it is not there,
  choose **Other (create new)** and fill in the new organization's details.

Click **Save Changes**. You go to your dashboard and the rest of the portal
opens up.

#### Other profile fields

- **ORCID** — pre-fills into your applications.
- **Evaluator Specialization Areas** (evaluators only) — Preclinical, Clinical
  and/or Radiochemistry. These decide which applications you are preferably
  matched with, so keep them up to date.
- **Automatic data consent for applications** — tick it to give the
  data-processing consent once, for all your future applications, instead of
  on every application.

The page also lists **My Roles**, the roles on your account.

#### Changing your password

1. On your profile page, click **Change Password** (in the *Password* box).
2. Enter your **Current Password**, then your **New Password** and
   **Confirm New Password**.
3. Click **Change Password**.

You can also go directly to `portal.redib.net/accounts/password/change/`.

---

### For Applicants (researchers)

You apply for time on imaging equipment, follow the application through review
and decision, accept the access if you are granted it, and report any
publications that result.

#### Your dashboard

**My Applications** lists every application you have created with its status
badge (see [Application statuses](#application-statuses)) and the next thing
you can do:

- **View** — open the application.
- **Continue** — carry on with a draft.
- **Accept/Decline** or **Accept/Decline Waitlist** — respond to a decision.

The left-hand menu (under **Applicant**) gives you:

- **My Applications** — the full list. Drafts on a call that has closed show
  **Call closed** instead of **Continue**, and completed applications have an
  **Add Publication** button.
- **My Active Access** — the applications you have accepted, with their
  equipment, hours and node contacts.
- **Publications** — your reported publications, and the form to add one.
- **Open Calls** — the public list of calls.

#### Asking a node about equipment before you apply

The public `/calls/` page lists open calls and, under *Upcoming Calls*, calls
that have been announced but are not open yet. Each call's page lists its
equipment, with a **Consult** button next to each instrument and a
**Request a consult** button above the list.

Use it when you want to know whether an instrument suits your study, what it
can do, or whether time is likely to be available:

1. Click **Consult** next to the instrument you are interested in — it
   arrives already ticked. You can tick more, at as many nodes as you like.
2. Fill in your name and email (pre-filled from your profile if you are logged
   in) and, optionally, a phone number, your institution and what you would
   like to discuss.
3. Click **Send request**. The coordinator(s) of every node whose equipment
   you ticked get your enquiry by email and will contact you directly. You get
   a copy for your records.

This is informal contact only. It does not start an application or commit you
to applying, and you do not need an account. To apply, log in and use the
application form once the call is open.

#### Submitting an application

1. Find the call on the **Calls** page and click **Apply Now** (or
   **Apply for Access** on the call's own page). You can hold one draft per
   call — if you already have one, you are taken back to it.
2. Work through the form. **Next** checks the current step and saves it.
   From step 2 on, **Save Draft** saves whatever you have typed so far, even a
   half-finished step, and returns you to your dashboard. Come back any time
   with **Continue**.
    - **Step 1 — Basic Information:** Name and Surname, ORCID, Entity, Email
      and Phone come from your profile and cannot be changed here — use
      **Edit your profile** on the step to correct them. Node coordinators
      reach you through this email and phone. The only thing you type on this
      step is the Project Title.
    - **Step 2 — Funding & Project Information:** a one-line Project Summary,
      the Subject Area, and whether the project has competitive funding. If it
      does, give the Project Code and Funding Agency (pick from the list, or
      choose *Other (enter new)*) and its Origin of Funds.
    - **Step 3 — Equipment Request:** the Service Modality, the Specialization
      Area (used to match evaluators), and the equipment from this call with
      the hours you need on each. You can request equipment at more than one
      node in the same application.
    - **General Information and Instructions** — after step 3 you see a
      read-only page with the instructions from the original ReDIB application
      form. Read it and click **I have read this — Continue to Scientific
      Content**. The same text is available later from the info button on
      step 5.
    - **Step 4 — Scientific Content:** six free-text sections, one for each
      criterion the evaluators score.
    - **Step 5 — Declarations & Consent:** use of animals or human subjects,
      ethics approval, insurance, informed consent, and data-processing
      consent. Some boxes only appear when earlier answers call for them. One
      of them is **"I have confirmed technical feasibility with the ReDIB
      node"** — see the next section.
3. **Preview Application** shows the whole application as the reviewers will
   see it. Click **Submit Application** and confirm. The status becomes
   **Under Feasibility Review** and the node coordinators are emailed. Once
   submitted, you cannot change it unless a node sends it back for edits.

The preview also offers **Download PDF for your records (optional)**,
**Back to Edit** and **Save and Continue Later**. **Cancel Application**
(on the preview and on steps 2–5) permanently deletes the draft.

#### Talking to the node before you submit

ReDIB expects you to discuss your proposal with the node(s) whose equipment you
are requesting *before* you submit — feasibility is a technical conversation,
and it goes much faster if it has already happened. Clicking
**Next: Preview & Submit** on step 5 triggers a short check:

- If you **left the feasibility box unticked**, the portal asks whether you
  would like to request a consult. **Yes, request a consult** emails every
  node coordinator at each node with equipment on your draft (or ReDIB, for a
  node with no coordinator); they will contact you. Your draft is saved and you return to **My Applications**.
  **No, continue without a consult** takes you to the preview.
- If you **ticked the box**, the portal asks you to confirm you really did
  speak to the node. **Yes, I confirmed feasibility** continues to the
  preview. **No, not yet** unticks the box and offers the consult request.

Requesting a consult does not submit your application and does not stop you
submitting later — request one, wait for the node's reply, then come back and
submit. If you have not picked any equipment yet, the request is recorded but
no email goes out; choose your equipment on step 3 and request again. The
request is shown on your application, so the coordinators can see the
conversation is under way.

#### If the call closes while you are drafting

Once the submission deadline passes, every page of the form shows a banner
saying when the call closed: you can still read and edit your draft, but it can
no longer be submitted. In **My Applications** the draft shows **Call closed**
instead of **Continue**.

The exception is an application a node sent back for edits. You can still
resubmit it after the deadline, so it keeps **Continue**, and the banner says
you can resubmit. This lasts until the call is **Resolved**.

#### What happens after you submit

Each step emails you, and your dashboard shows the current status:

- **Feasibility.** Each node with equipment on your application approves,
  rejects, or asks for edits. If a node asks for edits, the application
  returns to **Draft** with the node's comments at the top of the application
  page; click **Edit Application**, make the changes and submit again — every
  node then reviews it afresh. If a node rejects it, the application ends as
  **Rejected - Not Feasible**. When every node has approved, it goes to
  evaluation.
- **Evaluation.** Evaluators score your application. You do not see the scores
  during this phase.
- **Decision.** Once ReDIB releases the call's results to the nodes, each node
  decides for its own equipment, and the combination becomes your outcome (see
  [Phase 6](#phase-6-release-and-resolution)). You are emailed when every node
  has decided.

#### Responding to a decision

If your application is **Accepted** or placed on the **waiting list**, you have
**10 days** to respond. Click **Accept/Decline** (or
**Accept/Decline Waitlist**) on your dashboard. The page shows the equipment
and hours granted and the days you have left.

- **Accept Access** — you are put in touch with the node(s): one hand-off email
  goes to you with the node coordinator(s) copied. Reply to all to arrange
  your equipment time.
- **Accept Waitlist Offer** — you stay on the waiting list. If a slot opens, a
  node coordinator promotes your application and you receive the acceptance and
  hand-off emails straight away, with no second click. If no slot opens this
  call, you are told once that it was **Not Reached This Call**.
- **Decline Access** — you give up the offer; you can add a reason. This
  cannot be undone.

You are reminded 7, 3 and 1 days before your deadline. After the deadline the
page no longer accepts a response — your node coordinator will be in touch
about what happens next.

#### After you have been accepted

- **My Active Access** lists the applications you have accepted. Open
  **View Equipment & Hours** to see the approved hours and each node's
  contact. Scheduling happens **outside the portal**, by email or phone with the
  node coordinators.
- The application page shows the **Execution period ends** date: the call's
  date, or a date your node set for your project (marked *set by node*). Plan
  your work to finish by then.
- From about 60 days after the hand-off you get occasional reminders to
  report your final hours. When the work is done, click **Mark Complete**,
  enter the **Actual Hours Used** for every piece of equipment, and click
  **Mark Application Complete**. The application becomes **Completed**; this
  cannot be undone.

#### Publications

About six months after the hand-off, if you have not reported a publication
yet, you get a follow-up email. Publications can only be reported against a
completed application, so if your project is not marked complete yet, the email
asks you to do that first. To report one, open **Publications** and click
**Submit Publication** (or **Add Publication** next to a completed application
in **My Applications**). Enter the application it came from, the title,
authors, journal or conference, DOI and publication date, and confirm that
ReDIB is acknowledged; you can paste the acknowledgment text too. Publications
are how ReDIB demonstrates its research impact, so this matters even years
after the work.

#### Emails you will receive

- **Application [code] Received** — when you submit.
- **Edits Requested for [code]** — a node needs changes; the application is
  back in draft.
- **Feasibility Review Complete for [code]** — every node has decided on
  feasibility; says whether your application goes on to evaluation.
- **Application [code] Accepted**, **Application [code] Placed on Waitlist**,
  or **Application [code] Resolution** (not granted) — the decision.
- **Reminder to accept access for [code]** or **Reminder to respond to your
  waiting-list offer for [code]** — 7, 3 and 1 days before your response
  deadline.
- **Access Approved - Application [code] Ready for Scheduling** — the hand-off,
  with the node coordinator(s) copied.
- **Update on your waitlisted application [code]** — no slot opened this call.
- **Application [code] has been closed** — only if a node coordinator expires
  your application after the deadline and chooses to tell you by email.
- **Log your final hours for [code]** — reminders to complete your project.
- **Publication Follow-up for Application [code]** — about six months after
  the hand-off.
- **Your Application for [call] is Still a Draft** — 7 and 2 days before the
  submission deadline, while your draft is unsubmitted.
- **We received your consult request for [call]** — your copy of a consult
  request sent from a call page.

---

### For Node Coordinators

You make the node's two decisions on every application that requests your
equipment: **feasibility** (can we do this?) and **resolution** (do we accept
it on our equipment, and for how many hours?). Afterwards you arrange the work
with the applicant and see the project through to completion.

#### Your dashboard

- **Pending Feasibility Reviews** — submitted applications waiting for your
  node's feasibility decision, each with a **Review** button.
- **Pending Resolution Decisions** — evaluated applications waiting for your
  node's decision, each with a **Resolve** button.

The left-hand menu (under **Node Coordinator**) gives you:

- **Feasibility Reviews** — the full feasibility queue.
- **Resolution Queue** — applications awaiting your decision, and the ones you
  have already decided.
- **Scheduling** — applications the applicant has accepted, with contact
  details and hours.
- **Access Tracking** — every application at your node, and the buttons for
  waitlist promotion, stalled acceptances and completion.

Most emails about your node's applications go to all of its active node
coordinators, and any one of you can act on them.

#### Consult requests

- **From the public call pages.** While a call is announced or open, anyone
  can ask about specific equipment. The coordinators of each node concerned get
  the enquiry by email — contact details, the instruments asked about and the
  message — with a link to the list of requests for that call. Reply to the
  person directly; nothing else happens automatically.
- **From an applicant's draft.** An applicant who has not yet confirmed
  feasibility with you can ask for a consult from step 5 of their form; you get
  an email naming the equipment. The request also shows on their application.

#### Feasibility review

1. Click **Review** on a queue entry. You see the application — applicant,
   project, the equipment requested **at your node** (other nodes' equipment
   is theirs to judge), the scientific content and the declarations. The
   application page's **Download PDF** gives you the same content as a
   document, for applications at your node in any status, drafts included.
2. Choose a **Feasibility Decision**:
    - **Approve** — technically feasible at your node.
    - **Request Edits** — the applicant must revise it first. The comment is
      required: say clearly what to change.
    - **Reject** — not feasible at your node. The comment is required.
3. Click **Submit Feasibility Decision**.

Every node must approve before the application goes to evaluation. A
rejection from any node ends it. A request for edits returns it to the
applicant straight away; when it comes back, every node reviews it again.
You can request edits after the submission deadline too: the applicant can
still resubmit, until the call is **Resolved**.

#### Resolution

Applications reach your **Resolution Queue** only after the ReDIB coordinator
has **released** the call's results to the nodes — all of the call's
evaluated applications at once, so you can weigh them together against your
capacity. You get an **All Evaluations Complete** email for each one. (If you
follow an older link before the release, the portal tells you the call has not
been released yet.)

1. Click **Review** in the Resolution Queue (or **Resolve** on the dashboard).
   You see the application, the final score, each evaluator's score and
   recommendation, and the equipment requested at your node.
2. Under **Approved Hours per Equipment**, enter the hours you grant for each
   item — up to the hours requested. They default to the request.
3. **Execution period ends** is prefilled with the call's date. Change it if
   this project's access will run to a different date. It only counts if you
   accept; a waitlisted project gets its date when it is promoted.
4. Choose a **Resolution Decision**: **Accept**, **Waitlist** or **Reject**.
   If the application has **competitive funding** and no evaluator recommended
   Denied, **Reject is not offered** — a banner at the top explains why. If an
   evaluator did recommend Denied, the banner says rejection is available.
5. Add an optional comment and click **Submit Resolution**. Other nodes'
   decisions, if any, are shown at the bottom of the page.

When every node involved has decided, the application's status is set
(Accepted, Pending (Waiting List) or Rejected — see
[Phase 6](#phase-6-release-and-resolution)) and the applicant is emailed.

#### Access tracking

**Access Tracking** lists every application at your node with its status. The
**Node-accepted, awaiting applicant** button above the list filters it to
accepted or waitlisted applications whose applicant has not responded yet.
The buttons offered depend on where each application is:

- **Promote to Accepted** (waitlisted, and the applicant has accepted the
  waitlist offer) — use it when a slot frees up. The confirmation page asks
  you to confirm the approved hours for each item (at least one must be above
  zero) and the **Execution period ends** date, then
  **Confirm & Promote to Accepted**. The application becomes Accepted, your
  node's decision is recorded as an acceptance, and the applicant gets the
  acceptance and hand-off emails.
- **Not Reached This Call** (same situation) — no slot will open. Give a
  reason (it is shared with the applicant), then **Confirm & Close Out**. The
  applicant is emailed once. This is final.
- **Expire** and **Accept on Behalf** — see *Stalled acceptances* below.
- **Mark Complete + Log Hours** (accepted and the applicant has accepted) —
  once the work is done, enter the **Actual Hours Used** for every piece of
  equipment and click **Mark Application Complete**. This is final.

Accepted, unfinished projects also show the date their execution period ends.

#### Stalled acceptances

Nothing expires by itself. When an applicant's 10-day window passes with no
answer, their Accept/Decline page closes and you get a **Reminder #N** email
the next day and every 3 days after, with the ReDIB coordinator copied, until
you act. On **Access Tracking** the application then shows two buttons:

- **Expire** — ends the application. A reason is required and stored on the
  application. Tick *Also email the applicant* only if you want the system to
  tell them; leave it unticked if you have already spoken to them. Expiring an
  accepted application frees its hours, so you can promote a waitlisted one in
  its place; a waitlisted one holds no hours, so nothing is freed.
- **Accept on Behalf** — not recommended. Use it only if you know the
  applicant is ready to go ahead (say how you know in the required reason). On
  an accepted application the hand-off email goes out straight away; on a
  waitlisted one it records that they accept the waitlist offer.

The ReDIB coordinator is emailed whenever either button is used.

**Reinstating.** If an application was expired by mistake, or the applicant
gets in touch afterwards, open the application page and click **Reinstate**.
With a required reason, it returns to Accepted or Pending (Waiting List) —
whatever the node decided — and the applicant gets a fresh 10-day window and
an email saying their link works again.

#### Changing a project's end date

On the page of an accepted, unfinished application at your node, the
**Execution period ends** line has a date field and an **Update** button. The
date cannot be earlier than the call's execution start. If several nodes share
the application, the last change wins. Choosing the call's own date makes the
project follow the call's date again.

#### Emails you will receive

- **New Application for Equipment at [node]** — a submission needs your
  feasibility decision.
- **Feasibility review pending for [code]** — a review has been waiting more
  than 5 days; repeats until someone at your node acts.
- **Pre-submission consult requested for [node]** — an applicant asked to talk
  before submitting.
- **Equipment consult requested for [node] ([call])** — an enquiry from a
  public call page.
- **All Evaluations Complete for [code]** — the call has been released; this
  application is ready for your decision.
- **Access Approved - Application [code] Ready for Scheduling** — the hand-off
  (you are copied); the applicant accepted.
- **Capacity freed on [code]** — an accepted applicant declined, or an
  accepted application was expired; you may be able to promote a waitlisted
  one.
- **Reminder #N - [code] needs your decision** — an applicant missed their
  response deadline.
- **Waitlisted applications need a decision** — a digest of waitlisted
  applications whose applicants have accepted: first 30 days after they
  accepted, then every 30 days, and once after the execution period ends.
- **Applications Awaiting Completion** — a digest of your node's projects that
  are not marked complete yet, at most once a week.

---

### For Evaluators

You score the applications assigned to you. The portal hides who applied, so
your scoring is independent.

#### Your dashboard

**My Pending Evaluations** lists your assigned applications with the call, the
date you were assigned and the evaluation deadline, each with an **Evaluate**
button.

The left-hand menu (under **Evaluator**) has **My Evaluations**: counts of
pending, overdue and completed evaluations, then the lists themselves.
Completed evaluations open read-only with **View**.

#### Submitting an evaluation

1. Click **Evaluate**. The **Download Blind PDF** button at the top gives you
   a printable copy if you would rather read offline.
2. **Read the application.** You see the application code, project summary,
   origin of funds, subject area, specialization, the equipment requested, and
   the six scientific-content sections. You do **not** see the applicant's
   name, ORCID, organization or contact details, the project title (shown as
   *withheld for blind review*), the project code or the funding agency.
3. **Score the six criteria**, 0, 1 or 2 points each. The form describes what
   each score means for each criterion.
    - Category 1 — Scientific and Technical Relevance: quality and
      originality; methodology, design and work plan; expected
      scientific–technical contributions.
    - Category 2 — Timeliness and Impact: advancement of knowledge; social,
      economic and/or industrial impact; exploitation, translation and/or
      dissemination.
4. Choose an **Access Decision**: **Approved** or **Denied**. A Denied
   decision **requires a comment** — an evaluator's Denied is what allows the
   node to reject an application that has competitive funding (see
   [Phase 6](#phase-6-release-and-resolution)).
5. Click **Submit Evaluation**. The page shows your total. Submitted
   evaluations cannot be changed.

You can still submit for **7 days after the evaluation deadline**; the page
warns that you are overdue. After that the form locks and can no longer be
submitted, and the ReDIB coordinator is told which evaluations are missing.

#### How you get assigned

The ReDIB coordinator assigns evaluators after applications pass feasibility,
usually by running automatic assignment across a call. It prefers evaluators
whose specialization areas (Preclinical, Clinical, Radiochemistry) match the
application, but a match is a preference, not a requirement: if no matching
evaluator is available you may be assigned outside your areas so that no
application is left short. It never assigns you an application from your own
organization, and it caps how many applications any one evaluator takes in a
call. Keep your areas up to date on your **Profile**.

If your account or your evaluator role is deactivated, you are left out of
assignment altogether.

#### Emails you will receive

- **Evaluation Assignment for [code]** — one for each new assignment.
- **Evaluation Reminder ([n] Pending)** — one email listing all your pending
  evaluations, 7, 3 and 1 days before the evaluation deadline.
- **[n] Evaluations Overdue** — on the deadline day and then every 2 days,
  until the form locks 7 days after the deadline.

---

### For ReDIB Coordinators

You run the calls and watch the process end to end. The feasibility and
resolution decisions belong to the node coordinators and the scores to the
evaluators, but you can see everything, and several steps wait on you:
announcing the call, assigning evaluators, releasing results, and closing the
call out.

#### Your dashboard

- **Active Calls** — announced, open and closed calls, with **Manage Calls**
  and **Create New Call**.
- **Quick Stats** — applications waiting for a node decision, recent
  applications, and a link to the reports.
- **Recent Applications** — the latest submissions across all calls.

The left-hand menu (under **Coordinator**) gives you **Call Management**,
**Assign Evaluators**, **Resolution** and **Reports**.

#### Creating a call

1. In **Call Management**, click **Create New Call** and fill in:
    - **Call Code** (for example `REDIB-2602`), **Title**, **Description**
      (shown to applicants) and, optionally, **Guidelines**.
    - **Submission Period** (Start Date, End Date), **Evaluation Deadline**,
      **Execution Start** and **Execution End**. All dates are whole days:
      start dates open at **00:00** on the day you pick, and end dates and
      deadlines run to **23:59**, so applicants get the whole of the closing
      day. The evaluation deadline must fall after the submission end.
    - **Equipment Allocations** — every active piece of equipment at every
      node is included by default. Tick **Remove** to leave one out. A call
      needs at least one before it can be announced or published.
2. Click **Save Call**. The call is a **Draft**, visible only to coordinators.

A call's status only ever changes through the buttons on its page (or by the
calendar), never on the form. A draft call with no applications can be
removed with **Delete Call**; once a call has been announced or published it
cannot be deleted.

After you save changes to an existing call, the portal warns you if the dates
you saved contradict its status — for example, a call marked Open whose start
date is now in the future is **not** accepting applications or listed publicly
until then, and moving a closed call's deadline does not reopen it.

#### Announce vs Publish

The call page (open it from **Call Management**) shows the buttons for its
current status.

- **Announce** — for a call whose submission period starts in the future. The
  call becomes **Announced** and appears on `/calls/` under *Upcoming Calls*,
  with its own page (dates, equipment list and **Request a Consult**). No one
  can apply yet. It **opens by itself** on its start date — checked daily just
  after midnight and whenever someone loads the public calls pages.
- **Publish** — opens the call for submissions **now**. It is refused while the
  start date is still in the future; announce the call instead. On an
  announced call the same action is **Open Now**, which also needs the start
  date to have arrived — edit the start date first if you want to open early.

**No email goes to users** when a call is announced or opens, and the
confirmations say so. Announce the call yourself — through ReDIB's newsletter,
mailing lists and website — and link people to its public page (the
**Public View** button on the call page opens it).

While a call is announced or open, anyone can send a consult request about its
equipment. The requests go to the coordinators of the nodes involved and are
listed under **Consult Requests** on the call page (**Open list** shows them
full-page). If a node has no active coordinator, the request comes to you
instead. They are informal enquiries: nothing else is created.

#### Closing submissions

An open call closes by itself once its submission deadline passes.
**Close Submissions** on the call page closes it early. A closed call cannot
be reopened from the portal.

#### Assigning evaluators

Open **Assign Evaluators**, then **View Details** or **Manage** on the call.
Applications that have passed feasibility show as **Pending Assignment**.

- **Auto-Assign Evaluators** assigns **Evaluators per Application** (2 by
  default) to every application pending assignment, across the whole call at
  once:
    - it **never** assigns evaluators from the applicant's own organization,
      nor the same evaluator twice to one application;
    - it **caps** how many applications each evaluator takes in the call,
      counting those they already hold, so the work is spread out;
    - it **prefers** evaluators whose specialization areas match the
      application, but uses any eligible evaluator rather than leave an
      application short;
    - it **skips** deactivated accounts and evaluator roles.
- Afterwards, the page warns you if some applications could not be filled, or
  were filled with evaluators outside their specialization area. In each
  application's list of evaluators, **✓** marks an area match and
  **no area match** marks a mismatch — swap them by hand if a better evaluator
  is available.
- **Assign** on an application adds one evaluator by hand (evaluators whose
  areas match are marked ✓ in the list). **Remove** takes off an evaluator who
  has not submitted yet. If everyone left has submitted, the application moves
  on to **Evaluated**.

**Evaluators are emailed the moment they are assigned** — there is no review
step before the emails go out. You can assign while the call is still open (the
page reminds you of this); applications submitted later will need a second
run.

#### Watching a call

A call's page is the status wall for the call: every submitted application with
its current status, plus drafts a node has **sent back for edits**, so you can
see who is waiting on the applicant (drafts never submitted stay hidden). A
**Consult** badge marks applications whose applicant asked for a pre-submission
consult. **View** opens an application; as a coordinator you see its
feasibility status per node and, once scored, the evaluation summary with each
evaluator's scores, recommendation and comments. **Download PDF** works on any
application, drafts included.

The **Reminders** panel sends the same reminder emails the daily schedule
sends, right now, for this call only:

- **Remind Evaluators with Unsubmitted Scores**
- **Remind Open Feasibility Reviews**

Each shows first who will be emailed and who will be skipped because they were
already reminded today. Tick **Send anyway, including people reminded today**
to include them, then **Send Reminders**.

#### Releasing results to the nodes

When a call's evaluations are complete, the evaluated applications wait for
you: node coordinators are not told and cannot decide until you release them.
The **Resolution** page lists calls that are waiting on you.

1. On the call page, click **Release to Nodes**.
2. The confirmation page lists every evaluated application with its final
   score, each evaluator's score and recommendation, and the **spread**
   between evaluators. A warning mark flags a spread of 5 points or more —
   whether such a pair needs a closer look is ReDIB's call, not the portal's.
3. Click **Confirm & Release to Nodes**. Every node coordinator involved is
   emailed for each application at once. This cannot be undone.

Applications that finish evaluation after the release go to their nodes
straight away.

#### Watching resolution

The **Resolution** page lists released calls that still have applications
waiting for a node decision, with counts of accepted, waitlisted and rejected
applications. **View** opens a call's list of those applications, ranked by
score. Both pages are read-only: the node coordinators make the decisions, and
each applicant is emailed as soon as their last node decides.

The portal chases evaluators, applicants and nodes for you (see the email
list below). From an application's page you can also **Reinstate** it or
change its **Execution period ends** date, just as a node coordinator can.

#### Closing out a call

When every application on a closed call has its outcome, click
**Mark Call Resolved** on the call page, then **Confirm & Mark Resolved**. The
call moves to **Resolved** and its resolution is locked. **No emails are
sent.** It is refused while any application is still **Evaluated**.

#### Reports

**Reports** opens the **Statistics & Reports** page:

- Totals for calls, applications, reported publications and pending
  evaluations.
- **Current Call** — the most recent open or closed call, with its
  applications by status, average score, acceptance rate, and
  **Download Excel Report**: a workbook with *Summary*, *Applications* and
  *Equipment Summary* sheets.
- **Resolution Tables** — every call, each with **View Resolution Table**.
- Publication statistics, including the share that acknowledge ReDIB, and
  recent applications. **View Report History** lists the reports generated.

**The resolution table** is the per-call results table ReDIB publishes. It
shows two tables, English then Spanish, one row per submitted application:

| English | Spanish |
|---------|---------|
| Application | Solicitud |
| Organization | Organización |
| Node | Nodo |
| Resolution: Accepted / Wait List / Rejected | Resolución: Aceptada / Lista de espera / Rechazada |

The resolution is each node's own decision — an application promoted from the
waiting list reads *Accepted*. An application involving several nodes lists
each node on its own line within the row. Copy the tables straight into a
document, or use **Download CSV (English)** and **Download CSV (Español)**.
Warnings above the tables tell you if the call has not been released yet (the
table is then provisional), which applications have no node decision recorded
(for example, those rejected at feasibility), and which applicants have no
organization on their profile.

#### Emails you will receive

- **Overdue Evaluations for Call [call]** — the morning after the evaluation
  deadline, if any evaluations are missing, naming them and their evaluators.
- **Evaluators Locked Out - Call [call]** — the morning after the 7-day grace
  period ends, if evaluations are still missing.
- **Reminder #N - [code] needs your decision** — you are copied on the node
  coordinators' reminders about stalled acceptances. The node coordinator must
  act; you are copied so you know.
- **[code] was expired / force-accepted / reinstated by [name]** — a record
  each time a node coordinator (or another coordinator) uses Expire, Accept on
  Behalf or Reinstate, with their reason.
- When a node has **no active node coordinator**, the portal sends you what
  would have gone to them: new-application alerts, public and pre-submission
  consult requests, and stalled-acceptance reminders. Ask an administrator to give the node a
  coordinator — until then nobody can do that node's feasibility review.

---

### For Administrators

Administrators look after the data behind the portal in the admin panel at
`/admin/`, reached from **Admin Panel** in the left-hand menu.

- **Accounts and roles.** Create users and assign roles under *User Roles*. A
  role can be switched off without deleting it. Deactivating an evaluator's
  account or evaluator role takes them out of automatic assignment.
- **Nodes and equipment.** Equipment marked inactive is not offered on new
  calls.
- **Email templates.** Switching a template off (*Is active*) stops that email
  being sent, and stays off when the portal is updated. Changes to a
  template's subject or wording, however, are replaced by the standard text
  whenever the portal is updated — ask the developers to change the wording
  permanently.
- **Email preferences.** Notification preferences for any user can be changed
  here.

The Administrator role adds the **Admin Panel** link. To use call management
and the coordinator dashboard, the account also needs the ReDIB Coordinator
role, and the admin panel itself only opens for accounts with staff access. A *superuser* passes every role check in the portal and has
full access to the admin panel; keep such accounts to a minimum.

---

## Getting Help

### Common questions

**Q: I can't see Call Management. Why?**
A: Only ReDIB coordinators create and manage calls. Contact the administrator
if you need this access.

**Q: Can I change my role?**
A: No — roles are assigned by administrators. Ask the ReDIB administrator if you
need a different or additional role.

**Q: Why can't I see the applicant's name when I evaluate?**
A: Evaluation is blind to keep it objective. The applicant's identity is hidden
on purpose.

**Q: I'm a node coordinator. Why don't I see every application?**
A: You see only applications that request equipment at your node.

**Q: An evaluated application isn't in my Resolution Queue. Why?**
A: The ReDIB coordinator has not released that call's results to the nodes yet.
You will get an email for each application once they do.

**Q: I missed my 10-day deadline to accept. What now?**
A: The portal no longer accepts a response, but nothing has been cancelled
automatically. Contact the node coordinator — the node decides what happens
next.

**Q: How do I stop receiving reminder emails?**
A: There is no setting on your profile. Ask the ReDIB administrator to turn
reminders off for your account.

### Technical support

For problems with the portal, questions about using it, or role requests, use
**Contact us** in the **Need help?** menu, or email the address at the bottom
of this page.

---

**Document Version History**

- v1.0 (January 2026): Initial user guide created for ReDIB COA Portal
- v1.2 (April 2026): "Using the Portal" rewritten as four role-based
  walkthroughs (Applicants, Node Coordinators, Evaluators, ReDIB
  Coordinators) covering each role end-to-end as the user sees it.
- v1.3 (August 2026): caught up with the portal changes since April — the
  wizard's General Information interstitial and the pre-submission
  feasibility consult, Save Draft behaviour, applicant role on self-signup,
  the public newsletters section, draft PDFs and bounced drafts for
  reviewers, load-balanced evaluator auto-assign, and call open/close times.
  This guide is now served as a portal page at `/help/user-guide/` rather
  than downloaded as a PDF.
- v1.4 (2026-09-28): checked against the portal as deployed for the October
  2026 call. New: releasing a call's results to the nodes; the execution
  period end set per project; stalled acceptances (nothing expires by itself —
  Expire, Accept on Behalf, Reinstate); waitlist promotion and *Not Reached
  This Call*; Mark Call Resolved; the bilingual resolution table; grouped
  reminder emails and the on-demand Reminders panel; the closed-call banner;
  no call announcement emails; an application status table and per-role email
  lists. Corrected the dashboards, buttons, email timings, publication
  follow-up and notification preferences, and removed the duplicated role and
  dashboard sections.

---
