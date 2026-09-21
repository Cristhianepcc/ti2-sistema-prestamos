"""Utilidades de seguridad: hashing de contraseñas, JWT y dependencias de rol.

Ver docs/01-sdd.md §8. Los endpoints de login viven en routers/auth.py; acá está
lo reutilizable: emitir/validar el token y las dependencias que protegen endpoints.
"""
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import Rol, Usuario

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


# --- Dependencias de FastAPI -------------------------------------------------

#: `auto_error=False` para devolver 401 con nuestro mensaje; con el valor por
#: defecto FastAPI responde 403 cuando falta el header, que no es lo acordado
#: en el contrato de API.
bearer_scheme = HTTPBearer(auto_error=False, description="JWT obtenido en /auth/login")


def _no_autorizado(detalle: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detalle,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> Usuario:
    """Resuelve el usuario a partir del JWT del header `Authorization`.

    Lanza 401 si falta el token, si es inválido/expiró, o si el usuario ya no
    existe o fue desactivado después de emitirse el token.
    """
    if credenciales is None:
        raise _no_autorizado("No autenticado")

    try:
        payload = decode_access_token(credenciales.credentials)
    except JWTError:
        raise _no_autorizado("Token inválido o expirado")

    try:
        usuario_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise _no_autorizado("Token inválido o expirado")

    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise _no_autorizado("Token inválido o expirado")
    if not usuario.activo:
        raise _no_autorizado("Usuario inactivo")

    return usuario


#: Atajo para anotar endpoints: `usuario: UsuarioActual`.
UsuarioActual = Annotated[Usuario, Depends(get_current_user)]


def require_role(*roles: Rol):
    """Dependencia que exige **al menos uno** de los roles indicados.

    Los roles se leen del usuario en base de datos, no del token, para que un
    cambio de permisos tenga efecto sin esperar a que expire el JWT.

        @router.post("/recursos", dependencies=[Depends(require_role(Rol.CUSTODIO_CE))])
    """

    def dependencia(usuario: UsuarioActual) -> Usuario:
        if not usuario.tiene_rol(*roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para esta operación "
                       f"(requiere: {', '.join(r.value for r in roles)})",
            )
        return usuario

    return dependencia
