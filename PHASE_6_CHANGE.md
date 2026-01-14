 Phase 6 Resolution Workflow Change: Node Coordinator Ownership

 Overview

 Restructure the Phase 6 Resolution & Prioritization workflow to shift ownership from ReDIB Coordinator to individual
 Node Coordinators, implementing multi-node coordination logic and equipment usage tracking.

 Current State Analysis

 Current Resolution Ownership (Phase 6)

 - Owner: ReDIB Coordinator (global role)
 - Location: /applications/resolution/* views
 - Process: Single coordinator decides accept/reject/waitlist for ALL applications
 - Auto-approval: Applications with has_competitive_funding=True auto-accepted
 - Hours allocation: hours_approved auto-populated from hours_requested on acceptance

 Existing Infrastructure

 - Node Coordinators: Already exist via UserRole(role='node_coordinator', node=<node>)
 - Equipment-Node Link: RequestedAccess → Equipment → Node
 - Hours Tracking: RequestedAccess.hours_requested/hours_approved/actual_hours_used
 - Precedent: Feasibility review already uses node-coordinator pattern (Phase 3)

 Requirements Summary

 New Resolution Ownership

 1. Node coordinators own resolution for applications requesting their node's equipment
 2. Multi-node logic:
   - Accept if ALL nodes accept
   - Reject if ANY node rejects
   - Waitlist if no rejects but at least one waitlist
 3. Per-equipment hours approval: Node coordinator sets approved hours per equipment item
 4. Notifications: Applicants notified with final resolution after all nodes decide

 Equipment Usage Tracking

 5. Applicant tracking: Mark equipment entries as "done" and enter actual hours used
 6. Node coordinator tracking: Also mark equipment entries as "done" and enter actual hours
 7. Admin override: Only admins can reverse "done" status

 Dashboard Changes

 8. Node coordinator sidebar: Add "Resolution" option
 9. View scope: See evaluated applications requesting their node's equipment
 10. Application detail: View app, average scores, individual evaluations (optional via details button), and set resolution + approved hours
 11. All users visibility: Show final resolution and approved vs requested hours in dashboards

 Implementation Design

 Architecture Overview

 Following the proven FeasibilityReview pattern from Phase 3, we'll create a distributed resolution system where each
 node coordinator independently reviews applications requesting their equipment, then the system aggregates these
 decisions into a final application resolution.

 Key Components

 1. New Model: NodeResolution

 class NodeResolution(models.Model):
     """Node coordinator's resolution decision for applications requesting their equipment"""
     application = ForeignKey(Application)
     node = ForeignKey(Node)
     reviewer = ForeignKey(User)  # Node coordinator
     resolution = CharField(choices=['accept', 'waitlist', 'reject'])
     comments = TextField()
     reviewed_at = DateTimeField()

     class Meta:
         unique_together = ['application', 'node']

 Pattern mirrors FeasibilityReview model - one record per application-node combination.

 2. RequestedAccess Enhancements

 Add equipment completion tracking:
 - is_completed (boolean) - Set to True when EITHER applicant OR node marks done
 - completed_by (ForeignKey to User) - Who marked it complete
 - completed_at (DateTimeField) - When marked complete
 - actual_hours_reported_by (ForeignKey to User) - Who reported actual hours
 - actual_hours_reported_at (DateTimeField)

 The hours_approved field already exists and will be set by node coordinators (can differ from hours_requested).

 Note: Either applicant OR node coordinator can mark equipment as done (not both required).

 3. Service Layer: NodeResolutionService

 New service at applications/services/node_resolution.py:

 Key Methods:
 - get_applications_for_node_resolution() - Filter applications requesting node's equipment
 - apply_node_resolution(application, resolution, comments, approved_hours_dict, user) - Apply node's decision and set
 hours_approved per equipment
 - aggregate_application_resolution(application) - Aggregate multi-node decisions using logic:
   - ALL accept → Application accepted
   - ANY reject → Application rejected
   - No rejects but ≥1 waitlist → Application pending
   - Not all decided → Keep status='evaluated', no notification

 4. Views Architecture

 Node Coordinator Views (new):
 - node_resolution_queue() - Dashboard showing pending applications per node
 - node_resolution_review(application_id, node_id) - Resolution form with:
   - Application details and evaluation scores
   - Equipment list with hours_requested vs hours_approved inputs
   - Resolution radio buttons (accept/waitlist/reject)
   - Comments field
 - mark_equipment_done() - Applicant marks equipment complete, reports actual hours
 - node_confirm_equipment_done() - Node coordinator confirms completion

 ReDIB Coordinator Views (modified):
 - Keep existing views but read-only - show node resolution breakdown
 - Display per-application: which nodes decided what
 - Show aggregation status (pending/partial/complete)
 - No override capability - node decisions are final
 - Can view reports and monitor progress but cannot modify resolutions

 5. URL Structure

 /applications/node-resolution/ → queue
 /applications/node-resolution/<app_id>/node/<node_id>/ → review form
 /applications/<app_id>/equipment/<req_access_id>/mark-done/ → completion

 6. Multi-Node Aggregation Logic

 When a node coordinator submits their resolution:
 1. Validate competitive funding: If application has has_competitive_funding=True, node coordinators cannot reject
 (auto-accept at node level)
 2. Create/update NodeResolution record with their decision
 3. Set hours_approved for each equipment item from their node
 4. Check if all required nodes have decided:
   - Get unique nodes via application.requested_access.values_list('equipment__node').distinct()
   - Count decided nodes via application.node_resolutions.exclude(resolution='').count()
 5. If all decided, automatically aggregate using priority logic:
   - Any reject → 'rejected'
   - No rejects but any waitlist → 'pending'
   - All accept → 'accepted'
 6. Update Application.resolution, Application.status, aggregate comments
 7. Immediately trigger notifications to applicant (no manual finalization step)

 7. Notifications

 Trigger Point: Only when ALL nodes have decided and aggregation completes.

 Email Content: Include node-by-node breakdown showing each node's decision and approved hours per equipment.

 Modified Task: send_resolution_notifications_task() in applications/tasks.py

 8. Dashboard Integration

 Node Coordinator Sidebar: Add "Resolution Queue" link with pending count badge

 Node Coordinator Dashboard Card: Show "X applications awaiting your resolution"

 ReDIB Coordinator Dashboard: Show resolution progress per call (total, fully decided, partial, pending)

 9. Forms

 - NodeResolutionForm - Resolution choice and comments
 - NodeResolutionEquipmentFormSet - Inline formset for hours_approved per equipment
 - EquipmentCompletionForm - Report actual_hours_used

 10. Templates

 New:
 - templates/applications/node_resolution/queue.html - Node coordinator dashboard
 - templates/applications/node_resolution/review.html - Resolution form
 - templates/applications/equipment_completion.html - Mark equipment done

 Modified:
 - templates/dashboard_base.html - Add sidebar link
 - templates/applications/resolution/call_detail.html - Show node breakdown

 Critical Files to Modify

 1. applications/models.py - Add NodeResolution model, enhance RequestedAccess
 2. applications/services/node_resolution.py - Create new service (NEW FILE)
 3. applications/views.py - Add 4 new views, modify coordinator views
 4. applications/forms.py - Add 3 new forms
 5. applications/urls.py - Add new URL patterns
 6. applications/tasks.py - Modify notification task
 7. applications/admin.py - Add NodeResolution admin
 8. templates/ - Create/modify templates as listed
 9. applications/migrations/ - Create migration for model changes

 Implementation Sequence

 1. Models & Migration (Day 1)
   - Create NodeResolution model
   - Enhance RequestedAccess
   - Write migration
   - Add admin registration
 2. Service Layer (Day 2-3)
   - Create NodeResolutionService
   - Implement aggregation logic
   - Write unit tests
 3. Forms (Day 3)
   - Create NodeResolutionForm
   - Create equipment formset
   - Create completion form
 4. Views (Day 4-5)
   - Node coordinator views
   - Equipment completion views
   - Modify coordinator views
 5. Templates (Day 5-6)
   - Create node coordinator templates
   - Modify dashboard templates
   - Update sidebar navigation
 6. URLs & Integration (Day 6)
   - Wire up URL patterns
   - Test navigation flows
 7. Notifications (Day 7)
   - Modify notification task
   - Update email templates
   - Test trigger conditions
 8. Testing (Day 8-10)
   - Unit tests
   - Integration tests
   - Multi-node scenarios
   - Manual QA

 Testing Strategy

 Multi-Node Scenarios:
 - 2-node both accept → accepted
 - 2-node: accept + waitlist → pending
 - 2-node: accept + reject → rejected
 - 3-node: various combinations
 - Sequential decisions (node 1 then node 2)

 Equipment Tracking:
 - Applicant can mark done OR node coordinator can mark done
 - Either one is sufficient for is_completed = True
 - Test both paths work independently

 Edge Cases:
 - Node coordinator tries to resolve wrong node's application
 - Node coordinator tries to reject competitive funding application (should be blocked)
 - Change decision before aggregation (should be allowed)
 - All nodes decide simultaneously (race condition)
 - Application requests equipment from single node vs multiple nodes

 Data Migration

 For existing applications in 'evaluated' status:
 - Create pending NodeResolution records for each node involved
 - No changes to already-resolved applications (keep as historical data)

 Verification Plan

 After implementation:

 1. Manual Testing:
   - Create test call with multiple nodes
   - Submit application requesting equipment from 2+ nodes
   - Have each node coordinator log in and resolve
   - Verify aggregation logic
   - Test equipment completion flow
 2. Automated Tests:
   - Run full test suite
   - Add new tests for multi-node scenarios
 3. Smoke Test Checklist:
   - Node coordinators see only relevant applications
   - Hours approved can differ from hours requested
   - Multi-node aggregation follows priority rules
   - Notifications sent only after all nodes decide
   - Equipment completion requires both parties
   - ReDIB coordinator has visibility
   - Dashboard counts are accurate

 Rollback Plan

 If issues arise:
 1. This is on a branch (change-resolution-ownership)
 2. Can revert to main branch
 3. No production data affected (development/testing phase)
 4. Migration can be reversed if needed

 ---
 Design Decisions Summary

 Based on user clarification:

 1. Competitive Funding Auto-Accept: Applications with has_competitive_funding=True cannot be rejected by node
 coordinators (maintains current policy). Form will disable reject option, validation will prevent rejection.
 2. Equipment Completion: Either applicant OR node coordinator marking equipment as "done" is sufficient (not both
 required). Simplifies workflow while maintaining tracking.
 3. ReDIB Coordinator Role: Read-only visibility with no override capability. Node coordinator decisions are final.
 ReDIB coordinator can monitor progress and generate reports.
 4. Automatic Aggregation: Final resolution is set and notifications sent automatically when the last node makes their
 decision (no manual finalization step needed). Provides fastest response to applicants.

 These decisions create a fully distributed resolution system with appropriate safeguards for competitive funding
 commitments.
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌

 Requested permissions:
   · Bash(prompt: run database migrations)
   · Bash(prompt: run tests)
   · Bash(prompt: run development server for testing)
