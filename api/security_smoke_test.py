import json
import secrets
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, select

from uail_db.database import SessionLocal
from uail_db.models import APIKey, Tenant, User, UserSession, new_id
from app.security import (
    generate_api_key,
    hash_password,
    hash_user_token,
)

BASE_URL = "http://127.0.0.1:8000"
TENANT_A_ID = "b42abd66-e3e5-42a1-9dd0-2031a8f19c32"

CONFIG = Path.home() / ".config" / "cakra-aksara"
API_KEY_FILE = CONFIG / "api_key"
USER_FILE = CONFIG / "dev_user.json"

if not API_KEY_FILE.exists() or not USER_FILE.exists():
    raise SystemExit("File API key atau kredensial pengguna tidak ditemukan.")

api_key_a = API_KEY_FILE.read_text().strip()
credentials = json.loads(USER_FILE.read_text())
email_a = credentials["email"]

def request(method, path, key, body=None, token=None):
    headers = {"X-API-Key": key}
    data = None

    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()

    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        raw = error.read().decode()
        try:
            return error.code, json.loads(raw)
        except Exception:
            return error.code, {"detail": raw}

def expect(label, actual, wanted):
    if actual != wanted:
        raise AssertionError(
            f"{label}: diharapkan HTTP {wanted}, diterima HTTP {actual}"
        )
    print(f"[LULUS] {label}: HTTP {actual}")

def login(key, email, password):
    return request(
        "POST",
        "/v1/auth/login",
        key,
        {"email": email, "password": password},
    )

tokens = []
tenant_b_id = None
user_b_id = None
key_b_id = None
restricted_key_id = None
revoked_key_id = None
user_a_id = None
original_status = None

# Rotasi password akun uji yang sebelumnya tampil di percakapan.
new_password = secrets.token_urlsafe(32)
credentials["password"] = new_password

USER_FILE.write_text(json.dumps(credentials, indent=2) + "\n")
USER_FILE.chmod(0o600)

