"""Opt-in PostgreSQL integration tests using a disposable isolated schema."""

import os
import uuid

import pytest
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from uail_db.database import Base
from uail_db.models import (
    Memory,
    MemoryVersion,
    RequestRecord,
    Tenant,
    User,
)
from uail_db.repositories import MemoryRepository, TenantRepository
from uail_db.services import MemoryService


@pytest.fixture(scope="session")
def postgres_engine():
    database_url = os.getenv("TEST_DATABASE_URL")

    if not database_url:
        pytest.skip("TEST_DATABASE_URL belum diatur")

    url = make_url(database_url)

    if url.get_backend_name() != "postgresql":
        pytest.fail("TEST_DATABASE_URL harus menunjuk ke PostgreSQL")

    if not url.database:
        pytest.fail("Nama database pada TEST_DATABASE_URL wajib diisi")

    # Schema acak agar tidak menyentuh schema public atau schema aplikasi.
    schema = f"test_pg_{uuid.uuid4().hex}"

    admin_engine = create_engine(database_url, pool_pre_ping=True)
    test_engine = None

    try:
        with admin_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))

        test_engine = create_engine(database_url, pool_pre_ping=True)

        @event.listens_for(test_engine, "connect")
        def set_test_search_path(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute(f'SET search_path TO "{schema}"')
            cursor.close()

        Base.metadata.create_all(test_engine)

        yield test_engine

    finally:
        if test_engine is not None:
            test_engine.dispose()

        # Hanya schema acak yang dibuat fixture ini yang dihapus.
        with admin_engine.begin() as connection:
            connection.execute(
                text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
            )

        admin_engine.dispose()


@pytest.fixture
def pg_session(postgres_engine):
    factory = sessionmaker(
        bind=postgres_engine,
        expire_on_commit=False,
    )

    with factory() as session:
        yield session
        session.rollback()


def create_tenant_and_user(session, suffix):
    tenant = Tenant(
        name=f"PostgreSQL Test {suffix}",
        slug=f"postgres-test-{suffix}",
        settings={"integration_test": True},
    )
    session.add(tenant)
    session.flush()

    user = User(
        tenant_id=tenant.id,
        email=f"user-{suffix}@example.test",
        display_name="Integration Test",
    )
    session.add(user)
    session.commit()

    return tenant, user


def test_postgres_persists_tenant_and_json(pg_session):
    tenant, _ = create_tenant_and_user(
        pg_session,
        uuid.uuid4().hex[:12],
    )

    pg_session.expire_all()

    saved = pg_session.get(Tenant, tenant.id)

    assert saved is not None
    assert saved.settings == {"integration_test": True}


def test_postgres_enforces_tenant_scoped_repository(pg_session):
    suffix = uuid.uuid4().hex[:12]
    tenant_a, _ = create_tenant_and_user(pg_session, f"a-{suffix}")
    tenant_b, _ = create_tenant_and_user(pg_session, f"b-{suffix}")

    repo = TenantRepository(pg_session, RequestRecord)

    request = repo.create(
        tenant_id=tenant_a.id,
        request_type="postgres-integration",
    )
    pg_session.commit()

    assert repo.get(
        tenant_id=tenant_a.id,
        entity_id=request.id,
    ) is not None

    assert repo.get(
        tenant_id=tenant_b.id,
        entity_id=request.id,
    ) is None


def test_postgres_memory_service_and_version_history(pg_session):
    suffix = uuid.uuid4().hex[:12]
    tenant, user = create_tenant_and_user(pg_session, suffix)

    service = MemoryService(pg_session)

    memory = service.create(
        tenant_id=tenant.id,
        actor_user_id=user.id,
        content="PostgreSQL initial content",
        category="integration-test",
    )

    updated = service.update(
        tenant_id=tenant.id,
        actor_user_id=user.id,
        memory_id=memory.id,
        content="PostgreSQL updated content",
        expected_version=1,
    )

    assert updated.current_version == 2
    assert updated.content == "PostgreSQL updated content"

    versions = list(
        pg_session.scalars(
            select(MemoryVersion)
            .where(MemoryVersion.memory_id == memory.id)
            .order_by(MemoryVersion.version_number)
        )
    )

    assert [item.version_number for item in versions] == [1, 2]
    assert [item.content_snapshot for item in versions] == [
        "PostgreSQL initial content",
        "PostgreSQL updated content",
    ]


def test_postgres_rejects_stale_concurrent_update(postgres_engine):
    suffix = uuid.uuid4().hex[:12]
    factory = sessionmaker(
        bind=postgres_engine,
        expire_on_commit=False,
    )

    with factory() as setup_session:
        tenant = Tenant(
            name=f"Concurrent Test {suffix}",
            slug=f"concurrent-test-{suffix}",
        )
        setup_session.add(tenant)
        setup_session.commit()

        repo = MemoryRepository(setup_session)
        memory = repo.create(
            tenant_id=tenant.id,
            owner_user_id=None,
            content="Original",
            category="integration-test",
        )
        setup_session.commit()

        tenant_id = tenant.id
        memory_id = memory.id

    with factory() as session_a, factory() as session_b:
        repo_a = MemoryRepository(session_a)
        repo_b = MemoryRepository(session_b)

        assert repo_a.get(
            tenant_id=tenant_id,
            memory_id=memory_id,
        ).current_version == 1

        assert repo_b.get(
            tenant_id=tenant_id,
            memory_id=memory_id,
        ).current_version == 1

        repo_a.update(
            tenant_id=tenant_id,
            memory_id=memory_id,
            content="Updated by A",
            expected_version=1,
        )
        session_a.commit()

        with pytest.raises(ValueError, match="version conflict"):
            repo_b.update(
                tenant_id=tenant_id,
                memory_id=memory_id,
                content="Updated by B",
                expected_version=1,
            )

        session_b.rollback()

    with factory() as verify_session:
        saved = MemoryRepository(verify_session).get(
            tenant_id=tenant_id,
            memory_id=memory_id,
        )

        assert saved.current_version == 2
        assert saved.content == "Updated by A"
