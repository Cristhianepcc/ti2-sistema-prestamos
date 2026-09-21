"""Utilidades de seguridad: hashing de contraseñas y JWT.

Base para el issue #4 (auth). Los endpoints de login y las dependencias de rol
se implementan en routers/auth.py.
"""
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from .config import settings

#: bcrypt solo considera los primeros 72 bytes y a partir de la versión 4.1
#: lanza error si se le pasa más, en vez de truncar. Truncamos nosotros.
MAX_PASSWORD_BYTES = 72


def _a_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:MAX_PASSWORD_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_a_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(_a_bytes(plain), hashed.encode("utf-8"))


def create_access_token(subject: str, roles: list[str]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(subject), "roles": roles, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
