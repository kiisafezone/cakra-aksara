import base64
import hashlib
import hmac
import secrets


PASSWORD_ITERATIONS = 600_000


def generate_api_key() -> dict[str, str]:
    prefix = "cak_" + secrets.token_hex(6)
    secret = secrets.token_urlsafe(32)
    full_key = f"{prefix}.{secret}"
    return {
        "prefix": prefix,
        "secret": secret,
        "full_key": full_key,
        "key_hash": hash_api_key(secret),
    }


def hash_api_key(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    salt_text = base64.urlsafe_b64encode(salt).decode("ascii")
    digest_text = base64.urlsafe_b64encode(digest).decode("ascii")
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt_text}${digest_text}"


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False

    try:
        algorithm, iterations_text, salt_text, digest_text = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False

        iterations = int(iterations_text)
        if iterations < 100_000 or iterations > 2_000_000:
            return False

        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, UnicodeError):
        return False


def generate_user_token() -> str:
    return secrets.token_urlsafe(48)


def hash_user_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
