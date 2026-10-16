import base64, hashlib, hmac, json, secrets
from datetime import datetime, timedelta, timezone
from app.config.settings import settings

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 310000).hex()
    return f"pbkdf2_sha256${salt}${digest}"

def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt, expected = stored.split("$", 2)
        if scheme != "pbkdf2_sha256": return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 310000).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError): return False

def create_access_token(user_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    header = {"alg":"HS256", "typ":"JWT"}
    payload = {"sub":str(user_id), "role":role, "iat":int(now.timestamp()), "exp":int((now + timedelta(minutes=settings.jwt_expire_minutes)).timestamp())}
    body = f"{_b64(json.dumps(header,separators=(',',':')).encode())}.{_b64(json.dumps(payload,separators=(',',':')).encode())}"
    signature = hmac.new(settings.jwt_secret.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64(signature)}"

def decode_token(token: str) -> dict:
    try:
        header_part, payload_part, signature_part = token.split(".")
        header = json.loads(_unb64(header_part)); payload = json.loads(_unb64(payload_part))
        if header.get("alg") != "HS256": raise ValueError("Unsupported JWT algorithm")
        body = f"{header_part}.{payload_part}"
        expected = _b64(hmac.new(settings.jwt_secret.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, signature_part): raise ValueError("Invalid token signature")
        if int(payload.get("exp", 0)) <= int(datetime.now(timezone.utc).timestamp()): raise ValueError("Token expired")
        return payload
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid or expired token") from exc
