# ReDIB COA Portal

The web portal that runs **Competitive Open Access (COA)** calls for
[ReDIB](https://www.redib.net) (Red Distribuida de Imagen Biomédica), Spain's
distributed biomedical imaging infrastructure. Researchers apply for time on
imaging instruments across ReDIB's nodes, and the portal carries each
application through its whole life: call announcement, the application
wizard, node feasibility review, blind scoring by evaluators, per-node
resolution, the applicant's accept/decline, hand-off to the node, and
publication follow-up. It replaced a workflow run by email.

It is a small Django app for a small group of users: the ReDIB coordinator,
the node coordinators at each node, a pool of evaluators, and the applicants. It is
live at `portal.redib.net`.

## Quick start (development)

```bash
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py setup_localtest3_database --reset --yes   # sandbox data; every password is testpass123
python manage.py runserver                                  # log in at http://127.0.0.1:8000 as coordinator@test.redib.net
```

The full walkthrough, with the test accounts and optional Docker setup, is
[docs/QUICKSTART.md](docs/QUICKSTART.md). Run the tests with
`python manage.py test tests reports` ([docs/TESTING.md](docs/TESTING.md)).

## Where to look

**Start at [docs/README.md](docs/README.md)**, the index of all documentation.
The most-used entry points:

| If you want to… | Read |
|---|---|
| Use the portal as an applicant, evaluator, node coordinator or coordinator | [docs/USER_GUIDE.md](docs/USER_GUIDE.md) |
| Run the app locally | [docs/QUICKSTART.md](docs/QUICKSTART.md) |
| Understand how the code is organised | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Find a command, a script, or a day-to-day dev workflow | [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) |
| Run or extend the tests | [docs/TESTING.md](docs/TESTING.md) |
| Configure environment variables or load reference data | [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md) |
| Edit the reference TSV files | [data/README.md](data/README.md) |
| Deploy or operate the production server | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |
| See what is planned or known-broken | [docs/developer/backlog.md](docs/developer/backlog.md) |

[CLAUDE.md](CLAUDE.md) holds the working conventions for Claude Code sessions,
and is a quick orientation for humans too.

## Tech stack

| Component | Development | Production |
|-----------|------------|------------|
| Runtime | Python 3.11+ in a venv | Docker Compose (Python 3.11 image) |
| Web | `manage.py runserver` | Gunicorn behind Caddy (automatic TLS) |
| Database | SQLite | PostgreSQL 15 |
| Background jobs | Run inline (`CELERY_TASK_ALWAYS_EAGER`) | Celery 5 worker and beat, Redis 7 broker |
| Email | Console (printed to the terminal) | SMTP |
| Frontend | Django templates, HTMX, Alpine.js, Bootstrap 5 | same |
| Auth | django-allauth (email login, verified addresses) | same |
| PDFs / spreadsheets | WeasyPrint / openpyxl | same |

## Project layout

```
redib/           Django project: settings, URLs, Celery app and beat schedule
core/            User, UserRole, Organization, Node, Equipment; dashboards, profile, middleware
calls/           Calls and their equipment; public call pages and consult requests
applications/    Application wizard, feasibility review, resolution, acceptance, PDF export
evaluations/     Evaluator assignment and blind scoring (6 criteria, 0-2 each)
access/          Access tracking, completion and publication follow-up
communications/  Database-stored email templates, send task, email log
reports/         Statistics, Excel export, per-call resolution table
newsletters/     ReDIB HTML newsletters served as portal pages
templates/       All page templates
static/          CSS and images
data/            Reference TSVs loaded by the populate_redib_* commands
scripts/         Backup, role-drift check, dress-rehearsal harness, worktree helper
docker/          Container entrypoint and Caddyfile
tests/           The test suite (run as: manage.py test tests reports)
docs/            All documentation
```

## License

Copyright (C) 2026 Ryan Tasseff

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version. See [LICENSE](LICENSE) for the full text.

The AGPL specifically covers network use: anyone who runs a modified version
of this software as a network service must make their modified source
available to its users.

## Contact

ReDIB Network: [info@redib.net](mailto:info@redib.net)
