import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from uail_db.database import Base
from uail_db.models import Tenant, User, RequestRecord, ContextItem, Memory, MemoryVersion
from uail_db.repositories import TenantRepository
from uail_db.services import MemoryService, TenantAccessError

@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as s:
        yield s
    engine.dispose()

def tenants(session):
    a = Tenant(name="A", slug="a")
    b = Tenant(name="B", slug="b")
    session.add_all([a, b]); session.flush()
    ua = User(tenant_id=a.id, email="a@example.test")
    ub = User(tenant_id=b.id, email="b@example.test")
    session.add_all([ua, ub]); session.commit()
    return a, b, ua, ub

def test_tenant_guard_rejects_cross_tenant_user_reference(session):
    a, b, ua, ub = tenants(session)
    req = RequestRecord(tenant_id=a.id, user_id=ub.id, request_type="test")
    session.add(req)
    with pytest.raises(ValueError, match="cross-tenant"):
        session.flush()
    session.rollback()

def test_tenant_guard_rejects_cross_tenant_request_context(session):
    a, b, ua, ub = tenants(session)
    req = RequestRecord(tenant_id=b.id, request_type="test")
    session.add(req); session.commit()
    ctx = ContextItem(tenant_id=a.id, request_id=req.id, content="secret")
    session.add(ctx)
    with pytest.raises(ValueError, match="cross-tenant"):
        session.flush()
    session.rollback()

def test_tenant_repository_cannot_read_other_tenant(session):
    a, b, ua, ub = tenants(session)
    svc = MemoryService(session)
    m = svc.create(tenant_id=b.id, actor_user_id=ub.id, content="private", category="fact")
    assert TenantRepository(session, Memory).get(tenant_id=a.id, entity_id=m.id) is None

def test_memory_service_enforces_owner_and_versions(session):
    a, b, ua, ub = tenants(session)
    svc = MemoryService(session)
    m = svc.create(tenant_id=a.id, actor_user_id=ua.id, content="v1", category="fact")
    with pytest.raises(TenantAccessError):
        svc.get(tenant_id=a.id, actor_user_id=ub.id, memory_id=m.id)
    m2 = svc.update(tenant_id=a.id, actor_user_id=ua.id, memory_id=m.id,
                    content="v2", expected_version=1)
    assert m2.current_version == 2
    versions = list(session.scalars(select(MemoryVersion).where(MemoryVersion.memory_id == m.id)))
    assert [v.version_number for v in versions] == [1, 2]
    with pytest.raises(ValueError, match="version conflict"):
        svc.update(tenant_id=a.id, actor_user_id=ua.id, memory_id=m.id,
                   content="stale", expected_version=1)

def test_generic_repository_is_tenant_scoped_and_validates_fields(session):
    a, b, ua, ub = tenants(session)
    repo = TenantRepository(session, RequestRecord)
    item = repo.create(tenant_id=a.id, request_type="analysis")
    session.commit()
    assert repo.get(tenant_id=b.id, entity_id=item.id) is None
    assert repo.list(tenant_id=a.id, request_type="analysis") == [item]
    with pytest.raises(ValueError):
        repo.update(tenant_id=a.id, entity_id=item.id, id="tampered")


def test_missing_actor_cannot_create_or_list_memories(session):
    a, b, ua, ub = tenants(session)
    svc = MemoryService(session)

    with pytest.raises(TenantAccessError):
        svc.create(
            tenant_id=a.id,
            actor_user_id=None,
            content="must not become shared",
            category="fact",
        )

    with pytest.raises(TenantAccessError):
        svc.list(tenant_id=a.id, actor_user_id=None)


def test_regular_user_cannot_create_or_modify_shared_memory(session):
    a, b, ua, ub = tenants(session)
    admin = User(
        tenant_id=a.id,
        email="admin@example.test",
        role="admin",
    )
    session.add(admin)
    session.commit()

    svc = MemoryService(session)

    with pytest.raises(TenantAccessError):
        svc.create(
            tenant_id=a.id,
            actor_user_id=ua.id,
            content="unauthorized shared memory",
            category="fact",
            shared=True,
        )

    shared = svc.create(
        tenant_id=a.id,
        actor_user_id=admin.id,
        content="approved shared memory",
        category="fact",
        shared=True,
    )

    # Regular users may read shared memories.
    assert svc.get(
        tenant_id=a.id,
        actor_user_id=ua.id,
        memory_id=shared.id,
    ).id == shared.id

    with pytest.raises(TenantAccessError):
        svc.update(
            tenant_id=a.id,
            actor_user_id=ua.id,
            memory_id=shared.id,
            content="unauthorized change",
            expected_version=1,
        )

    with pytest.raises(TenantAccessError):
        svc.delete(
            tenant_id=a.id,
            actor_user_id=ua.id,
            memory_id=shared.id,
        )


def test_admin_can_update_and_delete_shared_memory(session):
    a, b, ua, ub = tenants(session)
    admin = User(
        tenant_id=a.id,
        email="admin2@example.test",
        role="admin",
    )
    session.add(admin)
    session.commit()

    svc = MemoryService(session)
    shared = svc.create(
        tenant_id=a.id,
        actor_user_id=admin.id,
        content="shared v1",
        category="fact",
        shared=True,
    )

    updated = svc.update(
        tenant_id=a.id,
        actor_user_id=admin.id,
        memory_id=shared.id,
        content="shared v2",
        expected_version=1,
    )
    assert updated.current_version == 2

    svc.delete(
        tenant_id=a.id,
        actor_user_id=admin.id,
        memory_id=shared.id,
    )

    assert svc.repo.get(tenant_id=a.id, memory_id=shared.id) is None


def test_actor_from_another_tenant_is_rejected(session):
    a, b, ua, ub = tenants(session)
    svc = MemoryService(session)

    with pytest.raises(TenantAccessError):
        svc.create(
            tenant_id=a.id,
            actor_user_id=ub.id,
            content="cross tenant attempt",
            category="fact",
        )
