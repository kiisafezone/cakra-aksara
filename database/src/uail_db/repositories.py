"""Tenant-scoped repositories. Repositories never commit; services own transactions."""
from typing import Any, TypeVar
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import (
    APIKey, Assumption, AuditEvent, Claim, ContextItem, ContinuityPackage,
    Contradiction, Evidence, IdempotencyRecord, Memory, MemoryVersion, Policy,
    RequestRecord, Verification,
)

T = TypeVar("T")

class TenantRepository:
    """Generic allow-listed CRUD repository with mandatory tenant filtering."""
    def __init__(self, session: Session, model: type[T]):
        if model not in _TENANT_MODELS:
            raise ValueError("model is not an approved tenant-scoped entity")
        self.session = session
        self.model = model

    def get(self, *, tenant_id: str, entity_id: str) -> T | None:
        return self.session.scalar(select(self.model).where(
            self.model.id == entity_id, self.model.tenant_id == tenant_id
        ))

    def list(self, *, tenant_id: str, limit: int = 50, offset: int = 0,
             **filters: Any) -> list[T]:
        allowed = {column.key for column in self.model.__table__.columns}
        if any(key not in allowed or key in {"id", "tenant_id"} for key in filters):
            raise ValueError("unsupported filter")
        stmt = select(self.model).where(self.model.tenant_id == tenant_id)
        for key, value in filters.items():
            stmt = stmt.where(getattr(self.model, key) == value)
        stmt = stmt.order_by(self.model.id).offset(max(offset, 0)).limit(min(max(limit, 1), 100))
        return list(self.session.scalars(stmt))

    def create(self, *, tenant_id: str, **values: Any) -> T:
        if "tenant_id" in values or "id" in values:
            raise ValueError("tenant_id and id are repository-managed")
        entity = self.model(tenant_id=tenant_id, **values)
        self.session.add(entity)
        self.session.flush()
        return entity

    def update(self, *, tenant_id: str, entity_id: str, **changes: Any) -> T:
        entity = self.get(tenant_id=tenant_id, entity_id=entity_id)
        if entity is None:
            raise LookupError("entity not found")
        protected = {"id", "tenant_id", "created_at"}
        if protected.intersection(changes):
            raise ValueError("protected fields cannot be changed")
        for key, value in changes.items():
            if not hasattr(entity, key):
                raise ValueError(f"unknown field: {key}")
            setattr(entity, key, value)
        self.session.flush()
        return entity

    def delete(self, *, tenant_id: str, entity_id: str) -> bool:
        entity = self.get(tenant_id=tenant_id, entity_id=entity_id)
        if entity is None:
            return False
        self.session.delete(entity)
        self.session.flush()
        return True

_TENANT_MODELS = {
    APIKey, Assumption, AuditEvent, Claim, ContextItem, ContinuityPackage,
    Contradiction, Evidence, IdempotencyRecord, Memory, MemoryVersion, Policy,
    RequestRecord, Verification,
}

class MemoryRepository:
    """Tenant-scoped memory access with immutable version snapshots."""
    def __init__(self, session: Session):
        self.session = session

    def create(self, *, tenant_id: str, owner_user_id: str | None,
               content: str, category: str, source_type: str | None = None,
               source_reference: str | None = None, metadata: dict | None = None) -> Memory:
        memory = Memory(
            tenant_id=tenant_id, owner_user_id=owner_user_id, content=content,
            category=category, current_version=1, source_type=source_type,
            source_reference=source_reference, metadata_json=metadata or {},
        )
        self.session.add(memory)
        self.session.flush()
        self.session.add(MemoryVersion(
            tenant_id=tenant_id, memory_id=memory.id, version_number=1,
            content_snapshot=content, change_reason="initial creation",
            source_reference=source_reference,
        ))
        self.session.flush()
        return memory

    def get(self, *, tenant_id: str, memory_id: str) -> Memory | None:
        return self.session.scalar(select(Memory).where(
            Memory.id == memory_id, Memory.tenant_id == tenant_id,
            Memory.deleted_at.is_(None), Memory.status != "deleted",
        ))

    def update(self, *, tenant_id: str, memory_id: str, content: str,
               expected_version: int, reason: str | None = None,
               changed_by: str | None = None) -> Memory:
        memory = self.get(tenant_id=tenant_id, memory_id=memory_id)
        if memory is None:
            raise LookupError("memory not found")
        if memory.current_version != expected_version:
            raise ValueError("version conflict")
        next_version = expected_version + 1
        memory.content = content
        memory.current_version = next_version
        self.session.add(MemoryVersion(
            tenant_id=tenant_id, memory_id=memory.id, version_number=next_version,
            content_snapshot=content, change_reason=reason, changed_by=changed_by,
        ))
        self.session.flush()
        return memory

    def list(self, *, tenant_id: str, owner_user_id: str | None = None,
             include_shared: bool = True, limit: int = 20) -> list[Memory]:
        stmt = select(Memory).where(
            Memory.tenant_id == tenant_id, Memory.deleted_at.is_(None),
            Memory.status == "active",
        )
        if owner_user_id is not None:
            stmt = stmt.where(
                (Memory.owner_user_id == owner_user_id) |
                ((Memory.owner_user_id.is_(None)) if include_shared else False)
            )
        return list(self.session.scalars(stmt.order_by(Memory.created_at.desc())
                                          .limit(min(max(limit, 1), 100))))
