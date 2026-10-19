"""Reglas de negocio de reservas (RF2, issue #25)."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.enums import EstadoReserva
from ..models.reserva import Reserva


_PRIORIDAD_RESERVA_ACTUAL = 1


def calcular_prioridad_reserva() -> int:
    """Devuelve la prioridad actual: SIMPLE hasta que exista RF4."""
    return _PRIORIDAD_RESERVA_ACTUAL


def _validar_sancion_activa(db: Session, usuario_id: int) -> None:
    """Punto de extensión para el bloqueo por sanciones de RF5.

    La entidad Sancion aún no existe; por ahora no se aplica el bloqueo.
    """
    # TODO(RF5): comprobar si el usuario tiene una sanción activa y bloquear
    # la reserva cuando se implemente el modelo y servicio de sanciones.
    pass


def crear_reserva(
    db: Session,
    *,
    usuario_id: int,
    recurso_id: int,
    fecha: date,
    franja: str,
) -> Reserva:
    """Crea una reserva pendiente con la prioridad vigente."""
    _validar_sancion_activa(db, usuario_id)

    reserva = Reserva(
        usuario_id=usuario_id,
        recurso_id=recurso_id,
        fecha=fecha,
        franja=franja,
        prioridad=calcular_prioridad_reserva(),
    )
    db.add(reserva)

    try:
        db.commit()
        db.refresh(reserva)
    except Exception:
        db.rollback()
        raise

    return reserva


def listar_cola_reservas(db: Session, recurso_id: int) -> list[Reserva]:
    """Lista las reservas pendientes por prioridad y orden FIFO."""
    consulta = (
        select(Reserva)
        .where(
            Reserva.recurso_id == recurso_id,
            Reserva.estado == EstadoReserva.PENDIENTE,
        )
        .order_by(Reserva.prioridad.desc(), Reserva.created_at.asc())
    )
    return list(db.scalars(consulta))
