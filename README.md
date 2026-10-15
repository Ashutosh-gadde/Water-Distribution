# Latur Municipal Corporation — Water Distribution System and Monitoring Portal

**Status: Stage 1 of 7 (foundation). Not ready for municipal use.**

## Implemented and tested (22 tests)
- Login, refresh-token rotation, logout (server-side session revocation), lockout after 5 failures
- Five internal roles with server-enforced permissions and role-rank limits
- Ward jurisdiction assignments with preserved history; ward access checks on the server
- Append-only audit log (ORM-enforced; add a PostgreSQL trigger/REVOKE before production)
- Alembic migration 0001 (verified up/down/up on SQLite)

## Not yet implemented
GIS map/import, schedules, sessions, complaints, notifications, reports, Marathi UI,
frontend app, MFA, PostgreSQL-specific testing (tests run on SQLite).

## Run tests
    cd backend && pip install -r requirements.txt && SECRET_KEY=x pytest

## Run with Docker
    cp .env.example .env     # set SECRET_KEY and POSTGRES_PASSWORD
    docker compose up --build
    docker compose exec backend python -m scripts.create_admin   # prompts for credentials
API docs: http://localhost:8000/docs · Health: /health

## Required municipal inputs (not invented here)
Verified boundaries, network assets, org structure and approval rules, logo,
SMS/email/WhatsApp credentials, sensor/SCADA access.
