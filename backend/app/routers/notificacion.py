"""Endpoints privados para consultar y marcar notificaciones propias."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.notificacion import Notificacion
from ..schemas.notificacion import NotificacionPublica, NotificacionUpdate
from ..security import UsuarioActual

router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])


@router.get("", response_model=list[NotificacionPublica])
def listar(
    usuario: UsuarioActual,
    db: Annotated[Session, Depends(get_db)],
    leidas: bool | None = Query(default=None),
) -> list[Notificacion]:
    """Lista únicamente las notificaciones del usuario autenticado."""
    consulta = select(Notificacion).where(Notificacion.usuario_id == usuario.id)
    if leidas is not None:
        consulta = consulta.where(Notificacion.leida.is_(leidas))
    consulta = consulta.order_by(
        Notificacion.created_at.desc(), Notificacion.id.desc()
    )
    return list(db.scalars(consulta))


@router.patch("/{notificacion_id}", response_model=NotificacionUpdate)
def marcar_leida(
    notificacion_id: int,
    datos: NotificacionUpdate,
    usuario: UsuarioActual,
    db: Annotated[Session, Depends(get_db)],
) -> NotificacionUpdate:
    """Marca como leída una notificación propia."""
    notificacion = db.get(Notificacion, notificacion_id)
    if notificacion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notificación no encontrada")
    if notificacion.usuario_id != usuario.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Notificación ajena")

    notificacion.leida = datos.leida
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return NotificacionUpdate(leida=notificacion.leida)
