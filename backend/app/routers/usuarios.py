"""Endpoints administrativos de usuarios y roles (RF7)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Rol, Usuario
from ..schemas.auth import UsuarioPublico
from ..schemas.usuario import UsuarioCreate, UsuarioRolesUpdate
from ..security import require_role
from ..services import usuario_service

router = APIRouter(
    prefix="/usuarios",
    tags=["usuarios"],
    dependencies=[Depends(require_role(Rol.ADMINISTRADOR_SISTEMA))],
)


@router.get("", response_model=list[UsuarioPublico])
def obtener_usuarios(db: Annotated[Session, Depends(get_db)]) -> list[Usuario]:
    """Lista usuarios; requiere ADMINISTRADOR_SISTEMA."""
    return usuario_service.listar_usuarios(db)


@router.post(
    "",
    response_model=UsuarioPublico,
    status_code=status.HTTP_201_CREATED,
)
def crear_usuario(
    datos: UsuarioCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Usuario:
    """Crea una cuenta administrativa; la contraseña se almacena con bcrypt."""
    try:
        return usuario_service.crear_usuario(db, **datos.model_dump())
    except usuario_service.UsuarioDuplicado as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error


@router.put("/{usuario_id}/roles", response_model=UsuarioPublico)
def reemplazar_roles(
    usuario_id: Annotated[int, Path(ge=1)],
    datos: UsuarioRolesUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> Usuario:
    """Reemplaza los roles actuales por la lista recibida."""
    try:
        return usuario_service.actualizar_roles(
            db, usuario_id=usuario_id, roles=datos.roles
        )
    except usuario_service.UsuarioNoEncontrado as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except usuario_service.UltimoAdministrador as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
