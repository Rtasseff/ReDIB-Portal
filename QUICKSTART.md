# ReDIB COA Portal - Quick Start Guide

## What Has Been Built

A complete Django-based Competitive Open Access (COA) management system with:

### Core Features Implemented
- **Complete data model** with 15+ models across 7 Django apps
- **Role-based access control** with 5 user types (Applicant, Node Coordinator, Evaluator, Coordinator, Admin)
- **Application workflow** with 13 application states
- **Evaluation system** with 5 scoring criteria (1-5 scale)
- **Django admin interfaces** for all models with advanced filtering and search
- **Docker configuration** for production deployment
- **Celery + Redis** setup for background tasks and scheduled jobs
- **Email system** configuration (console backend for development)
- **Audit trail** using django-simple-history

### Technology Stack
- Django 5.0 + Python 3.11
- PostgreSQL 15 (or SQLite for local dev)
- Redis 7 + Celery 5.6
- Bootstrap 5 + HTMX + Alpine.js
- django-allauth for authentication

## Current Status

### ✅ Completed
1. Git repository initialized
2. Virtual environment with all dependencies
3. Django project with modular app structure
4. All data models implemented and migrated
5. Django admin interfaces registered
6. Docker and Docker Compose configured
7. Base templates and static files
8. Initial git commit created

### 📋 Ready for Development
The following are ready to be implemented next:

1. **Frontend views and forms**
   - Application submission wizard
   - User dashboards for each role
   - Evaluation forms
   - Call management interface

2. **Email templates and automation**
   - 12+ email templates per design
   - Celery tasks for notifications
   - Scheduled reminders

3. **Reporting module**
   - Ministry reports
   - Node statistics
   - Equipment utilization
   - Publication tracking

4. **API endpoints** (optional)
   - REST API for external integrations
   - Mobile app support

## How to Use

### Local Development

1. **Activate virtual environment**
   ```bash
   source venv/bin/activate
   ```

2. **Run development server**
   ```bash
   python manage.py runserver
   ```

3. **Access the application**
   - Homepage: http://localhost:8000
   - Admin: http://localhost:8000/admin
   - Accounts: http://localhost:8000/accounts/login

4. **Create a superuser**
   ```bash
   python manage.py createsuperuser
   ```

### Using Docker (Production-like Environment)

1. **Start all services**
   ```bash
   docker compose up -d
   ```

2. **Run migrations**
   ```bash
   docker compose exec web python manage.py migrate
   ```

3. **Create superuser**
   ```bash
   docker compose exec web python manage.py createsuperuser
   ```

4. **View logs**
   ```bash
   docker compose logs -f web
   ```

5. **Stop services**
   ```bash
   docker compose down
   ```

## Initial Data Setup

After creating a superuser, use the Django admin to set up:

1. **Create the 4 ReDIB Nodes**
   - CICbiomaGUNE (code: CICBIO)
   - BioImaC (code: BIOIMAC)
   - Hospital La Fe (code: LAFE)
   - CNIC (code: CNIC)

2. **Add Equipment** to each node
   - MRI scanners (7T, 3T, 1T)
   - PET-CT systems
   - Cyclotrons
   - Other imaging equipment

3. **Create Organizations**
   - Universities
   - Research centers
   - Hospitals

4. **Create Users** and assign roles
   - Node coordinators for each node
   - Evaluators (10+ external experts)
   - ReDIB network coordinator

5. **Create a test Call**
   - Set dates
   - Allocate equipment hours
   - Publish to make it available

## Project Structure

```
ReDIB-Portal/
├── core/               # Users, organizations, nodes, equipment
│   ├── models.py       # Organization, Node, Equipment, User, UserRole
│   └── admin.py
├── calls/              # Call management
│   ├── models.py       # Call, CallEquipmentAllocation
│   └── admin.py
├── applications/       # Application workflow
│   ├── models.py       # Application, RequestedAccess, FeasibilityReview
│   └── admin.py
├── evaluations/        # Evaluation system
│   ├── models.py       # Evaluation
│   └── admin.py
├── access/             # Access grants and publications
│   ├── models.py       # AccessGrant, Publication
│   └── admin.py
├── communications/     # Email system (to be implemented)
├── reports/            # Reporting module (to be implemented)
├── templates/          # HTML templates
│   ├── base.html
│   └── home.html
├── static/             # CSS, JS, images
│   └── css/main.css
├── redib/              # Django project settings
│   ├── settings.py     # All configuration
│   ├── celery.py       # Celery configuration
│   └── urls.py
├── docker-compose.yml      # Production Docker setup
├── docker-compose.dev.yml  # Development Docker setup
├── Dockerfile
├── requirements.txt
└── README.md
```

## Next Steps

1. **Develop frontend views**
   - Start with the home page and call listing
   - Implement application submission form
   - Create dashboards for each user role

2. **Implement email system**
   - Create email templates
   - Set up Celery tasks
   - Configure SMTP settings

3. **Add reporting**
   - Design report templates
   - Implement export functionality (PDF, Excel)

4. **Testing**
   - Write unit tests for models
   - Integration tests for workflows
   - User acceptance testing

5. **Deploy to production**
   - Set up IONOS VPS
   - Configure domain and SSL
   - Set up backups

## Key Design Decisions

1. **Email-based authentication** - Users log in with email, not username
2. **Modular apps** - Each major feature in its own Django app for maintainability
3. **Docker-first deployment** - All services containerized for easy deployment
4. **Admin-heavy initial release** - Django admin provides immediate functionality
5. **Audit trail** - All models have change history via django-simple-history

## Troubleshooting

### Issue: Database connection errors
- **Solution**: Make sure PostgreSQL is running (via Docker or locally)
- For local dev, use SQLite: `DATABASE_URL=sqlite:///db.sqlite3` in `.env`

### Issue: Celery tasks not running
- **Solution**: Start Celery worker: `celery -A redib worker -l info`
- And Celery beat: `celery -A redib beat -l info`

### Issue: Static files not loading
- **Solution**: Run `python manage.py collectstatic`
- Make sure `STATIC_ROOT` directory exists

### Issue: django-allauth deprecation warnings
- **Solution**: These are warnings about newer config syntax
- Update settings.py to use new ACCOUNT_LOGIN_METHODS format (optional)
- Does not affect functionality

## Support

For questions about the system design, see `redib-coa-system-design.md`

For Django help, see https://docs.djangoproject.com/

For deployment help, refer to the Django deployment checklist:
https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/
