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

- [ ] Inconsistant application number - [Found: 2026-01-09] [Area: evaluations]
  - Steps to reproduce: go to assign evaluators (http://127.0.0.1:8000/evaluations/assign/), see 'Recent Calls Needing Attention' column 'Total Apps' for a specific call. Note that number. Then note the number in call managment (http://127.0.0.1:8000/calls/manage/) table under column 'Applications'  
  - Expected: Should be the same 
  - Actual: Can be different
  - Notes: Call managment may be ignoring drafts, I think this is a good pattern to repeate as coordinators, evaluators and so on do not need to know or worry about draft applicaitons.  It is just extra clutter.

- [ ] Different buttons, same result - [Found: 2026-01-09] [Area: evaluations]
  - Steps to reproduce: go to assign evaluators (http://127.0.0.1:8000/evaluations/assign/), see the table 'Recent Calls Needing Attention' and the table 'All Calls'. Note the column called 'Actions', you will see different button types: 'View Details' and 'Manage' click the different buttons for the same call (http://127.0.0.1:8000/evaluations/assign/call/3/)
  - Expected: Different button types infer different actions.  since the actions are the same, I would expect the next view to be differnt depending on if I click 'View Details' vs 'Manage'   
  - Actual: we see the same scree (http://127.0.0.1:8000/evaluations/assign/call/3/) regardless of manage or view details.
  - Notes: given the functionality in the view that is activated by these buttons, I suggest jsut calling it 'Assign' 

## Feature Ideas / Enhancements
<!-- Ideas for improvements or new features discovered during testing -->
- [ ] Display fiesability comments [Found: 2026-01-09] [Area: applications]
  - Notes: We should display the comments from the fiesability review (if they are avlaible) on the applicaiton details (http://127.0.0.1:8000/applications/5/) whenever they are viewed, even if viewed by the user with applicant role (assuming they were the applicant of that application).   

- [ ] Need additional steps and aprovals for assiging evaluators [Found: 2026-01-09] [Area: evaluations]
  - Notes: Logged in as coordinator. The functionality to auto-assign evaluators to a call (http://127.0.0.1:8000/evaluations/assign/call/3/) should do the assignment theoretically, then show the assignment to the user and then ask for approval.
  - Details: maybe the assignment process for a call can open a view wehre we see each applicaiton and under each is a drop down to select a reviewer and under that is a + button to add another evaluator and a way to remove those that have been added (same as we do for assinging equipment in the applicaiton phase). SO there would be this list off calls each with a list of evaluators. At the very bottom of this view woould be an 'Assign' button to offically assign the chosen evaluaotrs to the coresponding applications in the database, and then do the other steps (like email the evaluaotrs). This easily provides a manual way to assign. The random assignment could be changed to 'Auto-Suggest Evaluators' x number per application. This just picks the evaluators usind the existing logic and updates the view so the lists of apps with sub lists of evaluators.  There would still be a add and remove option under each evaluator sub list, which is exactly how the user can do a mannual change before excepting the suggestion by clicking the 'Assign' button. 
  - side note: I really like the current functinality where each application with evaluators in this view has a little eye in the 'Evaluators Assigned' column and this button lets you see the evaluator sub list. Lets keep that in the new view. 
  - final note: in the parenthasis next to the evaluator names (in the sub list under the applicaitons) you show the institute the evaluator is associated with.  Keep this but add there speciality if it exists (e.g., preclinical or clinical).      
## Questions / Clarifications Needed
<!-- Questions about expected behavior or design decisions -->
- [ ] Node director - [Found: 2026-01-05] [Area: applications]
  - module 'core' under models.py in class Node
  - Notes: as of now their is a required director with a many (directors) to one (node) relationship. We may not want to require, or even record, this as from the pov of the COA portal the director may not be relevant - no action. A manager/adminstrator or coordinator role may be more appropriate, with the action being emailed for fiesability and ultimate recording of hours used.



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
