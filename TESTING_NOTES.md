# Testing Notes

Quick capture of issues, changes, and updates during manual testing.

## Active Issues

### Critical
<!-- High-impact bugs that block core functionality -->
- [x] Broken call Managment button - [Found: 2026-01-07] [Area: applications]
  - Steps to reproduce: as a ReDIB coordinator create call call, save it, go back to portal's dashoard main page and select the 'Call Managment' tab on the sidebar
  - Expected: shows a page with the existing calls.
  - Actual: error 'NoReverseMatch at /calls/manage/'
  - Notes: if I login as a regular user (e.g. applicant) I only have the public calls tab in the dashboard and this does show the saved call without error.   
  - Error message: Reverse for 'call_detail' not found. 'call_detail' is not a valid view function or pattern name.

- [x] issues see in'http://127.0.0.1:8000/applications/1/step3/': adding more equipment in application. when filling out the application, these are initally 3 empty drop down boxes for selecting equipment and then giving hours.  It should be possible to add more, maybe a little plus sign at the bottom.
- [x] Multiple issues with help text in the application wizard
### High Priority
<!-- Important issues that should be fixed soon -->
- [ ] Profile page not found - [Found: 2026-01-07] [Area: ]
  - Steps to reproduce: at any dashboard page you can click the top right corrner with a button labaled as the users name to get a drop down of options, one is profile, that page does not exist.  
  - Expected: some page that lets yo uchange to users basic info like name, orca id, maybe email preferences
  - Actual: page not found
  - Notes: we could just remove the button all together.

### Medium/Low
<!-- Minor issues, cosmetic problems, or nice-to-have fixes -->

- [x] User cannot see their applications and the application status in the dashboard - [Found: 2026-01-08] [Area: dashboard/]
  - Steps to reproduce: login as user with submited applications and go to main dashboard (http://127.0.0.1:8000/dashboard/)
  - Expected: see browse (open) calls options(s) and see existing applicaitons option to click to see all applicatoins done and their status.
  - Actual: only see: browse (open) calls options(s)
  - Notes: ...

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
