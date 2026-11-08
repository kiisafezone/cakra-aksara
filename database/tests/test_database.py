from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from uail_db.database import Base
from uail_db.models import Tenant, Memory, MemoryVersion
from uail_db.repositories import MemoryRepository

def test_memory_create_update_and_version_conflict():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        tenant = Tenant(name="Test", slug="test")
        session.add(tenant)
        session.commit()

        repo = MemoryRepository(session)
        memory = repo.create(
            tenant_id=tenant.id, owner_user_id=None,
            content="Initial", category="project"
        )
        assert memory.current_version == 1

        updated = repo.update(
            tenant_id=tenant.id, memory_id=memory.id,
            content="Updated", expected_version=1, reason="correction"
        )
        assert updated.current_version == 2

        versions = list(session.scalars(
            select(MemoryVersion).where(MemoryVersion.memory_id == memory.id)
        ))
        assert [v.version_number for v in versions] == [1, 2]

        try:
            repo.update(
                tenant_id=tenant.id, memory_id=memory.id,
                content="Stale update", expected_version=1
            )
            assert False, "expected version conflict"
        except ValueError as exc:
            assert "version conflict" in str(exc)

def test_tenant_scoped_memory_lookup():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        t1 = Tenant(name="One", slug="one")
        t2 = Tenant(name="Two", slug="two")
        session.add_all([t1, t2])
        session.commit()
        repo = MemoryRepository(session)
        memory = repo.create(
            tenant_id=t1.id, owner_user_id=None,
            content="Private", category="note"
        )
        assert repo.get(tenant_id=t2.id, memory_id=memory.id) is None
