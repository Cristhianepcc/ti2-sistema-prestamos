"""Reglas de negocio de reservas (RF2, issue #25)."""

import re
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.enums import EstadoReserva, TipoPrestamo, TipoRecurso
from ..models.recurso import Recurso
from ..models.reserva import Reserva


class ErrorReserva(Exception):
    """Error de negocio relacionado con una reserva."""


class ConflictoReserva(ErrorReserva):
    """La operación contradice una regla de negocio."""


_ZONA_LIMA = timezone(timedelta(hours=-5))
_FORMATO_FRANJA = re.compile(
    r"(?P<inicio>(?:[01][0-9]|2[0-3]):[0-5][0-9])-"
    r"(?P<fin>(?:[01][0-9]|2[0-3]):[0-5][0-9])"
)


def validar_fecha_franja(
    fecha: date, franja: str, *, ahora: datetime | None = None
) -> str:
    """Valida una reserva futura y devuelve la franja normalizada."""
    ahora = ahora or datetime.now(_ZONA_LIMA)
    franja = franja.strip()
    coincidencia = _FORMATO_FRANJA.fullmatch(franja)
    if coincidencia is None:
        raise ConflictoReserva(
            "La franja debe tener el formato HH:MM-HH:MM en horario de 24 horas"
        )

    inicio = time.fromisoformat(coincidencia.group("inicio"))
    fin = time.fromisoformat(coincidencia.group("fin"))
    if fin <= inicio:
        raise ConflictoReserva("La hora final debe ser posterior a la hora inicial")
    if fecha < ahora.date():
        raise ConflictoReserva("No se puede reservar en una fecha pasada")
    if fecha == ahora.date() and inicio <= ahora.time().replace(tzinfo=None):
        raise ConflictoReserva("No se puede reservar una franja que ya comenzó")
    return franja


def _validar_tipo_recurso(tipo: TipoPrestamo, recurso: Recurso) -> None:
    """Mismo invariante tipo↔recurso que `prestamo_service.crear_prestamo`:
    esto evita asignar a un recurso un tipo de préstamo que no le corresponde."""
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
    """Crea una reserva pendiente tras validar fecha, hora y tipo de recurso."""
    franja = validar_fecha_franja(fecha, franja)
    recurso = db.get(Recurso, recurso_id)
    if recurso is not None:
        _validar_tipo_recurso(tipo, recurso)

    _validar_sancion_activa(db, usuario_id)

    reserva = Reserva(
        usuario_id=usuario_id,
        recurso_id=recurso_id,
        fecha=fecha,
        franja=franja,
        prioridad=0,  # campo legado; la cola se resuelve solo por FIFO.
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
    """Lista reservas pendientes en orden FIFO de creación."""
    consulta = (
        select(Reserva)
        .where(
            Reserva.recurso_id == recurso_id,
            Reserva.estado == EstadoReserva.PENDIENTE,
        )
        .order_by(Reserva.created_at.asc(), Reserva.id.asc())
    )
    return list(db.scalars(consulta))
