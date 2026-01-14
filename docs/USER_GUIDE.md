# ReDIB COA Portal - User Guide

**Version 1.0** | **Last Updated: January 2026**

---

## Table of Contents

1. [Introduction](#introduction)
2. [What is the ReDIB COA Portal?](#what-is-the-redib-coa-portal)
3. [Understanding the COA Workflow](#understanding-the-coa-workflow)
4. [Getting Started](#getting-started-phase-0)
5. [User Roles and Permissions](#user-roles-and-permissions)
6. [Using the Portal](#using-the-portal)

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
**Who:** Coordinators
- Coordinators review evaluated applications and make final decisions
- Applications are prioritized by score (highest first)
- Three possible outcomes:
  - **Accepted:** Access approved and equipment hours allocated
  - **Pending:** Quality acceptable, placed on waiting list
  - **Rejected:** Does not meet quality threshold
- **Special rule:** Applications with competitive funding are automatically accepted
- Once finalized, all applicants receive resolution notifications

### Phase 7: Acceptance and Handoff
**Who:** Applicants (Accepted researchers)
- Accepted applicants have **10 days** to accept or decline the granted access
- Upon acceptance, applicants and node coordinators receive handoff emails with scheduling instructions
- If no response within 10 days, the access is automatically declined
- Declined access releases equipment hours for pending applications

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

**Your specialization matters:** Evaluators have optional specialization areas (preclinical, clinical, radiotracers). The system preferentially assigns you to applications matching your expertise.

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

- **Evaluation completion** when all evaluators finish reviewing a call
- **Applicant declination** when accepted applicants decline access
- **Publication submission** when applicants report research outcomes

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

This section provides step-by-step instructions for using the portal. Each subsection corresponds to a phase in the COA workflow and includes detailed guidance for completing tasks.

---

### Phase 1: Creating and Managing Calls (For Coordinators)

This phase guides you through creating, publishing, and managing calls for Competitive Open Access applications.

#### Prerequisites

Before starting:
- You must have the **Coordinator** or **Admin** role
- You must have your login credentials
- Equipment and nodes should be configured in the system (Phase 0)

**First-time login:** If this is your first time logging in, you'll need to set your password. Contact your administrator to have your password set via the admin panel at `/admin/`.

---

#### Step 1: Log In to the Portal

1. Navigate to the portal homepage at `/`
2. You will be automatically redirected to the **Coordinator Dashboard**
3. If you see a login page instead, enter your credentials:
   - **Email:** Your assigned coordinator email (e.g., `coordinator@redib.net`)
   - **Password:** Your assigned password

**Expected Result:** You should see the coordinator dashboard with sections for active calls, resolution statistics, and recent applications. 

**Note:** If this is your first login you will be required to confirm your email if you have not yet done so. This is done by an automated email sent to your login email address.

---

#### Step 2: Navigate to Call Management

1. In the left sidebar, click **"Call Management"**
2. You will see a list of existing calls (if any)

**First-time experience:** If no calls exist yet, you'll see a message: "No Calls Yet" with a button labeled **"Create First Call"**

**What you'll see:**
- A table listing all calls with their code, title, status, submission period, equipment count, and application count
- Action buttons for each call (View, Edit, Publish/Close, Delete for drafts)

---

#### Step 3: Create a New Call

1. Click the **"Create New Call"** button (or **"Create First Call"** if it's your first call)
2. You'll be taken to the call creation form

Fill out the following information:

**Call Details:**

3. **Call Code** (Required)
   - Enter a unique identifier for the call
   - Format: `COA-YYYY-NN` (e.g., `COA-2026-01`)
   - This code will be visible to applicants

4. **Title** (Required)
   - Enter a descriptive title for the call
   - Example: "Competitive Open Access Call - January 2026"

5. **Status** (Required)
   - Select **"Draft"** (default)
   - Leave as draft until you're ready to publish
   - **Note:** Only published calls (status = "Open") are visible to applicants

6. **Description** (Required)
   - Write a multi-line description of the call scope
   - This text will be visible to applicants on the public call page
   - You can use HTML formatting if needed

7. **Guidelines** (Optional)
   - Provide application guidelines and requirements
   - Example: Eligibility criteria, required documents, etc.

---

**Important Dates:**

All dates are **date-only** (no time selection needed). The system automatically sets deadlines to 23:59 (end of day).

8. **Submission Period - Start Date** (Required)
   - Select the date when applications can start being submitted
   - Example: Today's date or a future date

9. **Submission Period - End Date** (Required)
   - Select the deadline for application submissions
   - Must be **after** the submission start date
   - Recommended: 45 days after start date
   - **Note:** Applications can be submitted until 23:59 on this date

10. **Evaluation Deadline** (Required)
    - Select the deadline for evaluators to complete their reviews
    - Must be **after** the submission end date
    - Recommended: 15 days after submission end (60 days from start)

11. **Execution Period - Start Date** (Required)
    - Select when approved applicants can begin using the equipment
    - Recommended: 30-60 days after evaluation deadline

12. **Execution Period - End Date** (Required)
    - Select when equipment access must be completed
    - Must be **after** execution start date
    - Recommended: 90-180 days after execution start

**Validation:** The form will prevent you from:
- Setting evaluation deadline before submission end date
- Setting execution end before execution start date
- Creating overlapping or illogical date ranges

---

**Equipment Allocations:**

13. **Review Equipment List**
    - Scroll down to the "Equipment Allocations" section
    - You'll see a table showing **all active equipment** from all nodes
    - **By default, all equipment is included** in the call

14. **Remove Equipment (Optional)**
    - If you want to **exclude** specific equipment from this call, check the "Remove" checkbox next to that equipment
    - **Note:** The description says "Check the box next to any equipment you want to **exclude** from this call"
    - Equipment without a checkmark will be included in the call

**Important:** You must include at least one equipment item. The system will prevent you from publishing a call with no equipment allocations.

---

15. **Save the Call (Draft)**
    - Click the **"Save Call"** button at the bottom
    - The call will be saved with status = "Draft"

**Expected Result:**
- You'll see a success message: "Call [CODE] created successfully"
- You'll be redirected to the call edit page
- The call is **not yet visible** to applicants (it's still a draft)

---

#### Step 4: Review Your Call

After saving, you can:

1. **View the call details** by clicking the **eye icon** in the Call Management dashboard
2. **Edit the call** by clicking the **pencil icon** or by being on the edit page already
3. **Check the equipment allocations** to ensure the correct equipment is included

**At this point, you can:**
- Continue editing the call
- Delete the draft call if needed (red "Delete Call" button)
- Publish the call when ready (green "Publish Call" button)

---

#### Step 5: Publish the Call

When you're ready to make the call visible to applicants:

**Option A: From the Edit Page**

1. While editing the call, locate the **"Publish Call"** button (green button on the right)
2. Click **"Publish Call"**
3. Confirm the action when prompted: "Publish this call? This will send notification emails to users."

**Option B: From the Call Management Dashboard**

1. Find your draft call in the table
2. Click the **"Publish"** button (green send icon) in the Actions column
3. Confirm the action when prompted

**Option C: By Changing Status**

1. Edit the call
2. Change the **Status** dropdown from "Draft" to "Open for Submissions"
3. Click **"Save Call"**

**Expected Result:**
- Call status changes to **"Open"**
- The `published_at` timestamp is set to the current date/time
- **Notification emails are sent** to all users who have enabled call notifications
- The call becomes **visible on the public call listing** (if the submission period has started)

---

#### Step 6: Verify Public Visibility

1. Open a new browser tab or log out
2. Navigate to the public calls page at `/calls/`
3. Check if your call appears:
   - **Currently Open:** If today's date is within the submission period
   - **Upcoming Calls:** If the submission start date is in the future

**What applicants will see:**
- Call code and title
- Description (truncated)
- Submission deadline (date only, no time)
- Number of equipment items available
- "Apply Now" button (if logged in) or "Login to Apply" button

---

#### Step 7: Managing Published Calls

Once a call is published, you can:

**Close the Call for Submissions:**

1. In the Call Management dashboard, find the open call
2. Click the **"Close"** button (lock icon)
3. Confirm the action
4. The call status changes to **"Closed"**
5. New applications can no longer be submitted
6. The call is ready for evaluator assignment (Phase 4)

**Edit a Published Call:**

1. You can still edit call details (title, description, dates)
2. Be careful changing dates after applications have been submitted
3. Equipment allocations can be modified

**Delete a Call:**

**Important:** You can only delete **draft** calls. Published calls cannot be deleted.

To delete a draft call:

1. **Option A (Edit Page):** Click the red **"Delete Call"** button
2. **Option B (Dashboard):** Click the trash icon in the Actions column
3. Confirm the deletion when prompted: "WARNING: This will permanently delete this call and all associated equipment allocations. This action cannot be undone. Are you sure?"

**Expected Result:**
- The call and all equipment allocations are permanently deleted
- You're redirected to the Call Management dashboard
- You'll see a success message: "Call [CODE] has been permanently deleted"

**Safety Features:**
- Only draft calls can be deleted
- Calls with applications cannot be deleted (additional safety check)
- JavaScript confirmation prevents accidental deletion

---

#### Common Issues and Tips

**Q: I created a call but applicants can't see it**
A: Check two things:
1. Is the call **published** (status = "Open")? Draft calls are not visible to applicants.
2. Has the submission period **started**? Calls only appear in "Currently Open" if today's date is within the submission period.

**Q: The form won't let me save**
A: Check for validation errors:
- Evaluation deadline must be **after** submission end date
- Execution end must be **after** execution start
- All required fields must be filled

**Q: How do I unpublish a call?**
A: You cannot unpublish a call once it's been published. You can only:
- Close it (prevents new applications)
- Edit its details
- If it has no applications, you could close it and ask an administrator to change the status back to draft via the admin panel

**Q: Can I delete a published call?**
A: No, only draft calls can be deleted. This prevents accidental deletion of calls with applications.

**Q: What happens to the equipment I unchecked?**
A: Equipment without a checkmark in the "Remove" column will be **included** in the call. Equipment with a checkmark will be **excluded**.

**Q: Why don't I see all nodes' equipment?**
A: You should see all active equipment from all nodes. If equipment is missing, it may be marked as inactive. Contact an administrator to activate equipment via the admin panel.

---

#### Next Steps

After publishing your call:

1. **Monitor applications** as they come in (Phase 2)
2. Wait for the **submission deadline** to pass
3. **Close the call** for submissions
4. **Assign evaluators** to applications (Phase 4)
5. Continue through the workflow phases...

For details on subsequent phases, see the workflow overview in the "Understanding the COA Workflow" section.

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

---
