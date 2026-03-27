"""密码哈希（无 passlib 依赖）：与 Hongshan 注册入口共用 DuckDB 存储."""

from __future__ import annotations

import hashlib
import secrets


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), 120_000).hex()
    return f"{salt}${h}"


def verify_password(password: str, stored: str) -> bool:
    if not stored or "$" not in stored:
        return False
    salt, _, digest = stored.partition("$")
    if not salt or not digest:
        return False
    h2 = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), 120_000).hex()
    return secrets.compare_digest(digest, h2)
