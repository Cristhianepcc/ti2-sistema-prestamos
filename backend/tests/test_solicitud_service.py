from datetime import datetime, timedelta, timezone

import pytest

from app.models import (
    EstadoPrestamo,
    EstadoRecurso,
    EstadoSolicitud,
    ModalidadUso,
    Notificacion,
    Prestamo,
    Rol,
    Solicitud,
    TipoNotificacion,
    TipoPrestamo,
    TipoSolicitud,
    TipoRecurso,
)
from app.services.invariantes import ZONA_LIMA
from app.services.prestamo_service import ConflictoPrestamo
from app.services.solicitud_service import (
    ConflictoSolicitud,
    PermisoSolicitud,
    aceptar_solicitud,
    avalar_solicitud,
    autorizar_solicitud,
    crear_solicitud,
    paso_pendiente,
    rechazar_solicitud,
)
from .helpers import crear_recurso, crear_usuario

# Martes 10:00 Lima: dentro del horario de Centro de Estudiantes/Infraestructura,
# para que aceptar_solicitud/crear_prestamo no dependan de la hora real.
AHORA_LABORAL = datetime(2026, 6, 9, 10, 0, tzinfo=ZONA_LIMA)


def actor(db, sufijo: str, rol: Rol):
    usuario = crear_usuario(db, sufijo)
    usuario.roles.append(rol)
    db.commit()
    return usuario


def test_flujo_por_curso_aval_y_aceptacion_crea_prestamo_y_notificacion(db_session):
    solicitante = crear_usuario(db_session, "SOLICITANTE")
    docente = actor(db_session, "DOCENTE", Rol.DOCENTE)
    custodio = actor(db_session, "INFRA", Rol.CUSTODIO_INFRA)
    recurso = crear_recurso(db_session, TipoRecurso.ACADEMICO, "SOLICITUD")
    solicitud = crear_solicitud(
        db_session,
        solicitante_id=solicitante.id,
        recurso_id=recurso.id,
        tipo_solicitud=TipoSolicitud.POR_CURSO,
        motivo="Práctica de laboratorio",
    )

    assert paso_pendiente(solicitud) == Rol.DOCENTE
    avalada = avalar_solicitud(
        db_session, solicitud_id=solicitud.id, docente_id=docente.id
    )
    assert avalada.estado == EstadoSolicitud.AVALADA
    assert paso_pendiente(avalada) == Rol.CUSTODIO_INFRA

    aceptada = aceptar_solicitud(
        db_session,
        solicitud_id=solicitud.id,
        custodio_id=custodio.id,
        modalidad_uso=ModalidadUso.EN_SITIO,
        fecha_limite=datetime.now(timezone.utc) + timedelta(days=1),
        ahora=AHORA_LABORAL,
    )
    prestamo = db_session.query(Prestamo).filter_by(solicitud_id=solicitud.id).one()
    notificacion = db_session.query(Notificacion).filter_by(solicitud_id=solicitud.id).one()

    assert aceptada.estado == EstadoSolicitud.ACEPTADA
    assert aceptada.aceptado_por_id == custodio.id
    assert aceptada.prestamo_id == prestamo.id
    assert prestamo.prestatario_id == solicitante.id
    assert prestamo.estado == EstadoPrestamo.ACTIVO
    assert recurso.estado == EstadoRecurso.PRESTADO
    assert notificacion.usuario_id == solicitante.id
    assert notificacion.tipo == TipoNotificacion.SOLICITUD_ACEPTADA
    assert "fue aceptada" in notificacion.mensaje


def test_flujo_excepcional_requiere_docente_y_direccion(db_session):
    solicitante = crear_usuario(db_session, "SOL-EXC")
    docente = actor(db_session, "DOC-EXC", Rol.DOCENTE)
    direccion = actor(db_session, "DIR-EXC", Rol.ADMINISTRADOR_SISTEMA)
    custodio = actor(db_session, "INF-EXC", Rol.CUSTODIO_INFRA)
    recurso = crear_recurso(db_session, TipoRecurso.ACADEMICO, "EXC")
    solicitud = crear_solicitud(
        db_session,
        solicitante_id=solicitante.id,
        recurso_id=recurso.id,
        tipo_solicitud=TipoSolicitud.EXCEPCIONAL,
        motivo="Investigación fuera del campus",
    )

    with pytest.raises(ConflictoSolicitud, match="estado AUTORIZADA"):
        aceptar_solicitud(
            db_session,
            solicitud_id=solicitud.id,
            custodio_id=custodio.id,
            modalidad_uso=ModalidadUso.RETIRO_TEMPORAL,
        )
    avalar_solicitud(db_session, solicitud_id=solicitud.id, docente_id=docente.id)
    assert paso_pendiente(solicitud) == Rol.ADMINISTRADOR_SISTEMA
    autorizar_solicitud(
        db_session, solicitud_id=solicitud.id, direccion_id=direccion.id
    )
    assert paso_pendiente(solicitud) == Rol.CUSTODIO_INFRA


