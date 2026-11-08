"""Application-level tenant consistency guard for SQLAlchemy ORM writes.

This guard supplements tenant-scoped repositories. It is not a replacement for
authorization and does not protect raw SQL or out-of-band database writers.
"""
from sqlalchemy import event, select
from sqlalchemy.orm import Session
from .models import (User, RequestRecord, Memory, Verification, Claim)

# (child model name, foreign-key attribute, parent model name)
_RELATIONS = {
    "User": [],
    "APIKey": [],
    "RequestRecord": [("user_id", "User")],
    "ContextItem": [("request_id", "RequestRecord")],
    "Memory": [("owner_user_id", "User")],
    "MemoryVersion": [("memory_id", "Memory"), ("changed_by", "User")],
    "Claim": [("request_id", "RequestRecord")],
    "Verification": [("claim_id", "Claim")],
    "Evidence": [("verification_id", "Verification")],
    "Assumption": [("request_id", "RequestRecord")],
    "Contradiction": [("request_id", "RequestRecord"), ("resolved_by", "User")],
    "Policy": [("created_by", "User")],
    "AuditEvent": [("request_id", "RequestRecord")],
    "ContinuityPackage": [("created_by", "User")],
}

@event.listens_for(Session, "before_flush")
def enforce_tenant_consistency(session, flush_context, instances):
    """Reject ORM writes whose tenant-owned references cross tenant boundaries."""
    for obj in session.new.union(session.dirty):
        tenant_id = getattr(obj, "tenant_id", None)
        if tenant_id is None:
            continue
        for fk_attr, parent_name in _RELATIONS.get(type(obj).__name__, []):
            fk_value = getattr(obj, fk_attr, None)
            if fk_value is None:
                continue
            parent = next(
                (candidate for candidate in session.new
                 if type(candidate).__name__ == parent_name
                 and getattr(candidate, "id", None) == fk_value),
                None,
            )
            if parent is None:
                parent_cls = {
                    "User": User, "RequestRecord": RequestRecord,
                    "Memory": Memory, "Verification": Verification, "Claim": Claim,
                }.get(parent_name)
                if parent_cls is None:
                    raise RuntimeError(f"Tenant guard cannot resolve model {parent_name}")
                parent = session.scalar(select(parent_cls).where(parent_cls.id == fk_value))
            if parent is None:
                # Let the database's FK constraint report a missing reference.
                continue
            if getattr(parent, "tenant_id", None) != tenant_id:
                raise ValueError(
                    f"cross-tenant reference rejected: {type(obj).__name__}.{fk_attr}"
                )
