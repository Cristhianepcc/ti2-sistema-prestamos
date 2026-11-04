from datetime import datetime, timedelta, timezone

import pytest

from app.models import (
    EstadoPrestamo,
    EstadoRecurso,
    ModalidadUso,
    TipoPrestamo,
    TipoRecurso,
)
from app.services.prestamo_service import (
    ConflictoPrestamo,
    crear_prestamo,
    registrar_devolucion,
)
from .helpers import crear_recurso, crear_usuario


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
        )