def test_rechazo_crea_notificacion_y_guarda_motivo(db_session):
    solicitante = crear_usuario(db_session, "SOL-RECH")
    custodio = actor(db_session, "CE-RECH", Rol.CUSTODIO_CE)
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "RECH")
    solicitud = crear_solicitud(
        db_session,
        solicitante_id=solicitante.id,
        recurso_id=recurso.id,
        tipo_solicitud=TipoSolicitud.SIMPLE,
    )

    rechazada = rechazar_solicitud(
        db_session,
        solicitud_id=solicitud.id,
        usuario_id=custodio.id,
        motivo_rechazo="No se presentó el solicitante",
    )
    notificacion = db_session.query(Notificacion).one()

    assert rechazada.estado == EstadoSolicitud.RECHAZADA
    assert rechazada.motivo_rechazo == "No se presentó el solicitante"
    assert notificacion.usuario_id == solicitante.id
    assert notificacion.tipo == TipoNotificacion.SOLICITUD_RECHAZADA
    assert "No se presentó" in notificacion.mensaje


def test_rechazo_exige_rol_del_turno_o_custodio_correcto(db_session):
    solicitante = crear_usuario(db_session, "SOL-PERM")
    docente = actor(db_session, "DOC-PERM", Rol.DOCENTE)
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "PERM")
    solicitud = crear_solicitud(
        db_session,
        solicitante_id=solicitante.id,
        recurso_id=recurso.id,
        tipo_solicitud=TipoSolicitud.SIMPLE,
    )

    with pytest.raises(PermisoSolicitud):
        rechazar_solicitud(
            db_session, solicitud_id=solicitud.id, usuario_id=docente.id
        )


def test_no_se_puede_avalar_simple_ni_rechazar_una_aceptada(db_session):
    solicitante = crear_usuario(db_session, "SOL-TERMINAL")
    docente = actor(db_session, "DOC-TERMINAL", Rol.DOCENTE)
    custodio = actor(db_session, "CE-TERMINAL", Rol.CUSTODIO_CE)
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "TERMINAL")
    simple = crear_solicitud(
        db_session,
        solicitante_id=solicitante.id,
        recurso_id=recurso.id,
        tipo_solicitud=TipoSolicitud.SIMPLE,
    )

    with pytest.raises(ConflictoSolicitud, match="no requiere aval"):
        avalar_solicitud(db_session, solicitud_id=simple.id, docente_id=docente.id)
    aceptar_solicitud(
        db_session,
        solicitud_id=simple.id,
        custodio_id=custodio.id,
        modalidad_uso=ModalidadUso.RETIRO_TEMPORAL,
        ahora=AHORA_LABORAL,
    )
    with pytest.raises(ConflictoSolicitud, match="ya no puede rechazarse"):
        rechazar_solicitud(
            db_session, solicitud_id=simple.id, usuario_id=custodio.id
        )


def test_aceptacion_fallida_no_deja_solicitud_aceptada_ni_notificacion(db_session):
    solicitante = crear_usuario(db_session, "SOL-DISP")
    custodio = actor(db_session, "CE-DISP", Rol.CUSTODIO_CE)
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "DISP")
    solicitud = crear_solicitud(
        db_session,
        solicitante_id=solicitante.id,
        recurso_id=recurso.id,
        tipo_solicitud=TipoSolicitud.SIMPLE,
    )
    recurso.estado = EstadoRecurso.PRESTADO
    db_session.commit()

    with pytest.raises(ConflictoPrestamo, match="no está disponible"):
        aceptar_solicitud(
            db_session,
            solicitud_id=solicitud.id,
            custodio_id=custodio.id,
            modalidad_uso=ModalidadUso.RETIRO_TEMPORAL,
            ahora=AHORA_LABORAL,
        )

    db_session.refresh(solicitud)
    assert solicitud.estado == EstadoSolicitud.SOLICITADA
    assert db_session.query(Prestamo).count() == 0
    assert db_session.query(Notificacion).count() == 0


