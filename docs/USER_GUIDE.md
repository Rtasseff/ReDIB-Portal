# ReDIB COA Portal - User Guide

**Version 1.2** | **Last Updated: April 2026**

---

## Table of Contents

1. [Introduction](#introduction)
2. [What is the ReDIB COA Portal?](#what-is-the-redib-coa-portal)
3. [Understanding the COA Workflow](#understanding-the-coa-workflow)
4. [Getting Started](#getting-started-phase-0)
5. [User Roles and Permissions](#user-roles-and-permissions)
6. [Using the Portal](#using-the-portal)
   - [Your Profile](#your-profile)
   - [For Applicants](#for-applicants-researchers)
   - [For Node Coordinators](#for-node-coordinators)
   - [For Evaluators](#for-evaluators)
   - [For ReDIB Coordinators](#for-redib-coordinators)
7. [Getting Help](#getting-help)

---

## Introduction

Welcome to the ReDIB COA Portal User Guide. This guide will help you navigate and use the portal to manage Competitive Open Access (COA) applications for accessing advanced biomedical imaging equipment across the ReDIB network.

This guide is written for all users of the portal, regardless of technical background. It focuses on using the web interface to accomplish your tasks.

---

## What is the ReDIB COA Portal?

The **ReDIB COA Portal** is a web-based system that automates the complete lifecycle of Competitive Open Access (COA) applications for biomedical imaging equipment. The portal replaces the previous manual, email-based process with an integrated platform that streamlines everything from call publication to research outcome tracking.

### What does the portal do?

The portal helps researchers:
- **Apply** for access to specialized imaging equipment (MRI, PET, CT, etc.)
- **Track** application status from submission through approval
- **Accept** granted access and coordinate scheduling
- **Report** publications resulting from their research

The portal helps ReDIB staff:
- **Publish** calls for access applications
- **Review** technical feasibility of requests
- **Evaluate** scientific merit of applications
- **Manage** equipment allocation and scheduling
- **Generate** reports for ministry compliance

### The ReDIB Network

The portal serves **4 ReDIB nodes** across Spain:
1. **CIC biomaGUNE** (San Sebastián)
2. **BioImaC** (Madrid)
3. **Imaging La Fe** (Valencia)
4. **TRIMA@CNIC** (Madrid)

Each node offers specialized imaging equipment and expertise in preclinical, clinical, and radiotracer research.

---

## Understanding the COA Workflow

The ReDIB COA process follows **10 phases** from call creation to research outcome reporting. Understanding these phases will help you know what to expect as you use the portal.

### Phase 0: Foundation and Setup
**Who:** Administrators
- User accounts are created and roles assigned
- Equipment and nodes are configured
- Email notification templates are set up

### Phase 1: Call Management
**Who:** Coordinators
- Coordinators create and publish calls for applications
- Each call specifies submission deadlines, evaluation deadlines, and available equipment
- Published calls become visible to all users on the public call listing

### Phase 2: Application Submission
**Who:** Applicants (Researchers)
- Researchers browse open calls and submit applications through a 5-step wizard:
  1. **Basic Information:** Your contact details and ORCID
  2. **Project Details:** Funding information and project type
  3. **Equipment Request:** Select equipment and specify hours needed
  4. **Scientific Content:** Describe your research across 6 evaluation criteria
  5. **Declarations:** Confirm ethics compliance and data protection consent
- Applications can be saved as drafts and completed later
- Once submitted, applications receive a unique code (e.g., COA-2025-01-001)

### Phase 3: Feasibility Review
**Who:** Node Coordinators
- Node coordinators review applications requesting their equipment
- They assess **technical feasibility** (not scientific merit)
- For multi-node applications, **all nodes must approve** for the application to proceed
- Applicants are notified of feasibility decisions

### Phase 4: Evaluator Assignment
**Who:** Coordinators
- After the submission deadline, coordinators assign evaluators to applications
- The system automatically suggests evaluators while avoiding conflicts of interest
- Each application typically receives 2 evaluators
- Evaluators are notified of their assignments

### Phase 5: Evaluation Process
**Who:** Evaluators
- Evaluators review applications in a **blind review** process (applicant identity hidden)
- They score applications on **6 criteria**, each rated 0-2 points (maximum 12 points total):
  - **Category I: Scientific and Technical Relevance**
    1. Quality and originality
    2. Methodology and design suitability
    3. Expected scientific contributions
  - **Category II: Timeliness and Impact**
    4. Contribution to knowledge advancement
    5. Social/economic impact potential
    6. Exploitation and dissemination opportunity
- Evaluators also provide a recommendation (Approved/Denied) and optional comments
- The system calculates final scores by averaging all evaluators' scores

### Phase 6: Resolution and Prioritization
**Who:** Node coordinators (per-node decision) + ReDIB coordinator (oversight)
- Each node coordinator independently decides for the equipment at their node:
  accept, waitlist (pending), or reject.
- Per-node decisions aggregate to a final application outcome:
  - **All nodes accept →** application is **Accepted**
  - **Any node rejects →** application is **Rejected**
  - **No rejects but at least one waitlist →** application is **Pending** (waitlisted)
- Applications with competitive funding normally cannot be rejected at the
  resolution phase. The exception: if at least one evaluator recommended
  **Denied**, the node coordinator may use that independent denial as grounds
  to reject. (Feasibility rejection and evaluator denial remain available at
  their own phases regardless of funding status.)
- Approved hours are recorded per equipment; on reject the service layer
  forces approved hours to zero so Access Tracking doesn't show phantom
  approved time.
- Once aggregation finalises, the applicant receives a resolution email
  (accepted, pending, or rejected).

### Phase 7: Acceptance and Handoff
**Who:** Applicants, then node coordinators for waitlist promotions
- Accepted applicants have **10 days** to accept or decline the granted access.
- **Pending (waitlist)** applicants get the same 10-day accept/decline window
  but the wording differs — accepting the waitlist offer only keeps the
  application in the queue; no hand-off fires yet.
- When an applicant accepts an accepted grant, a single hand-off email goes
  to the applicant (`To`) with all relevant node coordinators on `Cc`, so
  they can reply-all to coordinate scheduling directly.
- When a slot frees up for a waitlisted application whose applicant has
  already accepted the waitlist offer, a node coordinator clicks
  **"Mark as Accepted"** on the Access Tracking page. That promotes the
  application to Accepted and triggers the same resolution-accepted and
  hand-off emails as a normal accepted application.
- If an applicant does not respond within 10 days, the application is
  automatically expired and hours are released.

### Phase 8: Execution and Completion
**Who:** Node Coordinators and Applicants
- Node coordinators and applicants coordinate directly to schedule experiment time
- This happens outside the portal via email or phone
- Coordinators can optionally mark access as "completed" in the portal for tracking purposes

### Phase 9: Publication Follow-up
**Who:** Applicants (Researchers)
- Applicants receive follow-up reminders at **6 months** and **12 months** after access completion
- They are asked to report any publications resulting from their research
- Publications must acknowledge ReDIB according to the template:
  > *"This work acknowledges the use of ReDIB ICTS, supported by the Ministry of Science, Innovation and Universities (MICIU) at [NODE NAME]."*
- Reporting publications helps demonstrate ReDIB's research impact

### Phase 10: Reporting and Statistics
**Who:** Coordinators
- Coordinators can view comprehensive statistics and generate reports
- Reports include:
  - Call summary reports (Excel workbooks with 3 sheets)
  - Equipment utilization metrics
  - Publication statistics and acknowledgment rates
  - Ministry compliance reports
- All report generation is tracked for audit purposes

---

## Getting Started (Phase 0)

### Accessing the Portal

The ReDIB COA Portal is accessed through your web browser at the URL provided by your ReDIB administrator.

**For administrators accessing the admin interface:**
Navigate to `/admin/` and log in with your administrator credentials. The admin interface is used for initial setup and configuration.

### Core Data in the System

The portal manages several types of information:

- **Organizations:** Universities, research centers, hospitals, and companies
- **Nodes:** The 4 ReDIB network nodes that provide equipment
- **Equipment:** Imaging devices (MRI, PET, CT, etc.) available at each node
- **Users:** Portal users with their roles and permissions
- **Calls:** Published opportunities to apply for equipment access
- **Applications:** Researcher requests for equipment access
- **Evaluations:** Scientific assessments of applications
- **Publications:** Research outputs resulting from equipment access

---

## User Roles and Permissions

The portal uses a **role-based access system** to control what each user can see and do. Understanding your role(s) will help you navigate the portal effectively.

**Important:** Users can have multiple roles. For example, you might be both an Applicant and an Evaluator.

### 1. Applicant

**Role identifier:** `applicant`

**Who you are:** A researcher applying for access to imaging equipment.

#### What you see in the portal

- **Dashboard:** Shows "My Applications" section with:
  - List of your applications and their current status
  - Count of draft applications you can continue working on
  - Quick action buttons to view applications or browse available calls

- **Sidebar Navigation:**
  - "My Applications" - View and manage your submissions
  - "Open Calls" - Browse available calls to apply for
  - "My Profile" - Update your contact information and preferences

#### What you can do

- Browse published calls and view their details
- Create and submit applications through the 5-step wizard
- Save applications as drafts and return to complete them later
- View your application status and evaluation results
- Accept or decline granted access (within 10-day deadline)
- Report publications resulting from your research
- Update your notification preferences

#### What you cannot do

- View other users' applications
- Access feasibility reviews or evaluations
- Create or manage calls
- Assign evaluators or make resolution decisions

#### Notifications you receive

- **Application confirmation** when you submit an application
- **Feasibility decision** when node review is complete
- **Resolution notification** when final decisions are made (accepted/pending/rejected)
- **Acceptance reminder** at 7 days if you haven't responded to acceptance
- **Publication follow-up** at 6 and 12 months after access completion
- **Call announcements** (if you've enabled this in your preferences)

**Tip:** You can control which notifications you receive in your profile settings under "Notification Preferences."

---

### 2. Node Coordinator

**Role identifier:** `node_coordinator`

**Who you are:** A staff member at one of the ReDIB nodes responsible for reviewing technical feasibility and coordinating equipment access.

#### What you see in the portal

- **Dashboard:** Shows node coordinator sections including:
  - "Pending Feasibility Reviews" with applications awaiting your review
  - Direct action buttons to review applications
  - Statistics on applications requesting your node's equipment

- **Sidebar Navigation:**
  - "Feasibility Reviews" - Applications awaiting technical review
  - "Scheduling" - Accepted applications needing coordination
  - "Access Tracking" - Monitor ongoing and completed access
  - Equipment assigned to your node

#### What you can do

- Review applications requesting equipment from your node
- Approve or reject applications based on technical feasibility
- Provide comments explaining feasibility decisions
- View applicant contact information for scheduling
- Mark access as completed (optional tracking)
- View statistics specific to your node's equipment
- Update your notification preferences

#### What you cannot do

- View scientific evaluations or evaluator scores
- Make final acceptance/rejection decisions (only feasibility)
- Assign evaluators
- Create or publish calls
- Generate system-wide reports

#### Notifications you receive

- **Feasibility request** when new applications request your equipment
- **Feasibility reminder** at 5 days if reviews are pending
- **Handoff notification** when applicants accept access (to coordinate scheduling)

**Important:** You only see applications that request equipment from your specific node. Multi-node applications appear in multiple node coordinators' queues.

---

### 3. Evaluator

**Role identifier:** `evaluator`

**Who you are:** An expert reviewer who assesses the scientific merit of applications.

#### What you see in the portal

- **Dashboard:** Shows evaluator sections including:
  - "My Pending Evaluations" with applications assigned to you
  - Evaluation deadlines and days remaining
  - Quick action buttons to view and complete evaluations

- **Sidebar Navigation:**
  - "My Evaluations" - Applications you need to evaluate
  - "Completed Evaluations" - Your past reviews

#### What you can do

- View applications assigned to you in **blind review format** (applicant identity hidden)
- Score applications on 6 criteria (0-2 points each, max 12 total)
- Provide a recommendation (Approved/Denied)
- Add optional comments to support your evaluation
- View evaluation deadlines and track your progress
- Update your notification preferences

#### What you cannot do

- See applicant name, organization, or contact information during review
- Edit evaluations after submission (they are locked)
- View other evaluators' scores before submitting your own
- Make final acceptance decisions
- Access feasibility reviews

#### Notifications you receive

- **Evaluation assignment** when you're assigned to review applications
- **Evaluation reminder** at 7 and 14 days if evaluations are pending
- **Deadline warnings** when evaluation deadlines are approaching

**Your specialization matters:** Evaluators can declare one or more specialization areas (e.g. `clinical`, `preclinical`, `radiotracers`). The system preferentially assigns you to applications matching any of your declared areas.

---

### 4. Coordinator (ReDIB Coordinator)

**Role identifier:** `coordinator`

**Who you are:** A ReDIB staff member with administrative authority to manage calls, assign evaluators, and make final decisions.

#### What you see in the portal

- **Dashboard:** Shows comprehensive coordinator panels including:
  - Active calls and their status
  - Resolution statistics across all calls
  - Recent applications and their progress
  - System-wide metrics and pending tasks

- **Sidebar Navigation:**
  - "Call Management" - Create, edit, publish, and close calls
  - "Evaluator Assignment" - Assign evaluators to applications
  - "Resolution" - Review evaluations and make final decisions
  - "Reports & Statistics" - Generate reports and view analytics
  - "Publications" - Review reported research outcomes

#### What you can do

- **Create and publish calls** with equipment allocations and deadlines
- **Assign evaluators** to applications (manual or automatic assignment)
- **Review evaluation results** and final scores
- **Make resolution decisions** (accept/pending/reject applications)
- **Finalize resolutions** and trigger acceptance deadlines
- **Generate Excel reports** for ministry compliance
- **View all applications** across all calls and nodes
- **Monitor publication reporting** and acknowledgment rates
- Update email notification templates (admin access required)

#### What you cannot do

- Conduct technical feasibility reviews (that's the node coordinators' role)
- Submit evaluations (that's the evaluators' role)
- Apply for equipment access as an applicant (separate role required)

#### Notifications you receive

- **Evaluator overdue reminder** (daily) for each evaluator who has an
  evaluation past the call's evaluation deadline, plus a lockout email
  the day the window closes.
- **Applicant declination** when accepted applicants decline access.
- **Publication submission** when applicants report research outcomes.

You do **not** receive a per-application "evaluations complete" email —
node coordinators own the next action (resolution). Track evaluation
progress from the call detail and resolution dashboard instead.

**Special authority:** Coordinators are the **only users who can create calls**. This ensures centralized control over the COA process.

---

### 5. Administrator (Admin)

**Role identifier:** `admin`

**Who you are:** A system administrator with elevated privileges for configuration and user management.

#### What you see in the portal

- **Dashboard:** Same as Coordinator, plus:
  - "Admin Panel" link in the sidebar (access to Django admin interface)

- **Sidebar Navigation:**
  - All sections available to coordinators
  - "Admin Panel" - Direct link to `/admin/` for system configuration

#### What you can do

Everything a Coordinator can do, plus:
- Access the Django admin interface for system configuration
- Create and manage user accounts
- Assign roles to users
- Configure nodes and equipment
- Manage email templates
- Configure system settings
- View and edit all data directly in the database

#### What makes you an admin

- You have the `admin` role assigned in UserRole, **OR**
- You are a superuser (highest privilege level)

**Security note:** Admin access should be restricted to technical staff responsible for system maintenance.

---

### 6. Superuser

**Who you are:** The highest privilege level in the system, typically used for initial setup and emergency access.

#### What you can do

- **Bypass all role restrictions** - Access any feature regardless of role assignments
- Full access to the Django admin interface
- Create other superusers and administrators
- Access all views and data in the system

**Note:** Superuser status is separate from role assignments. Superusers automatically pass all role checks, even without explicit roles assigned.

**Security warning:** Superuser accounts should be carefully protected and used only when necessary for system administration.

---

## Role Assignment and the "No Roles" State

### How roles are assigned

Roles are assigned by administrators through the Django admin interface at `/admin/`. A user can have:
- **No roles** - Limited access to public information only
- **One role** - Access specific to that role
- **Multiple roles** - Combined access from all assigned roles

### What happens if you have no roles assigned

If you log in without any assigned roles, you will see:
- A "no roles assigned" notice on your dashboard
- Access to browse public calls only
- A message instructing you to contact your administrator

**What you cannot do without roles:**
- Submit applications
- Review feasibility
- Evaluate applications
- Create or manage calls
- Access any role-specific features

**If you need role access:** Contact your ReDIB administrator to request appropriate role assignment.

---

## Notification Preferences

All users can control which email notifications they receive. This is managed through your profile settings.

### Available notification preferences

1. **Call Published Notifications**
   - Controlled by: `receive_call_notifications` flag on your user account
   - Who it affects: All users
   - What it does: Receive email when new calls are published

2. **Application Update Notifications**
   - Controlled by: `notify_application_updates` in Notification Preferences
   - Who it affects: Applicants, Coordinators
   - What it does: Receive updates on application status changes

3. **Evaluation Assignment Notifications**
   - Controlled by: `notify_evaluation_assigned` in Notification Preferences
   - Who it affects: Evaluators
   - What it does: Receive notification when assigned to review applications

4. **Feasibility Request Notifications**
   - Controlled by: `notify_feasibility_requests` in Notification Preferences
   - Who it affects: Node Coordinators
   - What it does: Receive notification when applications need feasibility review

5. **Reminder Notifications**
   - Controlled by: `notify_reminders` in Notification Preferences
   - Who it affects: Evaluators, Node Coordinators, Applicants
   - What it does: Receive deadline reminders and follow-up emails

### How to update your preferences

1. Log in to the portal
2. Click on your profile or settings
3. Navigate to "Notification Preferences"
4. Check or uncheck the notification types you want to receive
5. Save your changes

**Tip:** Even if you disable reminders, you'll still receive critical notifications like resolution decisions and acceptance deadlines.

---

## Understanding the Dashboard

Your dashboard appearance depends on your assigned role(s). Here's what each role sees:

### Dashboard sections by role

| Section | Applicant | Node Coordinator | Evaluator | Coordinator | Admin |
|---------|-----------|------------------|-----------|-------------|-------|
| My Applications | ✓ | | | | |
| Open Calls | ✓ | | | | |
| Pending Feasibility Reviews | | ✓ | | | |
| Scheduling & Access Tracking | | ✓ | | | |
| My Pending Evaluations | | | ✓ | | |
| Completed Evaluations | | | ✓ | | |
| Active Calls | | | | ✓ | ✓ |
| Resolution Statistics | | | | ✓ | ✓ |
| Recent Applications (All) | | | | ✓ | ✓ |
| System-wide Metrics | | | | ✓ | ✓ |
| Admin Panel Link | | | | | ✓ |

### Multiple roles = Combined dashboard

If you have multiple roles, you'll see sections from all your roles combined. For example:
- **Applicant + Evaluator:** See both "My Applications" and "My Pending Evaluations"
- **Node Coordinator + Evaluator:** See both "Pending Feasibility Reviews" and "My Pending Evaluations"

---

## Using the Portal

This section walks through what each user actually sees and does at the portal,
written as if you were sitting in front of the screen. After login, your
dashboard and the menu down the left side are tailored to your role(s). If
you have multiple roles (e.g. evaluator + applicant), the panels combine.

A few things every role sees at all times:

- A **navigation bar at the top** with the ReDIB logo, your name menu (Profile /
  Logout), and a **"Need help?"** link that opens an email to the ReDIB support
  address.
- A **footer** with the same support address.
- If your profile is missing a required field (phone, organization, position,
  …), the system redirects you to your **Profile** page until you fill it in.
  This matters most on first login — finish the profile, then the rest of the
  portal becomes available.

Pick the section below that matches your role:

- [Your Profile](#your-profile)
- [For Applicants](#for-applicants-researchers)
- [For Node Coordinators](#for-node-coordinators)
- [For Evaluators](#for-evaluators)
- [For ReDIB Coordinators](#for-redib-coordinators)

---

### Your Profile

Every user has a profile page where you manage your personal information and
account settings. Completing your profile is the first thing you need to do
after logging in for the first time.

#### Navigating to your profile

Click your **name** in the top-right corner of any page, then select
**Profile** from the dropdown menu. You can also navigate directly to
`/profile/`.

#### Required fields

The portal requires the following fields before you can access any other
pages. If any are missing, the system will redirect you to your profile
page automatically until you complete them:

- **First name**
- **Last name**
- **Phone number** — the number node coordinators will use to reach you for
  scheduling
- **Organization** — select your institution from the dropdown
- **Position** — your role at your institution (e.g. Researcher, Professor,
  Technician)

Once all required fields are filled in, click **Save Changes**. You will be
redirected to your dashboard and the rest of the portal becomes available.

#### Other profile fields

Beyond the required fields, you can also fill in:

- **ORCID** — your ORCID identifier (pre-fills into applications)
- **Specialization areas** (evaluators only) — declare your expertise areas
  (preclinical, clinical, radiochemistry) so the system can match you to
  relevant applications
- **Notification preferences** — control which email notifications you
  receive (call announcements, reminders, etc.)

#### Changing your password

1. Click your **name** in the top-right corner and select **Profile**.
2. At the bottom of the profile page, click the **Change Password** link.
   This takes you to the password change form.
3. Enter your **current password**, then your **new password** twice to
   confirm.
4. Click **Change Password**. You will be logged out and redirected to the
   login page, where you can sign in with your new password.

You can also navigate directly to `/accounts/password/change/`.

---

### For Applicants (researchers)

You apply for time on imaging equipment, follow the application through review
and resolution, accept the offer if granted, and report any publications that
result.

#### Your dashboard

After logging in you see **My Applications** — a card listing every application
you've created, with a status badge on each one (Draft / Under Review / Pending
Evaluation / Evaluated / Accepted / Pending (Waitlist) / Rejected / etc.) and
the action button you can take next: *Continue editing*, *Accept*, *Decline*,
or *Add publication*.

The left sidebar (under the **Applicant** heading) gives you:

- **My Applications** — the same list, in full detail.
- **My Active Access** — applications that have been accepted; this becomes
  your hand-off page once you say yes to a granted slot.
- **Publications** — your reported publications + the form to add new ones.
- **Open Calls** — currently-published calls you can apply to.

#### Submitting an application

1. Click **Open Calls** (or *Browse Open Calls* on the dashboard). Each open
   call shows the submission deadline, the equipment available across nodes,
   and a description.
2. On a call's detail page, click **Apply**. You enter a **5-step wizard**.
   Drafts auto-save after each step — you can leave the wizard and come back
   any time from **My Applications → Continue**.
   - **Step 1 — Applicant info**: name, ORCID, organization, email, phone,
     project name. Most fields pre-fill from your profile. The email and
     phone you enter *here* are what node coordinators will use to reach you,
     so they can be different from your account email if needed.
   - **Step 2 — Project details**: short summary, funding agency (pick from
     the dropdown — about 375 entries seeded; use *Other (enter new)* if
     yours isn't listed), origin of funds, subject area, service modality.
   - **Step 3 — Equipment request**: select equipment items from the call
     and enter the hours you need for each. You can request equipment from
     more than one node in the same application.
   - **Step 4 — Scientific content**: six free-text sections — quality and
     originality, methodology, expected contributions, advancement of
     knowledge, social/economic impact, exploitation/dissemination.
     Evaluators score each one 0–2.
   - **Step 5 — Declarations**: animal/human use, ethics-committee
     approval, insurance, informed consent, and data-processing consent.
     Some checkboxes only appear if upstream answers warrant them.
3. When you click **Submit**, the application status moves to **Under
   Feasibility Review** and feasibility-review emails go out to the relevant
   node coordinators.

#### What happens after you submit

Each status change emails you, and the dashboard shows the current state:

- **Feasibility result**: each requested node either approves, rejects, or
  asks you for edits. If any node rejects on technical grounds the whole
  application is rejected. If any node asks for edits, the application
  returns to draft so you can revise and resubmit.
- **Evaluation**: after the submission window closes, evaluators score your
  application (you don't see scores during this phase). Once all evaluators
  submit, the status moves to **Evaluated**.
- **Resolution**: each node coordinator decides Accept / Pending (waitlist) /
  Reject for the equipment at *their* node. The combination becomes your
  overall outcome — see *Phase 6* in the workflow overview for the
  aggregation rule.
- **Acceptance**: if your outcome is **Accepted** or **Pending (waitlist)**,
  you have **10 days** to respond. From your dashboard click **Accept Access**
  or **Decline Access**. If you do nothing within 10 days, the application
  auto-expires and the hours are released.

#### After you've been accepted

- The **My Active Access** page lists your accepted applications with the
  per-equipment hours approved and the contact info for each node
  coordinator. **Scheduling happens off-portal** — by email or phone
  with the node coordinators (they were CC'd on the hand-off email, so the
  easiest start is to reply-all).
- When the work is done, click **Mark Complete** on the access entry and
  log the actual hours used per equipment.

#### Publications

Six months after your access completes you'll get a follow-up email asking
about publications. From the **Publications** page (or the *Add Publication*
button next to a completed application), submit each publication with title,
authors, journal, DOI, publication date, and the acknowledgment text from the
article. Publications are how ReDIB demonstrates research impact, so this
matters even when the work is years downstream.

---

### For Node Coordinators

You handle two technical decisions per application that requests equipment from
your node: **feasibility** (can we actually do this?) and **resolution** (do we
accept this on our equipment?). After the applicant accepts, you also coordinate
scheduling with them directly.

#### Your dashboard

Two queues at the top:

- **Pending Feasibility Reviews** — applications just submitted that request
  equipment at your node.
- **Pending Resolution Decisions** — applications that have finished
  evaluation and are waiting for your accept/waitlist/reject call.

The left sidebar (under **Node Coordinator**) gives you:

- **Feasibility Reviews** — full feasibility queue.
- **Resolution Queue** — full resolution queue.
- **Scheduling** — accepted applications at your node.
- **Access Tracking** — master list of all applications at your node, plus
  the buttons for **promoting waitlisted** applications to accepted and for
  **marking access complete + logging hours**.

#### Feasibility review

1. Click **Review** on a queue entry (or open **Feasibility Reviews**). You
   see the full application — applicant info, project details, equipment
   requested **at your node only** (other nodes' equipment is their call,
   not yours), and the scientific content.
2. Pick one of three actions:
   - **Approve** — equipment is feasible at your node.
   - **Request edits** — applicant needs to revise before you can sign off
     (you must include a comment explaining what to change).
   - **Reject** — technically infeasible at your node (you must include a
     comment).
3. Submit. The system aggregates across all requested nodes: every node must
   approve before the application moves to evaluation. If any node rejects,
   the application is terminally rejected. If any node requests edits, it
   returns to the applicant for revision.

#### Resolution

After all evaluators submit their scores, the application appears in your
**Resolution Queue**.

1. Click **Resolve**. You see the average score, each evaluator's individual
   score and recommendation, and a per-equipment table for *your node* with
   the **hours requested** and a field for **hours approved** (you can grant
   fewer hours than requested).
2. Pick a decision: **Accept**, **Pending (waitlist)**, or **Reject**.
   - If the application has **competitive funding**, **Reject is greyed
     out** *unless* at least one evaluator independently recommended
     Denied — see *Phase 6* in the workflow overview for why.
3. Add an optional comment and submit. Other nodes' decisions (if any) are
   visible on the page so you can see the full picture.

When all involved nodes have decided, the application status finalizes
(Accepted / Pending / Rejected) and the applicant gets the resolution email.

#### Access tracking + waitlist promotion

Open **Access Tracking**:

- For applications that are **Pending (waitlist)** *and* the applicant has
  said yes to the waitlist offer, a **Promote to Accepted** button appears.
  Click it when a slot frees up — that flips the status to Accepted, fires
  the resolution-accepted and hand-off emails, and starts scheduling.
- For applications that are **Accepted** (and the applicant has confirmed),
  a **Mark Complete + Log Hours** button appears once the work is done.
  Use it to record the actual hours used per equipment.

You only see applications at your node(s); multi-node applications appear
in multiple coordinators' queues.

---

### For Evaluators

You score applications assigned to you. The system hides applicant identity
so your scoring is independent.

#### Your dashboard

You see **My Pending Evaluations** — every application currently assigned to
you, with the call code, the date you were assigned, and the evaluation
deadline. Each row has an **Evaluate** button.

The left sidebar (under **Evaluator**) has a single entry: **My Evaluations**.
That page is the full version of the dashboard list, plus an *Overdue* section
(if you have any past-deadline assignments) and a *Completed* section showing
your past submissions read-only.

#### Submitting an evaluation

1. Click **Evaluate** on an application. You land on the evaluation form.
   The header has a **Download Blind PDF** button — useful if you'd rather
   review the application offline.
2. **Read the application.** You see the project title, summary, funding
   origin, subject area, equipment requested, and the six scientific-content
   sections. **You do not see** the applicant's name, ORCID, organization,
   contact info, project code, or funding agency — that's the blind-review
   protection.
3. **Score the six criteria**, each on a 0–2 scale (0 = Poor, 1 = Good,
   2 = Excellent). The total runs 0–12 and the form keeps a live total
   as you go.
   - Category I — Scientific & Technical Relevance: quality/originality,
     methodology, expected contributions.
   - Category II — Timeliness & Impact: knowledge advancement,
     social/economic impact, exploitation/dissemination.
4. Pick a recommendation: **Approved** or **Denied**.
   - If you pick **Denied**, **a comment is required** — your independent
     denial is the documented basis for rejecting an application that has
     competitive funding (see *Phase 6*).
5. **Submit.** Once submitted, your scores are locked. If the evaluation
   deadline has passed by more than 7 days (the grace period), the form
   auto-locks even if you haven't submitted, and the ReDIB coordinator is
   notified.

If you have multiple specialization areas declared on your profile
(preclinical / clinical / radiochemistry), the system tries to assign you
applications matching one of them. Update your areas any time on your
**Profile** page.

---

### For ReDIB Coordinators

You run the calls and watch the workflow end-to-end. You don't do feasibility
(that's the node coordinators) or evaluation (that's the evaluators), but you
have visibility into everything and you make sure each call closes cleanly.

#### Your dashboard

Three panels:

- **Active Calls** — quick view of open and recently-closed calls with status
  and an action button per call.
- **Quick Stats** — pending-resolution count + recent-application count + a
  button into Reports.
- **Recent Applications** — a table across all calls so you can spot stuck
  applications.

The left sidebar (under **Coordinator**) gives you four entry points:

- **Call Management** — create / edit / publish / close calls.
- **Assign Evaluators** — assign evaluators per application, or run
  auto-assign for a whole call.
- **Resolution** — overview of every application's resolution status.
- **Reports** — statistics dashboard + Excel exports.

#### Creating a call

1. From **Call Management** click **Create New Call** (or *Create First Call*
   on a fresh system). Fill in:
   - **Call Code** (e.g. `COA-2026-01`), **Title**, **Description**, optional
     Guidelines.
   - **Status** — leave as **Draft** until you're ready to publish; only
     `Open` calls are visible to applicants.
   - **Submission period** (start + end), **Evaluation deadline**, **Execution
     period** (start + end). All dates are date-only; the system uses 23:59
     as the end-of-day cutoff. The form rejects illogical ordering.
   - **Equipment Allocations** — every active equipment item across all
     nodes is included by default. Tick the **Remove** column to exclude
     any. You must keep at least one.
2. **Save Call** — the call is saved as a Draft, only you can see it.
3. When ready, click **Publish Call** (with confirmation). Status moves to
   **Open**, the `published_at` timestamp is set, a notification email goes
   out to every user who opted in to call announcements, and the call appears
   on the public `/calls/` page.
4. After the submission deadline, click **Close** to stop new submissions and
   open the call for evaluator assignment.

You can edit a call after publication, but you **cannot delete** it once
published or unpublish it. To revert a published-but-empty call to Draft you
have to use the admin panel at `/admin/`.

#### Assigning evaluators

After a call is closed, open **Assign Evaluators** and pick the call. The
system shows every application that needs evaluators with suggested matches
based on evaluator areas + conflict-of-interest detection (same organization).
Accept the suggestion or override manually. **Today this fires assignment
emails immediately** — there's a backlog item to add a confirm-and-review
preview step (#4 in `docs/developer/backlog.md`).

You can re-assign or add evaluators at any time before the deadline.

#### Watching resolution

The **Resolution** dashboard shows every application by status across calls.
Per-application, you can drill into the evaluation summary (per-criterion
average + per-evaluator scores + recommendations + comments). You don't make
the resolution decisions yourself — the **node coordinators** at each
requested node do that. Your job is to flag stuck applications and follow up
on overdue evaluators.

The system already fires daily reminder emails for overdue evaluators (and
copies you on the lockout when an evaluator misses the grace-period
deadline), so you don't need to chase by hand.

#### Reports

The **Reports** page shows statistics across all calls — total apps, average
score, acceptance rate, breakdown by status, publication-acknowledgment rate.
The big affordance is **Download Excel Report** for any call: a multi-sheet
workbook (applications + equipment usage + summary) suitable for ministry
compliance reporting.

---

## Getting Help

### Common questions

**Q: I can't see the call management section. Why?**
A: Only users with the Coordinator or Admin role can create and manage calls. Contact your administrator if you need this access.

**Q: Can I change my role?**
A: No, roles are assigned by administrators. If you need a different or additional role, contact your ReDIB administrator.

**Q: Why can't I see applicant names in evaluations?**
A: Evaluations use blind review to ensure objectivity. Applicant identity is intentionally hidden from evaluators.

**Q: I'm a node coordinator. Why don't I see all applications?**
A: Node coordinators only see applications requesting equipment from their specific node. This is intentional to focus your review on relevant requests.

**Q: How do I stop receiving reminder emails?**
A: Update your notification preferences in your profile settings. Uncheck "Reminder Notifications" to disable deadline reminders.

### Technical support

For technical issues, questions about the portal, or role assignment requests, contact:

**ReDIB Portal Administrator**
Email: [Your admin email here]
Support hours: [Your support hours here]

---

## Next Steps

Now that you understand the portal workflow and your role, you're ready to start using the system:

- **Applicants:** Browse open calls and start your first application
- **Node Coordinators:** Check for pending feasibility reviews
- **Evaluators:** Review your assigned evaluations before the deadline
- **Coordinators:** Create your first call or manage existing applications
- **Admins:** Configure nodes, equipment, and user accounts

**Remember:** The portal guides you through each step with clear instructions and help text. Don't hesitate to explore the interface - you can always save drafts and return later.

---

**Document Version History**
- v1.0 (January 2026): Initial user guide created for ReDIB COA Portal
- v1.2 (April 2026): "Using the Portal" rewritten as four role-based
  walkthroughs (Applicants, Node Coordinators, Evaluators, ReDIB
  Coordinators) covering each role end-to-end as the user sees it.

---
