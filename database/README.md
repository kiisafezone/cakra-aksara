# UAIL Database Starter v0.3.0

Tenant-scoped persistence foundation for the Universal AI Intelligence Layer.

## Stack
- Python 3.11+, SQLAlchemy 2.x, Alembic
- SQLite for local mode; PostgreSQL for server mode
- pytest

## Quick start
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
pytest -q
```
Set `DATABASE_URL`, for example:
`postgresql+psycopg://uail:uail@localhost:5432/uail`

## v0.3.0 additions
- ORM `before_flush` tenant-consistency guard validates tenant ownership of known foreign-key references.
- Generic allow-listed `TenantRepository` provides tenant-filtered get/list/create/update/delete.
- `MemoryRepository` stores immutable version snapshots and leaves transaction ownership to services.
- `MemoryService` enforces private-memory ownership, optimistic version checks, soft deletion, audit events, and commits at service boundaries.
- `EntityService` provides a transaction-owning service facade for other allow-listed entities.
- Tests cover cross-tenant reference rejection, cross-tenant reads, owner checks, version conflicts, and repository filtering.

## Important security boundaries
- The tenant guard protects ORM writes only. Raw SQL, bulk SQL statements, and external writers bypass ORM events.
- Repositories scope every read/write by `tenant_id`; service authorization is still required for private resources and role-based actions.
- PostgreSQL Row-Level Security is recommended as defense in depth. SQLite has no equivalent RLS.
- For high-assurance production, add composite tenant foreign keys in a dedicated migration, RLS policies, API authentication/authorization, and security review.
- The current Alembic history is a prototype baseline: `0001` creates the metadata schema and later revisions are staged placeholders. Do not treat the migration history as a mature incremental production history.
- PostgreSQL integration tests require a separately provisioned test database and have not been run in this package build.
