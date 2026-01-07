# Testing Notes

Quick capture of issues, changes, and updates during manual testing.

## Active Issues

### Critical
<!-- High-impact bugs that block core functionality -->
- [ ] Broken call Managment button - [Found: 2026-01-05] [Area: applications]
  - Steps to reproduce: as a ReDIB coordinator create call call, save it, go back to portal's dashoard main page and select the 'Call Managment' tab on the sidebar
  - Expected: shows a page with the existing calls.
  - Actual: error 'NoReverseMatch at /calls/manage/'
  - Notes: if I login as a regular user (e.g. applicant) I only have the public calls tab in the dashboard and this does show the saved call without error.   
  - Error message: Reverse for 'call_detail' not found. 'call_detail' is not a valid view function or pattern name.

Request Method: 	GET
Request URL: 	http://127.0.0.1:8000/calls/manage/
Django Version: 	5.0.14
Exception Type: 	NoReverseMatch
Exception Value: 	

Reverse for 'call_detail' not found. 'call_detail' is not a valid view function or pattern name.

Exception Location: 	/home/rtasseff/projects/ReDIB-Portal/venv/lib/python3.12/site-packages/django/urls/resolvers.py, line 851, in _reverse_with_prefix
Raised during: 	calls.views.coordinator_dashboard
Python Executable: 	/home/rtasseff/projects/ReDIB-Portal/venv/bin/python
Python Version: 	3.12.3
Python Path: 	

['/home/rtasseff/projects/ReDIB-Portal',
 '/home/rtasseff/projects/ReDIB-Portal',
 '/usr/lib/python312.zip',
 '/usr/lib/python3.12',
 '/usr/lib/python3.12/lib-dynload',
 '/home/rtasseff/projects/ReDIB-Portal/venv/lib/python3.12/site-packages']
  - 
### High Priority
<!-- Important issues that should be fixed soon -->
- [ ] Profile page not found - [Found: 2026-01-07] [Area: applications]
  - Steps to reproduce: at any dashboard page you can click the top right corrner with a button labaled as the users name to get a drop down of options, one is profile, that page does not exist.  
  - Expected: some page that lets yo uchange to users basic info like name, orca id, maybe email preferences
  - Actual: page not found
  - Notes: we could just remove the button all together.

### Medium/Low
<!-- Minor issues, cosmetic problems, or nice-to-have fixes -->


## Feature Ideas / Enhancements
<!-- Ideas for improvements or new features discovered during testing -->

## Questions / Clarifications Needed
<!-- Questions about expected behavior or design decisions -->
- [ ] Node director - [Found: 2026-01-05] [Area: applications]
  - module 'core' under models.py in class Node
  - Notes: as of now their is a required director with a many (directors) to one (node) relationship.
We may not want to require, or even record, this as from the pov of the COA portal the director may not be relevant - no action.
A manager/adminstrator or coordinator role may be more appropriate,
with the action being emailed for fiesability and ultimate recording of hours used.

## Completed / Resolved
<!-- Resolved issues - move items here when fixed -->

---

## Usage Notes

**Adding a new issue:**
```markdown
- [ ] Brief description - [Found: 2026-01-05] [Area: applications]
  - Steps to reproduce: ...
  - Expected: ...
  - Actual: ...
  - Notes: ...
```

**Areas:** applications, calls, evaluations, access, communications, reports, core, auth

**Moving to Completed:**
```markdown
- [x] Issue description - [Resolved: 2026-01-05]
  - Solution: ...
```