def test_aceptar_con_custodio_de_otro_gestor_devuelve_permiso(db_session):
    solicitante = crear_usuario(db_session, "SOL-GESTOR")
    custodio_ce = actor(db_session, "CE-GESTOR", Rol.CUSTODIO_CE)
    recurso = crear_recurso(db_session, TipoRecurso.ACADEMICO, "GESTOR")
    solicitud = crear_solicitud(
        db_session,
        solicitante_id=solicitante.id,
        recurso_id=recurso.id,
        tipo_solicitud=TipoSolicitud.POR_CURSO,
        motivo="Clase",
    )
    docente = actor(db_session, "DOC-GESTOR", Rol.DOCENTE)
    avalar_solicitud(
        db_session, solicitud_id=solicitud.id, docente_id=docente.id
    )

    with pytest.raises(PermisoSolicitud, match="no administra"):
        aceptar_solicitud(
            db_session,
            solicitud_id=solicitud.id,
            custodio_id=custodio_ce.id,
            modalidad_uso=ModalidadUso.EN_SITIO,
        )


def test_devolucion_perdida_saca_recurso_de_disponibilidad(db_session):
    from app.services.prestamo_service import crear_prestamo, registrar_devolucion

    prestatario = crear_usuario(db_session, "PERDIDO-USER")
    custodio = crear_usuario(db_session, "PERDIDO-CUST")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "PERDIDO")
    prestamo = crear_prestamo(
        db_session,
        recurso_id=recurso.id,
        prestatario_id=prestatario.id,
        registrado_por_id=custodio.id,
        tipo_prestamo=TipoPrestamo.SIMPLE,
        modalidad_uso=ModalidadUso.RETIRO_TEMPORAL,
        ahora=AHORA_LABORAL,
    )

    registrar_devolucion(db_session, prestamo_id=prestamo.id, perdido=True)

    assert recurso.estado == EstadoRecurso.MANTENIMIENTO
    assert not recurso.disponible


@pytest.mark.parametrize(
    "estado", [EstadoRecurso.PRESTADO, EstadoRecurso.MANTENIMIENTO]
)
def test_no_crea_solicitud_si_recurso_no_esta_disponible(db_session, estado):
    solicitante = crear_usuario(db_session, f"NO-DISP-{estado.value}")
    recurso = crear_recurso(
        db_session,
        TipoRecurso.LIBRO,
        f"NO-DISP-{estado.value}",
        estado=estado,
    )

    with pytest.raises(ConflictoSolicitud, match="no está disponible"):
        crear_solicitud(
            db_session,
            solicitante_id=solicitante.id,
            recurso_id=recurso.id,
            tipo_solicitud=TipoSolicitud.SIMPLE,
        )

def test_no_permite_segunda_solicitud_activa_del_mismo_usuario_y_recurso(db_session):
    solicitante = crear_usuario(db_session, "DUP-SOL")
    recurso = crear_recurso(db_session, TipoRecurso.ACADEMICO, "DUP")
    crear_solicitud(
        db_session,
        solicitante_id=solicitante.id,
        recurso_id=recurso.id,
        tipo_solicitud=TipoSolicitud.EXCEPCIONAL,
        motivo="tesis",
    )

    with pytest.raises(ConflictoSolicitud, match="Ya tienes una solicitud pendiente"):
        crear_solicitud(
            db_session,
            solicitante_id=solicitante.id,
            recurso_id=recurso.id,
            tipo_solicitud=TipoSolicitud.EXCEPCIONAL,
            motivo="profesión",
        )

    assert db_session.query(Solicitud).count() == 1


def test_otro_usuario_si_puede_solicitar_el_mismo_recurso(db_session):
    uno = crear_usuario(db_session, "DUP-UNO")
    dos = crear_usuario(db_session, "DUP-DOS")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "DUP-OTRO")

    for usuario in (uno, dos):
        crear_solicitud(
            db_session,
            solicitante_id=usuario.id,
            recurso_id=recurso.id,
            tipo_solicitud=TipoSolicitud.SIMPLE,
        )

    assert db_session.query(Solicitud).count() == 2


def test_puede_volver_a_solicitar_si_la_anterior_fue_rechazada(db_session):
    solicitante = crear_usuario(db_session, "DUP-RECH")
    custodio = actor(db_session, "DUP-CE", Rol.CUSTODIO_CE)
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "DUP-RECH")
    primera = crear_solicitud(
        db_session,
        solicitante_id=solicitante.id,
        recurso_id=recurso.id,
        tipo_solicitud=TipoSolicitud.SIMPLE,
    )
    rechazar_solicitud(db_session, solicitud_id=primera.id, usuario_id=custodio.id)

    segunda = crear_solicitud(
        db_session,
        solicitante_id=solicitante.id,
        recurso_id=recurso.id,
        tipo_solicitud=TipoSolicitud.SIMPLE,
    )

    assert segunda.id != primera.id