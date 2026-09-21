"""Endpoints de autenticación (RF7, issue #4).

Contrato: docs/02-contrato-api.md §2.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Usuario
from ..schemas.auth import LoginRequest, TokenResponse, UsuarioPublico
from ..security import UsuarioActual, create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

#: Hash descartable contra el que se compara cuando el email no existe, para que
#: el login tarde lo mismo exista o no el usuario y no se pueda deducir qué
#: emails están registrados midiendo el tiempo de respuesta.
_HASH_SEÑUELO = hash_password("no-existe")


@router.post("/login", response_model=TokenResponse)
def login(datos: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    """Valida credenciales y emite el JWT."""
    usuario = db.scalar(select(Usuario).where(Usuario.email == datos.email))

    if usuario is None:
        verify_password(datos.password, _HASH_SEÑUELO)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")

    if not verify_password(datos.password, usuario.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")

    # Se distingue de "credenciales inválidas" recién acá: la cuenta existe y la
    # contraseña es correcta, así que informar que está inactiva no filtra nada.
    if not usuario.activo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario inactivo")

    token = create_access_token(
        subject=str(usuario.id), roles=[rol.value for rol in usuario.roles]
    )
    return TokenResponse(
        access_token=token, user=UsuarioPublico.model_validate(usuario)
    )


@router.get("/me", response_model=UsuarioPublico)
def me(usuario: UsuarioActual) -> Usuario:
    """Datos del usuario del token. Sirve para revalidar la sesión al recargar."""
    return usuario
