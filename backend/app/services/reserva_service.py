"""Reglas de negocio de reservas (RF2, issue #25)."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.enums import EstadoReserva, TipoPrestamo, TipoRecurso
from ..models.recurso import Recurso
from ..models.reserva import Reserva


class ErrorReserva(Exception):
    """Error de negocio relacionado con una reserva."""


class ConflictoReserva(ErrorReserva):
    """La operación contradice una regla de negocio."""


# Prioridad híbrida (docs/00-contexto-alcance-propuesta.md §4): por tipo
# primero; dentro del mismo tipo, FIFO por `created_at` (ver
# `listar_cola_reservas`, que ordena por `prioridad DESC, created_at ASC`).
_PRIORIDAD_POR_TIPO = {
    TipoPrestamo.EXCEPCIONAL: 3,
    TipoPrestamo.POR_CURSO: 2,
    TipoPrestamo.SIMPLE: 1,
}


def calcular_prioridad_reserva(tipo: TipoPrestamo) -> int:
    """Prioridad de la reserva según el tipo que la originó."""
    return _PRIORIDAD_POR_TIPO[tipo]


def _validar_tipo_recurso(tipo: TipoPrestamo, recurso: Recurso) -> None:
    """Mismo invariante tipo↔recurso que `prestamo_service.crear_prestamo`:
    sin esto, cualquiera podría mandar `tipo=EXCEPCIONAL` en un libro solo
    para saltarse la cola."""
    if tipo == TipoPrestamo.SIMPLE:
        if recurso.tipo_recurso not in (TipoRecurso.LIBRO, TipoRecurso.DEPORTIVO):
            raise ConflictoReserva(
                "El tipo SIMPLE solo se admite para libros e implementos deportivos"
            )
    elif recurso.tipo_recurso != TipoRecurso.ACADEMICO:
        raise ConflictoReserva(
            "Los tipos POR_CURSO y EXCEPCIONAL solo se admiten para implementos académicos"
        )


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
    tipo: TipoPrestamo = TipoPrestamo.SIMPLE,
) -> Reserva:
    """Crea una reserva pendiente con la prioridad que le corresponde a `tipo`."""
    recurso = db.get(Recurso, recurso_id)
    if recurso is not None:
        _validar_tipo_recurso(tipo, recurso)

    _validar_sancion_activa(db, usuario_id)

    reserva = Reserva(
        usuario_id=usuario_id,
        recurso_id=recurso_id,
        fecha=fecha,
        franja=franja,
        prioridad=calcular_prioridad_reserva(tipo),
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
