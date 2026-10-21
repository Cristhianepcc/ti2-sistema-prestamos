"""Endpoints de préstamos y devolución (RF3, issue #31)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Prestamo
from ..models.enums import EstadoPrestamo, Rol
from ..schemas.prestamo import DevolucionCreate, PrestamoCreate, PrestamoPublico
from ..security import UsuarioActual, require_role
from ..services.prestamo_service import (
    ConflictoPrestamo,
    RegistroPrestamoNoEncontrado,
    crear_prestamo,
    registrar_devolucion,
)

router = APIRouter(prefix="/prestamos", tags=["prestamos"])


@router.post(
    "",
    response_model=PrestamoPublico,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(Rol.CUSTODIO_CE, Rol.CUSTODIO_INFRA))],
)
def registrar_prestamo(
    datos: PrestamoCreate,
    usuario: UsuarioActual,
    db: Annotated[Session, Depends(get_db)],
) -> Prestamo:
    """Registra la entrega de un recurso. Aplica las invariantes de #30."""
    try:
        return crear_prestamo(
            db,
            recurso_id=datos.recurso_id,
            prestatario_id=datos.prestatario_id,
            registrado_por_id=usuario.id,
            tipo_prestamo=datos.tipo_prestamo,
            modalidad_uso=datos.modalidad_uso,
            fecha_limite=datos.fecha_limite,
            reserva_id=datos.reserva_id,
            condicion_entrega=datos.condicion_entrega,
            garantia=datos.garantia.model_dump() if datos.garantia else None,
        )
    except RegistroPrestamoNoEncontrado as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    except ConflictoPrestamo as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e


@router.post(
    "/{id}/devolucion",
    response_model=PrestamoPublico,
    dependencies=[Depends(require_role(Rol.CUSTODIO_CE, Rol.CUSTODIO_INFRA))],
)
def devolver_prestamo(
    id: int,
    datos: DevolucionCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Prestamo:
    """Registra la devolución de un préstamo activo o atrasado."""
    try:
        return registrar_devolucion(
            db,
            prestamo_id=id,
            condicion_devolucion=datos.condicion_devolucion,
            danado=datos.danado,
        )
    except RegistroPrestamoNoEncontrado as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    except ConflictoPrestamo as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e


@router.get("", response_model=list[PrestamoPublico])
def listar_prestamos(
    usuario: UsuarioActual,
    db: Annotated[Session, Depends(get_db)],
    mios: bool | None = None,
    estado: EstadoPrestamo | None = None,
) -> list[Prestamo]:
    """Lista los préstamos propios (`mios=true`) o, para custodios, de todos."""
    stmt = select(Prestamo)

    if mios:
        stmt = stmt.where(Prestamo.prestatario_id == usuario.id)
    elif not usuario.tiene_rol(Rol.CUSTODIO_CE, Rol.CUSTODIO_INFRA):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo un custodio puede consultar préstamos de otros usuarios",
        )

    if estado is not None:
        stmt = stmt.where(Prestamo.estado == estado)

    return list(db.scalars(stmt))
