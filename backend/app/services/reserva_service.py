"""Reglas de negocio de reservas (RF2, issue #25)."""

import re
from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.enums import EstadoRecurso, EstadoReserva, TipoPrestamo, TipoRecurso
from ..models.recurso import Recurso
from ..models.reserva import Reserva
from .invariantes import (
    ZONA_LIMA,
    FueraDeHorarioLaboral,
    validar_dia_laboral,
    validar_hora_laboral,
)
from .sancion_service import mensaje_bloqueo, sancion_bloqueante


class ErrorReserva(Exception):
    """Error de negocio relacionado con una reserva."""


class ConflictoReserva(ErrorReserva):
    """La operación contradice una regla de negocio."""


class ReservaNoEncontrada(ErrorReserva):
    """No se encontró el recurso indicado para la reserva."""


_FORMATO_FRANJA = re.compile(
    r"(?P<inicio>(?:[01][0-9]|2[0-3]):[0-5][0-9])-"
    r"(?P<fin>(?:[01][0-9]|2[0-3]):[0-5][0-9])"
)


def validar_fecha_franja(
    fecha: date, franja: str, *, ahora: datetime | None = None
) -> str:
    """Valida una reserva futura y devuelve la franja normalizada."""
    ahora = ahora or datetime.now(ZONA_LIMA)
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
    # Centro de Estudiantes e Infraestructura no atienden fines de semana ni
    # fuera de 8:00-19:00: no tiene sentido dejar reservar una franja que
    # nadie va a poder confirmar ni entregar.
    try:
        validar_dia_laboral(fecha)
        validar_hora_laboral(inicio, fin)
    except FueraDeHorarioLaboral as e:
        raise ConflictoReserva(str(e)) from e
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
    sancion = sancion_bloqueante(db, usuario_id)
    if sancion is not None:
        raise ConflictoReserva(mensaje_bloqueo(sancion))


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
    if recurso is None:
        raise ReservaNoEncontrada("Recurso no encontrado")
    if recurso.estado == EstadoRecurso.MANTENIMIENTO:
        raise ConflictoReserva("Un recurso en mantenimiento no se puede reservar")
    _validar_tipo_recurso(tipo, recurso)

    duplicada = db.scalar(
        select(Reserva.id)
        .where(
            Reserva.usuario_id == usuario_id,
            Reserva.recurso_id == recurso_id,
            Reserva.fecha == fecha,
            Reserva.franja == franja,
            Reserva.estado.in_((EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA)),
        )
        .limit(1)
    )
    if duplicada is not None:
        raise ConflictoReserva(
            "Ya tienes una reserva activa para este recurso, fecha y franja"
        )

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
