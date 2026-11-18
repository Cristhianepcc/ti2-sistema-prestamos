"""Endpoints de Historial y Reportes (RF6, nivel 1)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.enums import EstadoPrestamo, Rol
from ..schemas.reporte import (
    HistorialResponse,
    ReporteInventario,
    ReportePrestamos,
    ReporteResumen,
)
from ..security import UsuarioActual, require_role
from ..services.reporte_service import (
    RangoInvalido,
    UsuarioNoEncontrado,
    listar_historial,
    reporte_inventario,
    reporte_prestamos,
    reporte_resumen,
)

router = APIRouter(tags=["historial-y-reportes"])


@router.get("/historial", response_model=HistorialResponse)
def obtener_historial(
    usuario: UsuarioActual,
    db: Annotated[Session, Depends(get_db)],
    usuario_id: int | None = None,
    estado: EstadoPrestamo | None = None,
    limite: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    """Historial propio, o el de cualquier usuario si quien pide es admin."""
    objetivo_id = usuario_id if usuario_id is not None else usuario.id
    if objetivo_id != usuario.id and not usuario.tiene_rol(Rol.ADMINISTRADOR_SISTEMA):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Solo puedes ver tu propio historial"
        )
    try:
        return listar_historial(
            db, usuario_id=objetivo_id, estado=estado, limite=limite, offset=offset
        )
    except UsuarioNoEncontrado as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e


@router.get(
    "/reportes/inventario",
    response_model=ReporteInventario,
    dependencies=[Depends(require_role(Rol.ADMINISTRADOR_SISTEMA))],
)
def obtener_reporte_inventario(db: Annotated[Session, Depends(get_db)]) -> dict:
    return reporte_inventario(db)


@router.get(
    "/reportes/prestamos",
    response_model=ReportePrestamos,
    dependencies=[Depends(require_role(Rol.ADMINISTRADOR_SISTEMA))],
)
def obtener_reporte_prestamos(
    db: Annotated[Session, Depends(get_db)],
    desde: date | None = None,
    hasta: date | None = None,
    top: Annotated[int, Query(ge=1, le=20)] = 5,
    limite_atrasados: Annotated[int, Query(ge=1, le=200)] = 50,
) -> dict:
    try:
        return reporte_prestamos(
            db, desde=desde, hasta=hasta, top=top, limite_atrasados=limite_atrasados
        )
    except RangoInvalido as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from e


@router.get(
    "/reportes/resumen",
    response_model=ReporteResumen,
    dependencies=[Depends(require_role(Rol.ADMINISTRADOR_SISTEMA))],
)
def obtener_reporte_resumen(db: Annotated[Session, Depends(get_db)]) -> dict:
    return reporte_resumen(db)
