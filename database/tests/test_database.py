import pytest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from uail_db.database import Base
from uail_db.models import Tenant, MemoryVersion
from uail_db.repositories import MemoryRepository


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()


def test_memory_create_update_and_version_conflict(session):
    tenant = Tenant(name="Test", slug="test")
    session.add(tenant)
    session.commit()

    repo = MemoryRepository(session)
    memory = repo.create(
        tenant_id=tenant.id,
        owner_user_id=None,
        content="Initial",
        category="project",
    )

    assert memory.current_version == 1

    updated = repo.update(
        tenant_id=tenant.id,
        memory_id=memory.id,
        content="Updated",
        expected_version=1,
        reason="correction",
    )

    assert updated.current_version == 2

    versions = list(
        session.scalars(
            select(MemoryVersion).where(
                MemoryVersion.memory_id == memory.id
            )
        )
    )
    assert [v.version_number for v in versions] == [1, 2]

    with pytest.raises(ValueError, match="version conflict"):
        repo.update(
            tenant_id=tenant.id,
            memory_id=memory.id,
            content="Stale update",
            expected_version=1,
        )


def test_tenant_scoped_memory_lookup(session):
    t1 = Tenant(name="One", slug="one")
    t2 = Tenant(name="Two", slug="two")
    session.add_all([t1, t2])
    session.commit()

    repo = MemoryRepository(session)
    memory = repo.create(
        tenant_id=t1.id,
        owner_user_id=None,
        content="Private",
        category="note",
    )

    assert repo.get(
        tenant_id=t2.id,
        memory_id=memory.id,
    ) is None


def test_two_sessions_cannot_update_same_memory_version(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'concurrency.db'}")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as setup_session:
            tenant = Tenant(name="Concurrent", slug="concurrent")
            setup_session.add(tenant)
            setup_session.commit()

            repo = MemoryRepository(setup_session)
            memory = repo.create(
                tenant_id=tenant.id,
                owner_user_id=None,
                content="Original",
                category="project",
            )
            setup_session.commit()

            tenant_id = tenant.id
            memory_id = memory.id

        with Session(engine) as session_a, Session(engine) as session_b:
            repo_a = MemoryRepository(session_a)
            repo_b = MemoryRepository(session_b)

            # Kedua session membaca versi awal yang sama.
            assert repo_a.get(
                tenant_id=tenant_id, memory_id=memory_id
            ).current_version == 1

            assert repo_b.get(
                tenant_id=tenant_id, memory_id=memory_id
            ).current_version == 1

            # Session A berhasil memperbarui versi 1 menjadi 2.
            repo_a.update(
                tenant_id=tenant_id,
                memory_id=memory_id,
                content="Updated by A",
                expected_version=1,
            )
            session_a.commit()

            # Session B harus ditolak karena versi 1 sudah usang.
            with pytest.raises(ValueError, match="version conflict"):
                repo_b.update(
                    tenant_id=tenant_id,
                    memory_id=memory_id,
                    content="Updated by B",
                    expected_version=1,
                )

            session_b.rollback()

        with Session(engine) as verify_session:
            final_memory = MemoryRepository(verify_session).get(
                tenant_id=tenant_id,
                memory_id=memory_id,
            )
            assert final_memory.current_version == 2
            assert final_memory.content == "Updated by A"

    finally:
        engine.dispose()
