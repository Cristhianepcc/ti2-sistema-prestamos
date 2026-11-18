from datetime import datetime, timedelta, timezone

import pytest

from app.models import (
    EstadoPrestamo,
    EstadoRecurso,
    ModalidadUso,
    TipoPrestamo,
    TipoRecurso,
)
from app.services.invariantes import ZONA_LIMA
from app.services.prestamo_service import (
    ConflictoPrestamo,
    crear_prestamo,
    registrar_devolucion,
)
from .helpers import crear_recurso, crear_usuario

# Martes 10:00 Lima: dentro del horario de Centro de Estudiantes/Infraestructura
# (8:00-19:00, lunes a viernes), para que estos tests no dependan de la hora
# real en que corre la suite.
AHORA_LABORAL = datetime(2026, 6, 9, 10, 0, tzinfo=ZONA_LIMA)


def test_crea_prestamo_y_actualiza_estado_del_recurso(db_session):
    prestatario = crear_usuario(db_session, "PRESTATARIO")
    custodio = crear_usuario(db_session, "CUSTODIO")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "PRESTAMO")

    prestamo = crear_prestamo(
        db_session,
        recurso_id=recurso.id,
        prestatario_id=prestatario.id,
        registrado_por_id=custodio.id,
        tipo_prestamo=TipoPrestamo.SIMPLE,
        modalidad_uso=ModalidadUso.EN_SITIO,
        ahora=AHORA_LABORAL,
    )

    assert prestamo.estado == EstadoPrestamo.ACTIVO
    assert recurso.estado == EstadoRecurso.PRESTADO


def test_devolucion_libera_el_recurso(db_session):
    prestatario = crear_usuario(db_session, "DEVOLUCION")
    custodio = crear_usuario(db_session, "CUSTODIODEV")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "DEVOLUCION")
    prestamo = crear_prestamo(
        db_session,
        recurso_id=recurso.id,
        prestatario_id=prestatario.id,
        registrado_por_id=custodio.id,
        tipo_prestamo=TipoPrestamo.SIMPLE,
        modalidad_uso=ModalidadUso.EN_SITIO,
        ahora=AHORA_LABORAL,
    )

    devuelto = registrar_devolucion(db_session, prestamo_id=prestamo.id)

    assert devuelto.estado == EstadoPrestamo.DEVUELTO
    assert recurso.estado == EstadoRecurso.DISPONIBLE


def test_no_permite_que_el_custodio_se_registre_a_si_mismo(db_session):
    usuario = crear_usuario(db_session, "MISMO")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "MISMO")

    with pytest.raises(ConflictoPrestamo, match="no puede ser el prestatario"):
        crear_prestamo(
            db_session,
            recurso_id=recurso.id,
            prestatario_id=usuario.id,
            registrado_por_id=usuario.id,
            tipo_prestamo=TipoPrestamo.SIMPLE,
            modalidad_uso=ModalidadUso.EN_SITIO,
            ahora=AHORA_LABORAL,
        )


def test_prestamo_excepcional_exige_retiro_temporal(db_session):
    prestatario = crear_usuario(db_session, "EXCEPCIONAL")
    custodio = crear_usuario(db_session, "CUSTODIOEX")
    recurso = crear_recurso(db_session, TipoRecurso.ACADEMICO, "EXCEPCIONAL")

    with pytest.raises(ConflictoPrestamo, match="RETIRO_TEMPORAL"):
        crear_prestamo(
            db_session,
            recurso_id=recurso.id,
            prestatario_id=prestatario.id,
            registrado_por_id=custodio.id,
            tipo_prestamo=TipoPrestamo.EXCEPCIONAL,
            modalidad_uso=ModalidadUso.EN_SITIO,
            fecha_limite=datetime.now(timezone.utc) + timedelta(days=2),
            ahora=AHORA_LABORAL,
        )


# --- Horario de atención (sábado/domingo, 8:00-19:00) -------------------------


