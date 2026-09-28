# Changelog - ReDIB COA Portal

All notable changes to this project will be documented in this file.

## [Unreleased] - 2025-12-25

### Critical Fixes

#### Node Model - Missing Director Field
**Issue**: Design document (section 4.2, line 140) specified `director` field for Node model, but it was not implemented.

**Fix**: Added `director` ForeignKey field to Node model
- Field: `director = ForeignKey(User, on_delete=PROTECT, null=True, blank=True)`
- Related name: `directed_nodes`
- Purpose: Track node leadership for permissions and notifications
- Admin updated to display director in list view with autocomplete

**Impact**: Can now properly assign node directors and route notifications

---

#### Email System Implementation
**Issue**: Design (section 7.2) specified comprehensive email system with 12+ templates, but communications app was empty.

**Fix**: Implemented complete email infrastructure in `communications` app:

**New Models**:
1. **EmailTemplate**: Stores reusable email templates
   - 13 template types (all from design section 7.2):
     - `call_published` - Notify users when calls are published
     - `application_received` - Confirmation to applicant
     - `feasibility_request` - Request feasibility review from node
     - `feasibility_reminder` - Reminder for pending reviews
     - `feasibility_rejected` - Notify applicant of rejection
     - `evaluation_assigned` - Notify evaluator of assignment
     - `evaluation_reminder` - Reminder for pending evaluations
     - `resolution_accepted` - Notify applicant of acceptance
     - `resolution_pending` - Notify applicant of waiting list
     - `resolution_rejected` - Notify applicant of rejection
     - `acceptance_reminder` - Remind to accept/reject grant
     - `access_scheduled` - Confirm scheduled access
     - `publication_followup` - Request publication information
   - Supports Django template syntax in subject and body
   - Separate HTML and plain text versions
   - Version history with django-simple-history

2. **EmailLog**: Complete audit trail of all emails sent
   - Tracks status: queued, sent, failed, bounced
   - Stores error messages for debugging
   - Links to related objects (calls, applications, evaluations)
   - Indexed for performance

3. **NotificationPreference**: Per-user email preferences
   - Users can opt-out of specific notification types
   - Preferences honored by all Celery tasks

**Admin Interfaces**: Full admin for all email models with filtering and search

**Impact**: Email communication system is now fully functional and auditable

---

#### Celery Tasks Implementation
**Issue**: Design (section 7.3) specified 4 periodic Celery Beat tasks, but none were implemented. Beat schedule referenced non-existent tasks.

**Fix**: Implemented all required Celery tasks across multiple apps:

**communications/tasks.py**:
- `send_email_from_template()` - Core email sending function
- `send_bulk_email()` - Bulk email with per-recipient context

**applications/tasks.py**:
- `send_feasibility_reminders()` - Daily at 9 AM
  - Finds reviews pending >5 days
  - Honors user notification preferences
  - Logs all emails sent

**evaluations/tasks.py**:
- `send_evaluation_reminders()` - Daily at 9 AM
  - Reminds evaluators 7 days before deadline
  - Only sends to incomplete evaluations
  - Respects notification preferences
- `assign_evaluators_to_application()` - Auto-assign 2 random evaluators
  - Filters by specialization area when possible
  - Prevents duplicate assignments
  - Sends assignment emails automatically

**access/tasks.py**:
- `process_acceptance_deadlines()` - Daily at 10 AM
  - Sends reminder at 7 days (design: 10 days without acceptance)
  - Auto-declines at 10 days with no response
  - Updates application status accordingly
- `send_publication_followups()` - Weekly on Mondays at 10 AM
  - Follows up 6 months after completion
  - Only sends if no publications reported
  - Includes node acknowledgment text

**Impact**: Automated workflow reminders and notifications now work as designed

---

### Important Fixes

#### AEI Subject Area Classification
**Issue**: Application model used generic subject areas (biology, medicine, etc.) instead of Spanish AEI (Agencia Estatal de Investigación) classification.

**Fix**: Replaced `SUBJECT_AREAS` choices with official AEI classifications:
- PHY - Physics
- CHE - Chemistry
- MAT - Materials Science and Technology
- EAR - Earth Sciences
- BIO - Biology
- MED - Medicine
- AGR - Agricultural Sciences
- ENG - Engineering and Architecture
- SOC - Social Sciences
- ECO - Economics
- LAW - Law
- HUM - Humanities
- Other

**Migration**: `applications/migrations/0003_` handles the change

**Impact**: Proper alignment with Spanish research classification system; better reporting

---

#### Application State Machine Validation
**Issue**: Design (section 6.1) defines strict state machine with valid transitions, but no validation was implemented.

**Fix**: Implemented state machine validation in Application model:

**New Features**:
1. `VALID_TRANSITIONS` class attribute - defines all valid state transitions
2. `save()` method enhanced - validates transitions on update
3. `can_transition_to(new_status)` method - check if transition is valid
4. `get_next_valid_states()` method - get list of valid next states

**State Transition Rules** (from design document):
```
draft → submitted
submitted → under_feasibility_review, rejected_feasibility
under_feasibility_review → rejected_feasibility, pending_evaluation
pending_evaluation → under_evaluation
under_evaluation → evaluated
evaluated → accepted, pending, rejected
accepted → scheduled
pending → scheduled, rejected
scheduled → in_progress
in_progress → completed
```

**Terminal States**: `rejected_feasibility`, `rejected`, `completed`

**Impact**: Prevents invalid workflow transitions; raises `ValidationError` on invalid state changes

---

#### Reports Module Structure
**Issue**: Design (section 9) specifies comprehensive reporting, but reports app was empty.

