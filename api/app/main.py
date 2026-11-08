import re
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from uail_db.database import engine
from uail_db.models import User, UserSession, new_id
from app.auth import (
    APIKeyContext,
    UserContext,
    get_current_api_key,
    get_current_user,
    require_api_key_scope,
)
from app.config import settings
from app.dependencies import get_db
from app.security import (
    generate_user_token,
    hash_password,
    hash_user_token,
    verify_password,
)


SESSION_MINUTES = 60

app = FastAPI(
    title=settings.title,
    description=settings.description,
    version=settings.version,
)


class RegisterInput(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=12, max_length=256)
    display_name: str | None = Field(default=None, max_length=255)


class LoginInput(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=256)


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(status_code=422, detail="Invalid email address")
    return email


def user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "tenant_id": user.tenant_id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "status": user.status,
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "cakra-aksara-api",
        "environment": settings.environment,
    }


@app.get("/ready")
def ready():
    from fastapi import HTTPException
    from sqlalchemy import text
    from sqlalchemy.exc import SQLAlchemyError

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "database": "unavailable"},
        )


@app.get("/v1/auth/check")
def check_api_key(
    context: APIKeyContext = Depends(
        require_api_key_scope("auth:check")
    ),
):
    return {
        "authenticated": True,
        "tenant_id": context.tenant.id,
        "api_key_id": context.api_key.id,
        "scopes": context.api_key.scopes or [],
    }


@app.post("/v1/auth/register", status_code=201)
def register_user(
    payload: RegisterInput,
    context: APIKeyContext = Depends(
        require_api_key_scope("users:register")
    ),
    db: Session = Depends(get_db),
):
    email = normalize_email(payload.email)

    existing = db.scalar(
        select(User).where(
            User.tenant_id == context.tenant.id,
            User.email == email,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        id=new_id(),
        tenant_id=context.tenant.id,
        email=email,
        display_name=(payload.display_name or "").strip() or None,
        password_hash=hash_password(payload.password),
        role="user",
        status="active",
    )
    db.add(user)

    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")

    return {"created": True, "user": user_payload(user)}


@app.post("/v1/auth/login")
def login_user(
    payload: LoginInput,
    context: APIKeyContext = Depends(
        require_api_key_scope("users:login")
    ),
    db: Session = Depends(get_db),
):
    email = normalize_email(payload.email)
    user = db.scalar(
        select(User).where(
            User.tenant_id == context.tenant.id,
            User.email == email,
        )
    )

    if (
        user is None
        or user.status != "active"
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = generate_user_token()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=SESSION_MINUTES
    )

    session = UserSession(
        id=new_id(),
        tenant_id=context.tenant.id,
        user_id=user.id,
        token_hash=hash_user_token(token),
        expires_at=expires_at,
    )
    db.add(session)
    db.commit()

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at.isoformat(),
        "user": user_payload(user),
    }


@app.get("/v1/auth/me")
def get_me(
    context: UserContext = Depends(get_current_user),
    api_context: APIKeyContext = Depends(
        require_api_key_scope("users:read")
    ),
):
    if context.tenant.id != api_context.tenant.id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    return {"authenticated": True, "user": user_payload(context.user)}


@app.post("/v1/auth/logout")
def logout_user(
    context: UserContext = Depends(get_current_user),
    api_context: APIKeyContext = Depends(
        require_api_key_scope("users:logout")
    ),
    db: Session = Depends(get_db),
):
    if context.tenant.id != api_context.tenant.id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    context.session.revoked_at = datetime.now(timezone.utc)
    db.add(context.session)
    db.commit()
    return {"logged_out": True}