@pytest.mark.parametrize(
    "ahora",
    [
        datetime(2026, 6, 13, 10, 0, tzinfo=ZONA_LIMA),  # sábado
        datetime(2026, 6, 14, 10, 0, tzinfo=ZONA_LIMA),  # domingo
        datetime(2026, 6, 9, 7, 59, tzinfo=ZONA_LIMA),  # martes, antes de abrir
        datetime(2026, 6, 9, 19, 0, tzinfo=ZONA_LIMA),  # martes, justo al cerrar
    ],
)
def test_crear_prestamo_fuera_de_horario_laboral_es_rechazado(db_session, ahora):
    prestatario = crear_usuario(db_session, f"HORARIO-USR-{ahora.hour}{ahora.day}")
    custodio = crear_usuario(db_session, f"HORARIO-REG-{ahora.hour}{ahora.day}")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, f"HOR-{ahora.hour}{ahora.day}")

    with pytest.raises(ConflictoPrestamo, match="Centro de Estudiantes"):
        crear_prestamo(
            db_session,
            recurso_id=recurso.id,
            prestatario_id=prestatario.id,
            registrado_por_id=custodio.id,
            tipo_prestamo=TipoPrestamo.SIMPLE,
            modalidad_uso=ModalidadUso.EN_SITIO,
            ahora=ahora,
        )
    # El recurso no debe quedar marcado como prestado si la entrega se rechazó.
    assert recurso.estado == EstadoRecurso.DISPONIBLE


# --- fecha_limite nunca cae sábado/domingo -------------------------------------


def test_fecha_limite_por_curso_corre_a_lunes_si_cae_sabado(db_session):
    # Viernes 2026-06-12 + 1 día = sábado 2026-06-13 -> debe correr al lunes 15.
    viernes = datetime(2026, 6, 12, 10, 0, tzinfo=ZONA_LIMA)
    prestatario = crear_usuario(db_session, "LIMITE-POC-USR")
    custodio = crear_usuario(db_session, "LIMITE-POC-REG")
    recurso = crear_recurso(db_session, TipoRecurso.ACADEMICO, "LIMITE-POC")

    prestamo = crear_prestamo(
        db_session,
        recurso_id=recurso.id,
        prestatario_id=prestatario.id,
        registrado_por_id=custodio.id,
        tipo_prestamo=TipoPrestamo.POR_CURSO,
        modalidad_uso=ModalidadUso.EN_SITIO,
        ahora=viernes,
    )

    assert prestamo.fecha_limite.date() == datetime(2026, 6, 15).date()
    assert prestamo.fecha_limite.weekday() == 0  # lunes
    assert prestamo.fecha_limite.time() == viernes.timetz().replace(tzinfo=None)


def test_fecha_limite_excepcional_corre_a_lunes_si_cae_sabado(db_session):
    # Miércoles 2026-06-10 + 3 días = sábado 2026-06-13 -> debe correr al lunes 15.
    miercoles = datetime(2026, 6, 10, 14, 0, tzinfo=ZONA_LIMA)
    prestatario = crear_usuario(db_session, "LIMITE-EXC-USR")
    custodio = crear_usuario(db_session, "LIMITE-EXC-REG")
    recurso = crear_recurso(db_session, TipoRecurso.ACADEMICO, "LIMITE-EXC")

    prestamo = crear_prestamo(
        db_session,
        recurso_id=recurso.id,
        prestatario_id=prestatario.id,
        registrado_por_id=custodio.id,
        tipo_prestamo=TipoPrestamo.EXCEPCIONAL,
        modalidad_uso=ModalidadUso.RETIRO_TEMPORAL,
        ahora=miercoles,
    )

    assert prestamo.fecha_limite.date() == datetime(2026, 6, 15).date()
    assert prestamo.fecha_limite.weekday() == 0  # lunes


def test_fecha_limite_libro_simple_nunca_necesita_correccion(db_session):
    # +7 días siempre cae el mismo día de semana que la entrega (lun-vie), así
    # que nunca debería necesitar correrse.
    martes = datetime(2026, 6, 9, 10, 0, tzinfo=ZONA_LIMA)
    prestatario = crear_usuario(db_session, "LIMITE-LIB-USR")
    custodio = crear_usuario(db_session, "LIMITE-LIB-REG")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "LIMITE-LIB")

    prestamo = crear_prestamo(
        db_session,
        recurso_id=recurso.id,
        prestatario_id=prestatario.id,
        registrado_por_id=custodio.id,
        tipo_prestamo=TipoPrestamo.SIMPLE,
        modalidad_uso=ModalidadUso.EN_SITIO,
        ahora=martes,
    )

    assert prestamo.fecha_limite.weekday() == martes.weekday()
