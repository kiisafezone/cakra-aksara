"""Application services: authorization-aware operations and transaction boundaries."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AuditEvent, Memory, User, utcnow
from .repositories import MemoryRepository, TenantRepository


class TenantAccessError(PermissionError):
    """Raised when an actor attempts an unauthorized tenant operation."""


class MemoryService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = MemoryRepository(session)

    def _require_actor(self, tenant_id: str, actor_user_id: str | None) -> User:
        if not actor_user_id:
            raise TenantAccessError("an active user identity is required")

        actor = self.session.scalar(
            select(User).where(
                User.id == actor_user_id,
                User.tenant_id == tenant_id,
                User.status == "active",
            )
        )
        if actor is None:
            raise TenantAccessError("active user not found in this tenant")

        return actor

    def create(
        self,
        *,
        tenant_id: str,
        actor_user_id: str | None,
        content: str,
        category: str,
        shared: bool = False,
        **metadata,
    ) -> Memory:
        actor = self._require_actor(tenant_id, actor_user_id)

        if shared and actor.role != "admin":
            raise TenantAccessError("only admins can create shared memories")

        owner_id = None if shared else actor.id

        memory = self.repo.create(
            tenant_id=tenant_id,
            owner_user_id=owner_id,
            content=content,
            category=category,
            **metadata,
        )
        self._audit(tenant_id, actor.id, "memory.create", memory.id)
        self.session.commit()
        self.session.refresh(memory)
        return memory

    def get(
        self,
        *,
        tenant_id: str,
        actor_user_id: str | None,
        memory_id: str,
    ) -> Memory:
        actor = self._require_actor(tenant_id, actor_user_id)

        memory = self.repo.get(tenant_id=tenant_id, memory_id=memory_id)
        if memory is None:
            raise LookupError("memory not found")

        if memory.owner_user_id is not None and memory.owner_user_id != actor.id:
            raise TenantAccessError("memory is private to another user")

        return memory

    def update(
        self,
        *,
        tenant_id: str,
        actor_user_id: str | None,
        memory_id: str,
        content: str,
        expected_version: int,
        reason: str | None = None,
    ) -> Memory:
        actor = self._require_actor(tenant_id, actor_user_id)
        memory = self.get(
            tenant_id=tenant_id,
            actor_user_id=actor.id,
            memory_id=memory_id,
        )

        if memory.owner_user_id is None and actor.role != "admin":
            raise TenantAccessError("only admins can update shared memories")

        updated = self.repo.update(
            tenant_id=tenant_id,
            memory_id=memory_id,
            content=content,
            expected_version=expected_version,
            reason=reason,
            changed_by=actor.id,
        )
        self._audit(tenant_id, actor.id, "memory.update", updated.id)
        self.session.commit()
        self.session.refresh(updated)
        return updated

    def list(
        self,
        *,
        tenant_id: str,
        actor_user_id: str | None,
        include_shared: bool = True,
        limit: int = 20,
    ):
        actor = self._require_actor(tenant_id, actor_user_id)
        return self.repo.list(
            tenant_id=tenant_id,
            owner_user_id=actor.id,
            include_shared=include_shared,
            limit=limit,
        )

    def delete(
        self,
        *,
        tenant_id: str,
        actor_user_id: str | None,
        memory_id: str,
    ) -> None:
        actor = self._require_actor(tenant_id, actor_user_id)
        memory = self.get(
            tenant_id=tenant_id,
            actor_user_id=actor.id,
            memory_id=memory_id,
        )

        if memory.owner_user_id is None and actor.role != "admin":
            raise TenantAccessError("only admins can delete shared memories")

        memory.status = "deleted"
        memory.deleted_at = utcnow()
        self._audit(tenant_id, actor.id, "memory.delete", memory.id)
        self.session.commit()

    def _audit(self, tenant_id, actor_id, action, resource_id):
        self.session.add(
            AuditEvent(
                tenant_id=tenant_id,
                actor_type="user",
                actor_id=actor_id,
                action=action,
                resource_type="memory",
                resource_id=resource_id,
                outcome="success",
                metadata_json={},
            )
        )


class EntityService:
    """Small service facade for other tenant-scoped entities."""

    def __init__(self, session: Session, model):
        self.session = session
        self.repo = TenantRepository(session, model)

    def create(self, *, tenant_id: str, **values):
        entity = self.repo.create(tenant_id=tenant_id, **values)
        self.session.commit()
        self.session.refresh(entity)
        return entity

    def get(self, *, tenant_id: str, entity_id: str):
        return self.repo.get(tenant_id=tenant_id, entity_id=entity_id)

    def list(self, *, tenant_id: str, limit: int = 50, offset: int = 0, **filters):
        return self.repo.list(
            tenant_id=tenant_id,
            limit=limit,
            offset=offset,
            **filters,
        )

    def update(self, *, tenant_id: str, entity_id: str, **changes):
        entity = self.repo.update(
            tenant_id=tenant_id,
            entity_id=entity_id,
            **changes,
        )
        self.session.commit()
        self.session.refresh(entity)
        return entity

    def delete(self, *, tenant_id: str, entity_id: str):
        deleted = self.repo.delete(tenant_id=tenant_id, entity_id=entity_id)
        self.session.commit()
        return deleted