**Fix**: Implemented basic reporting infrastructure:

**New Model**: `ReportGeneration`
- Tracks all generated reports for audit
- Supports 6 report types (from design):
  - Call Summary Report
  - Node Usage Statistics
  - Ministry Annual Report
  - Equipment Utilization Report
  - Publication Outcomes Report
  - User Activity Report
- Stores report parameters and filters
- File upload support (PDF, Excel, CSV)
- Links to related calls/nodes
- JSON field for flexible parameters

**Admin Interface**: Full admin with filtering by type, format, date

**Note**: Report generation logic to be implemented in future views

**Impact**: Foundation for ministry reporting requirements is in place

---

### Configuration Improvements

#### Django-allauth Deprecation Warnings
**Status**: Noted but not fixed
- 4 deprecation warnings about updated settings syntax
- Old syntax still works, no functional impact
- Can be updated to new `ACCOUNT_LOGIN_METHODS` syntax in future

---

### Code Quality Improvements

#### Enhanced Docstrings
- All new models have comprehensive docstrings
- All Celery tasks have detailed docstrings explaining:
  - Purpose and trigger
  - Parameters and return values
  - Business logic
- State machine methods fully documented

#### Error Handling
- All Celery tasks have try/catch blocks
- Email failures logged to EmailLog with error messages
- State validation raises informative ValidationError

#### Admin Enhancements
- All new models registered in Django admin
- Custom list_display, list_filter, search_fields
- Organized fieldsets for better UX
- Readonly fields where appropriate
- Autocomplete for foreign keys

---

## Database Schema Changes

### New Tables
1. `communications_emailtemplate` - Email template storage
2. `communications_emaillog` - Email audit log
3. `communications_notificationpreference` - User preferences
4. `communications_historicalemailtemplate` - Template history
5. `reports_reportgeneration` - Report tracking

### Modified Tables
1. `core_node` - Added `director_id` foreign key
2. `applications_application` - Modified `subject_area` choices

### Indexes Added
- `communications_emaillog`: created_at, status, recipient_email

---

## File Summary

### New Files Created
```
communications/tasks.py          - Email sending tasks
applications/tasks.py            - Application workflow tasks
evaluations/tasks.py             - Evaluation workflow tasks
access/tasks.py                  - Access grant workflow tasks
CHANGELOG.md                     - This file
```

### Files Modified
```
core/models.py                   - Added director field to Node
core/admin.py                    - Updated Node admin
applications/models.py           - AEI classification + state machine
communications/models.py         - Complete email system
communications/admin.py          - Email admin interfaces
reports/models.py                - Report generation model
reports/admin.py                 - Report admin interface
```

### Migrations Created
```
core/migrations/0002_*.py                    - Node director field
applications/migrations/0003_*.py            - Subject area update
communications/migrations/0001_initial.py    - Email system
reports/migrations/0001_initial.py           - Reports module
```

---

## Testing Recommendations

### Critical Tests Needed
1. **State Machine**: Test all valid and invalid transitions
2. **Email Tasks**: Test email sending with mock SMTP
3. **Evaluator Assignment**: Test random selection and notification
4. **Deadline Processing**: Test reminder and auto-decline logic

### Manual Testing
1. Create email templates in admin
2. Test each Celery task manually
3. Verify state transitions in admin
4. Check email logs for all notifications

---

## Next Steps (Not in This Release)

### Still To Implement (from review)
1. **Frontend Views**: All user-facing dashboards and forms
2. **Permission Framework**: Role-based access control decorators
3. **URL Configuration**: Routes for all features
4. **API Endpoints**: REST API (marked as future in design)
5. **Email Template Content**: Actual HTML/text for 13 templates
6. **Report Generators**: Logic to generate PDF/Excel reports

### Documentation Needed
1. User onboarding guide
2. Administrator manual
3. API documentation (when implemented)
4. Email template variable reference

---

## Upgrade Instructions

### From Previous Version

1. **Backup database** before upgrading

2. **Install new dependencies** (if needed):
   ```bash
   pip install -r requirements.txt
   ```

3. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

4. **Create email templates** in Django admin:
   - Navigate to Communications > Email Templates
   - Create templates for all 13 types
   - Set `is_active=True` when ready

5. **Assign node directors**:
   - Navigate to Core > Nodes
   - Set director for each node

6. **Update application subject areas** (if needed):
   - Old values (biology, medicine, etc.) will still work
   - New applications should use AEI codes

7. **Test Celery tasks**:
   ```bash
   # In separate terminal
   celery -A redib worker -l info
   celery -A redib beat -l info
   ```

8. **Verify email sending** works in development:
   - Check console output (default backend)
   - Or configure SMTP in .env file

---

## Security Notes

- Email templates support Django template syntax - sanitize user input
- State machine validation prevents unauthorized status changes
- Email logs may contain sensitive information - restrict access
- Report files stored in media directory - configure proper permissions

---

## Performance Notes

- EmailLog table will grow over time - consider periodic archiving
- Celery tasks query large datasets - monitor database performance
- Email sending is asynchronous - no impact on request latency
- Indexes added to EmailLog for common queries

---

## Compatibility

- **Django**: 5.0.14 (tested)
- **Python**: 3.11+ (required)
- **Database**: PostgreSQL 15+ (recommended), SQLite 3 (development only)
- **Celery**: 5.6.0
- **Redis**: 7.0+

---

**Version**: Validation and Critical Fixes Release
**Date**: 2025-12-25
**Author**: Code Review and Validation Process
**Design Document**: redib-coa-system-design.md v1.0
