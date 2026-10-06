# Library Management System

## Overview

A production-structured REST API for searchable library catalogs, members, circulation, copy availability, and overdue reporting.

## Features

- Member registration, login/logout, and admin/librarian/member roles
- Catalog CRUD with ISBN uniqueness, search, availability filters, sorting, and pagination
- Atomic borrowing and returning with row locks, active-loan uniqueness, copy-count invariants, and member ownership
- Member loan history, overdue report, dashboard, audit timestamps, activity records, migrations, seeds, Docker, and CI

## Technology Stack

Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2, PostgreSQL 17, PyJWT, Argon2, pytest, Ruff, pip-audit, Docker.

## Requirements

Python 3.12+ and PostgreSQL 15+, or Docker with Compose.

## Installation

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
copy .env.example .env
```

## Environment Variables

Required: `DATABASE_URL` and a random `JWT_SECRET` of at least 32 characters. Optional: `JWT_EXPIRY_MINUTES` and comma-separated `ALLOWED_ORIGINS`. Never deploy example credentials.

## Database Setup

```bash
python -m app.migrate
python -m app.seed
```

Docker: `docker compose up -d db`, followed by `docker compose --profile tools run --rm migrate` and `docker compose --profile tools run --rm seed`.

## Running the Application

Run `uvicorn app.main:app --reload` and open `http://localhost:8000/docs`. With Docker, run `docker compose up --build api` after migration.

## Running Tests

```bash
ruff check .
pytest -q
pip-audit
```

## Default Development Accounts

Seed-only accounts: admin `admin@example.com` / `AdminPassword123!`; librarian `librarian@example.com` / `LibrarianPassword123!`; member `member@example.com` / `MemberPassword123!`. Change them outside disposable local development.

## API Endpoints

Auth: `POST /api/auth/register|login|logout`. Staff: `POST /api/staff`. Books: `GET/POST /api/books`, `GET/PUT /api/books/{id}`. Loans: `GET/POST /api/loans`, `PATCH /api/loans/{id}/return`. Reporting: `GET /api/reports/overdue`, `GET /api/dashboard`. Health: `GET /health`.

## Folder Structure

`app/` contains API, schemas, services, repositories, models, auth, database, and configuration. `migrations/` owns PostgreSQL schema changes. `tests/` covers circulation rules. `.github/workflows/` provides PostgreSQL CI.

## Architecture

Routes handle HTTP; services enforce circulation transactions and authorization; repositories build catalog queries; schemas whitelist I/O; models and migrations enforce inventory invariants.

## Security Notes

Argon2 passwords, short-lived revocable JWT sessions, rate-limited timing-equalized login, server-side RBAC and ownership, parameterized queries, row locks, partial unique constraints, bounded validation/pagination, CORS allow-listing, generic server errors, and no credential/hash exposure.

## Known Limitations

Reservations, fines/payments, barcode devices, multi-branch inventory, notifications, password recovery, and immutable external auditing are outside scope. The login limiter is per process. Production deployments should add Redis/gateway throttling and scheduled overdue notifications.
