import hmac
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from uail_db.models import APIKey, Tenant, User, UserSession
from app.dependencies import get_db
from app.security import hash_api_key, hash_user_token


api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class APIKeyContext:
    api_key: APIKey
    tenant: Tenant


@dataclass
class UserContext:
    user: User
    session: UserSession
    tenant: Tenant


def unauthorized():
    return HTTPException(
        status_code=401,
        detail="Invalid or inactive credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def is_expired(expires_at: datetime | None) -> bool:
    if expires_at is None:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= datetime.now(timezone.utc)


def get_current_api_key(
    token: str | None = Depends(api_key_scheme),
    db: Session = Depends(get_db),
) -> APIKeyContext:
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing X-API-Key header",
        )

    try:
        prefix, secret = token.split(".", 1)
    except ValueError:
        raise unauthorized()

    if not prefix.startswith("cak_") or not secret:
        raise unauthorized()

    api_key = db.scalar(
        select(APIKey).where(APIKey.key_prefix == prefix)
    )
    if api_key is None:
        raise unauthorized()

    supplied_hash = hash_api_key(secret)
    if not hmac.compare_digest(api_key.key_hash, supplied_hash):
        raise unauthorized()

    if api_key.revoked_at is not None or is_expired(api_key.expires_at):
        raise unauthorized()

    tenant = db.get(Tenant, api_key.tenant_id)
    if tenant is None or tenant.status != "active":
        raise HTTPException(status_code=403, detail="Tenant is inactive")

    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()

    return APIKeyContext(api_key=api_key, tenant=tenant)


def require_api_key_scope(required_scope: str):
    def dependency(
        context: APIKeyContext = Depends(get_current_api_key),
    ) -> APIKeyContext:
        scopes = context.api_key.scopes or []
        if required_scope not in scopes:
            raise HTTPException(
                status_code=403,
                detail=f"API key lacks required scope: {required_scope}",
            )
        return context

    return dependency


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    context: APIKeyContext = Depends(get_current_api_key),
    db: Session = Depends(get_db),
) -> UserContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized()

    token_hash = hash_user_token(credentials.credentials)
    user_session = db.scalar(
        select(UserSession).where(UserSession.token_hash == token_hash)
    )

    if user_session is None:
        raise unauthorized()

    if (
        user_session.revoked_at is not None
        or is_expired(user_session.expires_at)
        or user_session.tenant_id != context.tenant.id
    ):
        raise unauthorized()

    user = db.get(User, user_session.user_id)
    if (
        user is None
        or user.status != "active"
        or user.tenant_id != context.tenant.id
    ):
        raise unauthorized()

    user_session.last_used_at = datetime.now(timezone.utc)
    db.commit()

    return UserContext(
        user=user,
        session=user_session,
        tenant=context.tenant,
    )
