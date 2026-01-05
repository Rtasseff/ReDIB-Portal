# Testing Notes

Quick capture of issues, changes, and updates during manual testing.

## Active Issues

### Critical
<!-- High-impact bugs that block core functionality -->

### High Priority
<!-- Important issues that should be fixed soon -->

### Medium/Low
<!-- Minor issues, cosmetic problems, or nice-to-have fixes -->
- [ ] Node director - [Found: 2026-01-05] [Area: applications]
  - module 'core' under models.py in class Node
  - Notes: as of now their is a required director with a many (directors) to one (node) relationship.
We may not want to require, or even record, this as from the pov of the COA portal the director may not be relevant - no action.
A manager/adminstrator or coordinator role may be more appropriate,
with the action being emailed for fiesability and ultimate recording of hours used.

## Feature Ideas / Enhancements
<!-- Ideas for improvements or new features discovered during testing -->

## Questions / Clarifications Needed
<!-- Questions about expected behavior or design decisions -->

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