try:
    with SessionLocal() as db:
        user_a = db.scalar(
            select(User).where(
                User.tenant_id == TENANT_A_ID,
                User.email == email_a,
            )
        )
        if user_a is None:
            raise SystemExit("Akun pengujian utama tidak ditemukan.")

        user_a_id = user_a.id
        original_status = user_a.status
        user_a.password_hash = hash_password(new_password)
        user_a.status = "active"

        prefix_a = api_key_a.split(".", 1)[0]
        key_a = db.scalar(
            select(APIKey).where(APIKey.key_prefix == prefix_a)
        )
        if (
            key_a is None
            or key_a.tenant_id != TENANT_A_ID
            or key_a.revoked_at is not None
        ):
            raise SystemExit("API key utama tidak aktif atau tidak cocok.")

        key_a.scopes = sorted(
            set(key_a.scopes or [])
            | {
                "auth:check",
                "users:register",
                "users:login",
                "users:read",
                "users:logout",
            }
        )

        # Bersihkan tenant uji yang tertinggal dari eksekusi sebelumnya.
        stale_tenants = db.scalars(
            select(Tenant).where(Tenant.slug.like("security-test-%"))
        ).all()
        for stale in stale_tenants:
            db.execute(delete(UserSession).where(UserSession.tenant_id == stale.id))
            db.execute(delete(User).where(User.tenant_id == stale.id))
            db.execute(delete(APIKey).where(APIKey.tenant_id == stale.id))
            db.execute(delete(Tenant).where(Tenant.id == stale.id))
        db.flush()

        tenant_b = Tenant(
            id=new_id(),
            name="Security Test Tenant",
            slug="security-test-" + secrets.token_hex(6),
            status="active",
            settings={},
        )
        db.add(tenant_b)
        db.flush()
        tenant_b_id = tenant_b.id

        email_b = "cross-" + secrets.token_hex(6) + "@example.com"
        password_b = secrets.token_urlsafe(32)

        user_b = User(
            id=new_id(),
            tenant_id=tenant_b.id,
            email=email_b,
            display_name="Temporary Security Test User",
            password_hash=hash_password(password_b),
            role="user",
            status="active",
        )
        db.add(user_b)
        db.flush()
        user_b_id = user_b.id

        generated_b = generate_api_key()
        key_b = APIKey(
            id=new_id(),
            tenant_id=tenant_b.id,
            name="Temporary Tenant B Test Key",
            key_prefix=generated_b["prefix"],
            key_hash=generated_b["key_hash"],
            scopes=[
                "auth:check",
                "users:login",
                "users:read",
                "users:logout",
            ],
        )
        db.add(key_b)
        key_b_id = key_b.id

        generated_restricted = generate_api_key()
        restricted_key = APIKey(
            id=new_id(),
            tenant_id=TENANT_A_ID,
            name="Temporary Restricted Test Key",
            key_prefix=generated_restricted["prefix"],
            key_hash=generated_restricted["key_hash"],
            scopes=[],
        )
        db.add(restricted_key)
        restricted_key_id = restricted_key.id

        generated_revoked = generate_api_key()
        revoked_key = APIKey(
            id=new_id(),
            tenant_id=TENANT_A_ID,
            name="Temporary Revoked Test Key",
            key_prefix=generated_revoked["prefix"],
            key_hash=generated_revoked["key_hash"],
            scopes=["auth:check"],
            revoked_at=datetime.now(timezone.utc),
        )
        db.add(revoked_key)
        revoked_key_id = revoked_key.id

        db.commit()

    key_b_secret = generated_b["full_key"]
    restricted_secret = generated_restricted["full_key"]
    revoked_secret = generated_revoked["full_key"]

    # 1. API key utama dan scope.
    status, _ = request("GET", "/v1/auth/check", api_key_a)
    expect("API key tenant A aktif", status, 200)

    status, _ = request("GET", "/v1/auth/check", restricted_secret)
    expect("API key tanpa scope ditolak", status, 403)

    status, _ = request("GET", "/v1/auth/check", revoked_secret)
    expect("API key yang dicabut ditolak", status, 401)

    # 2. Password salah.
    status, _ = login(api_key_a, email_a, "password-salah-untuk-pengujian")
    expect("Password salah ditolak", status, 401)

    # 3. API key A tidak boleh login sebagai user B.
    status, _ = login(api_key_a, email_b, password_b)
    expect("Tenant A tidak dapat login sebagai user B", status, 401)

    # 4. API key B tidak boleh login sebagai user A.
    status, _ = login(key_b_secret, email_a, new_password)
    expect("Tenant B tidak dapat login sebagai user A", status, 401)

    # 5. Login sah pada kedua tenant.
    status, result_a = login(api_key_a, email_a, new_password)
    expect("Login user A", status, 200)
    token_a = result_a["access_token"]
    tokens.append(token_a)

    status, result_b = login(key_b_secret, email_b, password_b)
    expect("Login user B", status, 200)
    token_b = result_b["access_token"]
    tokens.append(token_b)

    # 6. Identitas harus cocok dengan tenant API key.
    status, _ = request("GET", "/v1/auth/me", key_b_secret, token=token_a)
    expect("Token A tidak dapat dipakai dengan API key B", status, 401)

    status, _ = request("GET", "/v1/auth/me", api_key_a, token=token_b)
    expect("Token B tidak dapat dipakai dengan API key A", status, 401)

    # 7. Scope untuk baca dan logout wajib ada.
    status, _ = request(
        "GET", "/v1/auth/me", restricted_secret, token=token_a
    )
    expect("Scope users:read wajib", status, 403)

    status, _ = request(
        "POST", "/v1/auth/logout", restricted_secret, token=token_a
    )
    expect("Scope users:logout wajib", status, 403)

    # 8. Pengguna nonaktif tidak boleh login atau memakai sesi.
    token_a2 = token_a
    with SessionLocal() as db:
        user = db.get(User, user_a_id)
        user.status = "inactive"
        db.commit()

    try:
        status, _ = request(
            "GET", "/v1/auth/me", api_key_a, token=token_a2
        )
        expect("Sesi pengguna nonaktif ditolak", status, 401)

        status, _ = login(api_key_a, email_a, new_password)
        expect("Login pengguna nonaktif ditolak", status, 401)
    finally:
        with SessionLocal() as db:
            user = db.get(User, user_a_id)
            if user is not None:
                user.status = "active"
                db.commit()

    # 9. Logout harus mencabut token.
    status, _ = request(
        "POST", "/v1/auth/logout", api_key_a, token=token_a
    )
    expect("Logout user A", status, 200)

    status, _ = request(
        "GET", "/v1/auth/me", api_key_a, token=token_a
    )
    expect("Token A setelah logout ditolak", status, 401)

    status, _ = request(
        "POST", "/v1/auth/logout", key_b_secret, token=token_b
    )
    expect("Logout user B", status, 200)

    status, _ = request(
        "GET", "/v1/auth/me", key_b_secret, token=token_b
    )
    expect("Token B setelah logout ditolak", status, 401)

    print("\nSEMUA PENGUJIAN KEAMANAN LULUS.")

finally:
    # Hapus data tenant B sesuai urutan foreign key.
    with SessionLocal() as db:
        if tenant_b_id:
            db.execute(delete(UserSession).where(UserSession.tenant_id == tenant_b_id))
            db.execute(delete(User).where(User.tenant_id == tenant_b_id))
            db.execute(delete(APIKey).where(APIKey.tenant_id == tenant_b_id))
            db.execute(delete(Tenant).where(Tenant.id == tenant_b_id))

        # Hapus sesi sementara tenant A.
        for token in tokens:
            db.execute(
                delete(UserSession).where(
                    UserSession.token_hash == hash_user_token(token)
                )
            )

        for key_id in (restricted_key_id, revoked_key_id):
            if key_id:
                db.execute(delete(APIKey).where(APIKey.id == key_id))

        if user_a_id and original_status is not None:
            user_a = db.get(User, user_a_id)
            if user_a is not None:
                user_a.status = original_status

        db.commit()

    print("Data tenant sementara dan sesi uji dibersihkan.")
    print("Password akun uji telah dirotasi dan disimpan lokal.")
