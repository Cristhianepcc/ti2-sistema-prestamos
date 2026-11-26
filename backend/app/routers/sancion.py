"""Endpoints de consulta y gestión de sanciones (RF5)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.enums import Rol
from ..models.sancion import Sancion
from ..schemas.sancion import (
    EstadoBloqueoSancion,
    SancionCreate,
    SancionPublica,
    SancionResolucionCreate,
)
from ..security import UsuarioActual, require_role
from ..services.sancion_service import (
    ConflictoSancion,
    PermisoSancion,
    SancionNoEncontrada,
    crear_sancion_manual,
    estado_bloqueo,
    listar_sanciones,
    mensaje_bloqueo,
    resolver_sancion,
)

router = APIRouter(prefix="/sanciones", tags=["sanciones"])
ROLES_CUSTODIO = (Rol.CUSTODIO_CE, Rol.CUSTODIO_INFRA)
ROLES_GESTION_SANCION = (*ROLES_CUSTODIO, Rol.ADMINISTRADOR_SISTEMA)


@router.get("", response_model=list[SancionPublica])
def listar(
    usuario: UsuarioActual,
    db: Annotated[Session, Depends(get_db)],
    mias: bool = Query(default=False),
    activas: bool | None = Query(default=None),
) -> list[Sancion]:
    """Usuarios ven sus sanciones; custodios, las de sus recursos; admin, todas."""
    return listar_sanciones(db, actor=usuario, mias=mias, activas=activas)


@router.get("/bloqueo", response_model=EstadoBloqueoSancion)
def mi_bloqueo(
    usuario: UsuarioActual,
    db: Annotated[Session, Depends(get_db)],
) -> EstadoBloqueoSancion:
    """Indica si el usuario autenticado está bloqueado ahora mismo y por qué."""
    sancion = estado_bloqueo(db, usuario.id)
    if sancion is None:
        return EstadoBloqueoSancion(bloqueado=False, mensaje=None, motivo=None, fin=None)
    return EstadoBloqueoSancion(
        bloqueado=True,
        mensaje=mensaje_bloqueo(sancion),
        motivo=sancion.motivo,
        fin=sancion.fin,
    )


@router.post(
    "",
    response_model=SancionPublica,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(*ROLES_GESTION_SANCION))],
)
def registrar(
    datos: SancionCreate,
    usuario: UsuarioActual,
    db: Annotated[Session, Depends(get_db)],
) -> Sancion:
    """Registra una sanción sobre un préstamo ya creado.

    La devolución crea automáticamente las sanciones que correspondan; este
    endpoint permite documentar casos anteriores o corregidos manualmente.
    """
    try:
        return crear_sancion_manual(
            db,
            prestamo_id=datos.prestamo_id,
            motivo=datos.motivo,
            detalle=datos.detalle,
            actor_id=usuario.id,
        )
    except SancionNoEncontrada as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except PermisoSancion as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(error)) from error
    except ConflictoSancion as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error


@router.patch(
    "/{sancion_id}/levantar",
    response_model=SancionPublica,
    dependencies=[Depends(require_role(*ROLES_GESTION_SANCION))],
)
def levantar(
    sancion_id: int,
    datos: SancionResolucionCreate,
    usuario: UsuarioActual,
    db: Annotated[Session, Depends(get_db)],
) -> Sancion:
    """Registra reparación/reposición y cierra la sanción sin borrar su historial."""
    try:
        return resolver_sancion(
            db,
            sancion_id=sancion_id,
            actor_id=usuario.id,
            detalle=datos.detalle,
            recurso_reposicion_id=datos.recurso_reposicion_id,
        )
    except SancionNoEncontrada as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except PermisoSancion as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(error)) from error
    except ConflictoSancion as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
