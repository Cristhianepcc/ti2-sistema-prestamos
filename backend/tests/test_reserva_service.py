from datetime import date, datetime, timedelta, timezone

import pytest

from app.models import TipoPrestamo, TipoRecurso
from app.services.reserva_service import (
    ConflictoReserva,
    crear_reserva,
    listar_cola_reservas,
    validar_fecha_franja,
)
from .helpers import crear_recurso, crear_usuario


def fecha_futura_lima():
    return datetime.now(timezone(timedelta(hours=-5))).date() + timedelta(days=1)


@pytest.mark.parametrize(
    ("tipo_recurso", "tipo_prestamo"),
    [
        (TipoRecurso.LIBRO, TipoPrestamo.SIMPLE),
        (TipoRecurso.DEPORTIVO, TipoPrestamo.SIMPLE),
        (TipoRecurso.ACADEMICO, TipoPrestamo.POR_CURSO),
    ],
)
def test_permite_reservar_los_tres_tipos_de_recurso(
    db_session, tipo_recurso, tipo_prestamo
):
    usuario = crear_usuario(db_session, tipo_recurso.value)
    recurso = crear_recurso(db_session, tipo_recurso, tipo_recurso.value)
    fecha = fecha_futura_lima()

    reserva = crear_reserva(
        db_session,
        usuario_id=usuario.id,
        recurso_id=recurso.id,
        fecha=fecha,
        franja="10:00-12:00",
        tipo=tipo_prestamo,
    )

    assert reserva.recurso_id == recurso.id
    assert reserva.fecha == fecha
    assert reserva.prioridad == 0


def test_rechaza_fecha_pasada():
    ahora = datetime(2026, 6, 10, 12, 0, tzinfo=timezone(timedelta(hours=-5)))
    with pytest.raises(ConflictoReserva, match="fecha pasada"):
        validar_fecha_franja(date(2026, 6, 9), "10:00-12:00", ahora=ahora)


def test_rechaza_hora_de_inicio_pasada_en_el_dia_actual():
    ahora = datetime(2026, 6, 10, 12, 0, tzinfo=timezone(timedelta(hours=-5)))
    with pytest.raises(ConflictoReserva, match="ya comenzó"):
        validar_fecha_franja(date(2026, 6, 10), "10:00-13:00", ahora=ahora)


@pytest.mark.parametrize("franja", ["10-12", "25:00-26:00", "12:00-11:00", "09:00-09:00"])
def test_rechaza_franjas_invalidas(franja):
    ahora = datetime(2026, 6, 10, 12, 0, tzinfo=timezone(timedelta(hours=-5)))
    with pytest.raises(ConflictoReserva):
        validar_fecha_franja(date(2026, 6, 11), franja, ahora=ahora)


def test_atiende_la_cola_en_orden_fifo_sin_prioridad_por_tipo(db_session):
    recurso = crear_recurso(db_session, TipoRecurso.ACADEMICO, "FIFO")
    primero = crear_usuario(db_session, "PRIMERO")
    segundo = crear_usuario(db_session, "SEGUNDO")
    fecha = fecha_futura_lima()

    reserva_primera = crear_reserva(
        db_session,
        usuario_id=primero.id,
        recurso_id=recurso.id,
        fecha=fecha,
        franja="10:00-12:00",
        tipo=TipoPrestamo.POR_CURSO,
    )
    reserva_segunda = crear_reserva(
        db_session,
        usuario_id=segundo.id,
        recurso_id=recurso.id,
        fecha=fecha,
        franja="10:00-12:00",
        tipo=TipoPrestamo.EXCEPCIONAL,
    )

    cola = listar_cola_reservas(db_session, recurso.id)
    assert [reserva.id for reserva in cola] == [reserva_primera.id, reserva_segunda.id]

def test_schema_reserva_acepta_y_rechaza_el_formato_de_franja():
    from pydantic import ValidationError

    from app.schemas.reserva import ReservaCreate

    fecha = fecha_futura_lima()
    solicitud = ReservaCreate(recurso_id=1, fecha=fecha, franja="10:00-12:00")
    assert solicitud.franja == "10:00-12:00"

    with pytest.raises(ValidationError):
        ReservaCreate(recurso_id=1, fecha=fecha, franja="25:00-26:00")