"""Endpoints de Historial y Reportes (RF6, nivel 1)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.enums import EstadoPrestamo, Rol
from ..models.recurso import Recurso
from ..models.usuario import Usuario
from ..schemas.reporte import (
    EvolucionPrestamos,
    HistorialResponse,
    HistorialRecursoResponse,
    ReporteInventario,
    ReportePrestamos,
    ReporteResumen,
    ReporteUsuarios,
)
from ..security import UsuarioActual, require_role
from ..services.reporte_service import (
    RangoInvalido,
    RecursoNoEncontrado,
    UsuarioNoEncontrado,
    evolucion_prestamos,
    historial_recurso,
    listar_historial,
    reporte_inventario,
    reporte_prestamos,
    reporte_resumen,
    reporte_usuarios,
)

router = APIRouter(tags=["historial-y-reportes"])


@router.get("/historial", response_model=HistorialResponse)
def obtener_historial(
    usuario: UsuarioActual,
    db: Annotated[Session, Depends(get_db)],
    codigo: str | None = None,
    estado: EstadoPrestamo | None = None,
    limite: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    """Historial propio, o el de cualquier usuario (por `codigo`) si quien pide es admin."""
    if codigo is None:
        objetivo_id = usuario.id
    else:
        if not usuario.tiene_rol(Rol.ADMINISTRADOR_SISTEMA):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Solo puedes ver tu propio historial"
            )
        objetivo = db.scalar(select(Usuario).where(Usuario.codigo == codigo.strip()))
        if objetivo is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
        objetivo_id = objetivo.id
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
    "/reportes/recursos/{codigo}/historial",
    response_model=HistorialRecursoResponse,
    dependencies=[
        Depends(require_role(Rol.ADMINISTRADOR_SISTEMA, Rol.CUSTODIO_CE, Rol.CUSTODIO_INFRA))
    ],
)
def obtener_historial_recurso(
    codigo: str,
    usuario: UsuarioActual,
    db: Annotated[Session, Depends(get_db)],
    limite: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    """Historial de préstamos de un recurso: si volvió dañado o perdido, y cuándo.

    El administrador ve cualquier recurso; cada custodio, solo los de su
    propio gestor (misma regla que `recurso.py`, vía `Usuario.puede_gestionar`).
    """
    recurso = db.scalar(select(Recurso).where(Recurso.codigo == codigo.strip()))
    if recurso is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso no encontrado")
    if not usuario.puede_gestionar(recurso.gestor):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Solo puedes ver el historial de recursos de tu propio gestor"
        )
    try:
        return historial_recurso(db, recurso_id=recurso.id, limite=limite, offset=offset)
    except RecursoNoEncontrado as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e


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
    "/reportes/prestamos/evolucion",
    response_model=EvolucionPrestamos,
    dependencies=[Depends(require_role(Rol.ADMINISTRADOR_SISTEMA))],
)
def obtener_evolucion_prestamos(
    db: Annotated[Session, Depends(get_db)],
    desde: date | None = None,
    hasta: date | None = None,
) -> dict:
    try:
        return evolucion_prestamos(db, desde=desde, hasta=hasta)
    except RangoInvalido as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from e


@router.get(
    "/reportes/resumen",
    response_model=ReporteResumen,
    dependencies=[Depends(require_role(Rol.ADMINISTRADOR_SISTEMA))],
)
def obtener_reporte_resumen(db: Annotated[Session, Depends(get_db)]) -> dict:
    return reporte_resumen(db)


@router.get(
    "/reportes/usuarios",
    response_model=ReporteUsuarios,
    dependencies=[Depends(require_role(Rol.ADMINISTRADOR_SISTEMA))],
)
def obtener_reporte_usuarios(db: Annotated[Session, Depends(get_db)]) -> dict:
    return reporte_usuarios(db)
