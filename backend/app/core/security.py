import hashlib
import os
import datetime
import jwt
from typing import Optional, Dict, Any

# Security configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "omniroute-enterprise-secret-key-20261022-secure-auth")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 hours

def hash_password(password: str) -> str:
    """
    Secure password hashing using PBKDF2-HMAC-SHA256 with a cryptographically
    random 16-byte salt and 100,000 iterations (NIST SP 800-63B compliant).
    Format stored: pbkdf2_sha256$iterations$salt$hash
    """
    salt = os.urandom(16)
    iterations = 100_000
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${derived.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Constant-time verification of password against stored PBKDF2 hash.
    """
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_hash = bytes.fromhex(parts[3])
        actual_hash = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
        import hmac
        return hmac.compare_digest(expected_hash, actual_hash)
    except Exception:
        return False

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[datetime.timedelta] = None
) -> str:
    """
    Generates a cryptographically signed HS256 JWT access token.
    """
    to_encode = data.copy()
    now = datetime.datetime.now(datetime.timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": now,
        "nbf": now
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decodes and validates JWT signature and expiry.
    Raises jwt.PyJWTError on invalid/expired token.
    """
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return payload
