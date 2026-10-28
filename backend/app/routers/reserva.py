"""Endpoints de reservas (RF2, issue #26)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Recurso, Reserva
from ..models.enums import EstadoReserva
from ..schemas.reserva import ReservaCreate, ReservaPublica
from ..security import UsuarioActual
from ..services.reserva_service import ConflictoReserva, crear_reserva

router = APIRouter(prefix="/reservas", tags=["reservas"])


@router.post(
    "",
    response_model=ReservaPublica,
    status_code=status.HTTP_201_CREATED,
)
def crear_reserva_endpoint(
    datos: ReservaCreate,
    usuario: UsuarioActual,
    db: Annotated[Session, Depends(get_db)],
) -> Reserva:
    """Crea una reserva para el usuario autenticado."""
    recurso = db.get(Recurso, datos.recurso_id)
    if recurso is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurso no encontrado",
        )

    if recurso.disponible:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El recurso está disponible y no requiere una reserva",
        )

    try:
        return crear_reserva(
            db,
            usuario_id=usuario.id,
            recurso_id=datos.recurso_id,
            fecha=datos.fecha,
            franja=datos.franja,
            tipo=datos.tipo,
        )
    except ConflictoReserva as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(error)
        ) from error


@router.get("", response_model=list[ReservaPublica])
def listar_mis_reservas(
    usuario: UsuarioActual,
    db: Annotated[Session, Depends(get_db)],
    mias: bool = Query(...),
) -> list[Reserva]:
    """Lista las reservas del usuario autenticado."""
    if not mias:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puedes consultar tus propias reservas",
        )

    consulta = select(Reserva).where(Reserva.usuario_id == usuario.id)
    return list(db.scalars(consulta))


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def cancelar_reserva(
    id: int,
    usuario: UsuarioActual,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Cancela una reserva pendiente si pertenece al usuario autenticado."""
    reserva = db.get(Reserva, id)
    if reserva is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reserva no encontrada",
        )

    if reserva.usuario_id != usuario.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el dueño de la reserva puede cancelarla",
        )

    if reserva.estado != EstadoReserva.PENDIENTE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se pueden cancelar reservas pendientes",
        )

    reserva.estado = EstadoReserva.CANCELADA
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
