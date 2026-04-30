# ReDIB COA Portal

Competitive Open Access (COA) management system for the [ReDIB](https://www.redib.net) (Red
Distribuida de Imagen Biomédica) distributed biomedical imaging network. Django web app that
automates the full COA lifecycle — from call publication through application, evaluation,
node-level resolution, hand-off, access tracking, and publication follow-up — replacing the
prior manual email-based workflow.

## Where to look

| If you want to… | Read |
|---|---|
| Run the app locally for development | [docs/QUICKSTART.md](docs/QUICKSTART.md) |
| Use the portal as an applicant, evaluator, node coordinator, or coordinator | [docs/USER_GUIDE.md](docs/USER_GUIDE.md) |
| Deploy or update the production VPS | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |
| Configure environment variables | [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md) |
| Add a feature or fix a bug | [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) |
| Run or extend the test suite | [docs/TESTING.md](docs/TESTING.md) |
| Edit the reference TSV files | [data/README.md](data/README.md) |
| Drop a new feature request or known issue | [docs/developer/backlog.md](docs/developer/backlog.md) |
| Browse all documentation | [docs/README.md](docs/README.md) |

## Tech stack

| Component | Development | Production |
|-----------|------------|------------|
| Runtime | Python 3.11 + venv | Docker Compose |
| Web | `manage.py runserver` | Gunicorn behind Caddy (auto-TLS) |
| Database | SQLite (auto-created) | PostgreSQL 15 |
| Cache / queue | In-process | Redis 7 + Celery 5 |
| Email | Console backend | SMTP |
| Frontend (both) | Django templates + HTMX + Alpine.js + Bootstrap 5 |
| Auth (both) | django-allauth |

## Project layout

```
redib/         # Django project (settings, celery)
core/          # User, UserRole, Organization, Node, Equipment + middleware/admin
calls/         # Call + per-equipment allocation
applications/  # 5-step wizard, feasibility, resolution, PDF export
evaluations/   # Assignment + blind scoring (6 criteria, 0–2)
access/        # Access tracking + publication tracking
communications/# DB-stored email templates + Celery send tasks
reports/       # Statistics dashboard + Excel export
templates/     # Django templates (every UI surface)
static/        # CSS, JS, images
data/          # Reference TSVs (loaded by populate_redib_* commands)
tests/         # Integration tests grouped by workflow phase
docs/          # All documentation (start at docs/README.md)
```

See [CLAUDE.md](CLAUDE.md) for the working-context conventions used by Claude Code.

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

ReDIB Network — [info@redib.net](mailto:info@redib.net)
