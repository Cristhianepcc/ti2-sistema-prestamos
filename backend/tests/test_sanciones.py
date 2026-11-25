from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import get_db
from app.models import (
    EstadoRecurso,
    EstadoPrestamo,
    Gestor,
    ModalidadUso,
    MotivoSancion,
    Prestamo,
    Recurso,
    Rol,
    Sancion,
    TipoPrestamo,
    TipoRecurso,
    TipoSolicitud,
)
from app.routers.sancion import router as sancion_router
from app.security import create_access_token
from app.services.prestamo_service import (
    ConflictoPrestamo,
    PermisoPrestamo,
    crear_prestamo,
    registrar_devolucion,
)
from app.services.reserva_service import ConflictoReserva, crear_reserva
from app.services.sancion_service import (
    ConflictoSancion,
    PermisoSancion,
    resolver_sancion,
    sancion_bloqueante,
)
from app.services.solicitud_service import ConflictoSolicitud, crear_solicitud
from app.services.invariantes import ZONA_LIMA
from .helpers import crear_recurso, crear_usuario

AHORA = datetime(2026, 6, 9, 10, 0, tzinfo=ZONA_LIMA)


def actor(db, sufijo, *roles):
    usuario = crear_usuario(db, sufijo)
    usuario.roles.extend(roles)
    db.commit()
    return usuario


def prestamo_ejemplo(db, sufijo, *, fecha_limite=None, tipo=TipoRecurso.LIBRO):
    prestatario = crear_usuario(db, f"{sufijo}-PREST")
    custodio = actor(db, f"{sufijo}-CUST", Rol.CUSTODIO_CE)
    recurso = crear_recurso(db, tipo, sufijo)
    prestamo = crear_prestamo(
        db,
        recurso_id=recurso.id,
        prestatario_id=prestatario.id,
        registrado_por_id=custodio.id,
        tipo_prestamo=TipoPrestamo.SIMPLE if tipo != TipoRecurso.ACADEMICO else TipoPrestamo.POR_CURSO,
        modalidad_uso=ModalidadUso.EN_SITIO,
        fecha_limite=fecha_limite or AHORA + timedelta(days=2),
        ahora=AHORA,
    )
    return prestatario, custodio, recurso, prestamo


def cliente(db, usuario):
    app = FastAPI()
    app.include_router(sancion_router, prefix="/api")

    def reemplazar_db():
        yield db

    app.dependency_overrides[get_db] = reemplazar_db
    token = create_access_token(subject=str(usuario.id), roles=[])
    return TestClient(app, headers={"Authorization": f"Bearer {token}"})


def test_devolucion_tardia_y_danada_crea_dos_sanciones(db_session):
    prestatario, custodio, recurso, prestamo = prestamo_ejemplo(
        db_session, "DOS-CAUSAS", fecha_limite=AHORA - timedelta(hours=1)
    )

    registrar_devolucion(
        db_session,
        prestamo_id=prestamo.id,
        danado=True,
        actor_usuario_id=custodio.id,
        ahora=AHORA,
    )

    sanciones = db_session.scalars(
        select(Sancion).where(Sancion.prestamo_id == prestamo.id)
    ).all()
    por_motivo = {s.motivo: s for s in sanciones}
    assert set(por_motivo) == {MotivoSancion.DANIO, MotivoSancion.RETRASO}
    assert por_motivo[MotivoSancion.DANIO].fin is None
    assert por_motivo[MotivoSancion.DANIO].activa is True
    retraso = por_motivo[MotivoSancion.RETRASO]
    assert retraso.fin - retraso.inicio == timedelta(hours=72)
    assert "después del plazo" in retraso.detalle
    assert retraso.eventos[0].actor_usuario_id == custodio.id
    assert prestamo.danado is True
    assert prestamo.perdido is False
    assert recurso.estado == EstadoRecurso.MANTENIMIENTO


def test_perdida_prevalece_sobre_danio_y_retraso_se_guarda_aparte(db_session):
    prestatario, custodio, recurso, prestamo = prestamo_ejemplo(
        db_session, "PERDIDA-TARDE", fecha_limite=AHORA - timedelta(days=1)
    )

    registrar_devolucion(
        db_session,
        prestamo_id=prestamo.id,
        danado=True,
        perdido=True,
        actor_usuario_id=custodio.id,
        ahora=AHORA,
    )

    motivos = set(
        db_session.scalars(
            select(Sancion.motivo).where(Sancion.prestamo_id == prestamo.id)
        ).all()
    )
    assert motivos == {MotivoSancion.PERDIDA, MotivoSancion.RETRASO}
    assert prestamo.danado is True
    assert prestamo.perdido is True
    assert recurso.estado == EstadoRecurso.BAJA


def test_devolucion_normal_no_crea_sancion(db_session):
    _, _, _, prestamo = prestamo_ejemplo(db_session, "NORMAL")

    registrar_devolucion(db_session, prestamo_id=prestamo.id, ahora=AHORA)

    assert db_session.scalar(select(Sancion.id).where(Sancion.prestamo_id == prestamo.id)) is None


def test_sancion_por_retraso_vence_automaticamente_a_las_72_horas(db_session):
    prestatario, custodio, _, prestamo = prestamo_ejemplo(
        db_session, "VENCE", fecha_limite=AHORA - timedelta(minutes=1)
    )
    registrar_devolucion(
        db_session,
        prestamo_id=prestamo.id,
        actor_usuario_id=custodio.id,
        ahora=AHORA,
    )
    sancion = db_session.scalar(select(Sancion).where(Sancion.prestamo_id == prestamo.id))

    assert sancion_bloqueante(db_session, prestatario.id, ahora=AHORA + timedelta(hours=71)) is not None
    assert sancion_bloqueante(db_session, prestatario.id, ahora=AHORA + timedelta(hours=72)) is None
    assert sancion.activa is False
    assert [e.tipo for e in sancion.eventos] == ["REGISTRADA", "VENCIDA"]


def test_sancion_activa_bloquea_reserva_solicitud_y_prestamo(db_session):
    prestatario, custodio, _, prestamo = prestamo_ejemplo(db_session, "BLOQUEO")
    registrar_devolucion(
        db_session,
        prestamo_id=prestamo.id,
        danado=True,
        actor_usuario_id=custodio.id,
        ahora=AHORA,
    )

    recurso_prestado = crear_recurso(
        db_session, TipoRecurso.LIBRO, "BLOQUEO-RESERVA", estado=EstadoRecurso.PRESTADO
    )
    fecha = datetime.now(ZONA_LIMA).date() + timedelta(days=3)
    while fecha.weekday() >= 5:
        fecha += timedelta(days=1)
    with pytest.raises(ConflictoReserva, match="sanción activa"):
        crear_reserva(
            db_session,
            usuario_id=prestatario.id,
            recurso_id=recurso_prestado.id,
            fecha=fecha,
            franja="10:00-11:00",
        )

    recurso_solicitud = crear_recurso(db_session, TipoRecurso.LIBRO, "BLOQUEO-SOLICITUD")
    with pytest.raises(ConflictoSolicitud, match="sanción activa"):
        crear_solicitud(
            db_session,
            solicitante_id=prestatario.id,
            recurso_id=recurso_solicitud.id,
            tipo_solicitud=TipoSolicitud.SIMPLE,
        )

    recurso_prestamo = crear_recurso(db_session, TipoRecurso.LIBRO, "BLOQUEO-PRESTAMO")
    custodio_nuevo = actor(db_session, "BLOQUEO-CUST-NUEVO", Rol.CUSTODIO_CE)
    with pytest.raises(ConflictoPrestamo, match="sanción activa"):
        crear_prestamo(
            db_session,
            recurso_id=recurso_prestamo.id,
            prestatario_id=prestatario.id,
            registrado_por_id=custodio_nuevo.id,
            tipo_prestamo=TipoPrestamo.SIMPLE,
            modalidad_uso=ModalidadUso.EN_SITIO,
            ahora=AHORA,
        )


def test_reparacion_resuelve_sancion_y_deja_evento(db_session):
    prestatario, custodio, recurso, prestamo = prestamo_ejemplo(db_session, "REPARAR")
    registrar_devolucion(
        db_session,
        prestamo_id=prestamo.id,
        danado=True,
        actor_usuario_id=custodio.id,
        ahora=AHORA,
    )
    sancion = db_session.scalar(select(Sancion).where(Sancion.prestamo_id == prestamo.id))

    resuelta = resolver_sancion(
        db_session,
        sancion_id=sancion.id,
        actor_id=custodio.id,
        detalle="Se cambió la pieza dañada y se probó el equipo.",
        ahora=AHORA + timedelta(hours=4),
    )

    assert resuelta.activa is False
    assert recurso.estado == EstadoRecurso.DISPONIBLE
    assert resuelta.eventos[-1].tipo == "REPARACION_REGISTRADA"
    assert resuelta.eventos[-1].actor_usuario_id == custodio.id
    assert sancion_bloqueante(db_session, prestatario.id, ahora=AHORA + timedelta(hours=5)) is None


def test_perdida_exige_recurso_de_reposicion_y_lo_registra(db_session):
    _, custodio, recurso, prestamo = prestamo_ejemplo(db_session, "REPONER")
    registrar_devolucion(
        db_session,
        prestamo_id=prestamo.id,
        perdido=True,
        actor_usuario_id=custodio.id,
        ahora=AHORA,
    )
    sancion = db_session.scalar(select(Sancion).where(Sancion.prestamo_id == prestamo.id))

    with pytest.raises(ConflictoSancion, match="ejemplar de reposición"):
        resolver_sancion(
            db_session,
            sancion_id=sancion.id,
            actor_id=custodio.id,
            detalle="La reposición se ingresó.",
            ahora=AHORA + timedelta(hours=1),
        )

    reposicion = crear_recurso(db_session, TipoRecurso.LIBRO, "REPONER-NUEVO")
    resuelta = resolver_sancion(
        db_session,
        sancion_id=sancion.id,
        actor_id=custodio.id,
        detalle="Nuevo ejemplar registrado en inventario.",
        recurso_reposicion_id=reposicion.id,
        ahora=AHORA + timedelta(hours=2),
    )

    assert resuelta.activa is False
    assert recurso.estado == EstadoRecurso.BAJA
    assert resuelta.eventos[-1].recurso_reposicion_id == reposicion.id

    _, segundo_custodio, _, segundo_prestamo = prestamo_ejemplo(
        db_session, "REPONER-SEGUNDO"
    )
    registrar_devolucion(
        db_session,
        prestamo_id=segundo_prestamo.id,
        perdido=True,
        actor_usuario_id=segundo_custodio.id,
        ahora=AHORA,
    )
    segunda_sancion = db_session.scalar(
        select(Sancion).where(Sancion.prestamo_id == segundo_prestamo.id)
    )
    with pytest.raises(ConflictoSancion, match="ya fue usado como reposición"):
        resolver_sancion(
            db_session,
            sancion_id=segunda_sancion.id,
            actor_id=segundo_custodio.id,
            detalle="Intento de reutilizar la misma reposición.",
            recurso_reposicion_id=reposicion.id,
            ahora=AHORA + timedelta(hours=3),
        )


def test_custodio_no_puede_resolver_sancion_de_otro_gestor(db_session):
    _, _, _, prestamo = prestamo_ejemplo(db_session, "OTRO-GESTOR")
    infra = actor(db_session, "CUST-INFRA", Rol.CUSTODIO_INFRA)
    registrar_devolucion(
        db_session,
        prestamo_id=prestamo.id,
        danado=True,
        ahora=AHORA,
    )
    sancion = db_session.scalar(select(Sancion).where(Sancion.prestamo_id == prestamo.id))

    with pytest.raises(PermisoSancion, match="no administra"):
        resolver_sancion(
            db_session,
            sancion_id=sancion.id,
            actor_id=infra.id,
            detalle="No corresponde a mi gestor.",
        )


def test_custodio_no_puede_registrar_devolucion_de_otro_gestor(db_session):
    _, _, recurso, prestamo = prestamo_ejemplo(db_session, "DEVOLUCION-GESTOR")
    custodio_infra = actor(db_session, "DEVOLUCION-INFRA", Rol.CUSTODIO_INFRA)

    with pytest.raises(PermisoPrestamo, match="no administra"):
        registrar_devolucion(
            db_session,
            prestamo_id=prestamo.id,
            danado=True,
            actor_usuario_id=custodio_infra.id,
            ahora=AHORA,
        )

    assert prestamo.estado.value == "ACTIVO"
    assert recurso.estado == EstadoRecurso.PRESTADO


def test_api_custodio_registra_sancion_y_usuario_solo_ve_la_propia(db_session):
    prestatario, custodio, _, prestamo = prestamo_ejemplo(
        db_session, "API", fecha_limite=AHORA - timedelta(minutes=1)
    )
    prestamo.estado = EstadoPrestamo.DEVUELTO
    prestamo.fecha_devolucion = AHORA
    db_session.commit()
    otro = crear_usuario(db_session, "API-OTRO")
    api_custodio = cliente(db_session, custodio)
    api_usuario = cliente(db_session, prestatario)
    api_otro = cliente(db_session, otro)

    creada = api_custodio.post(
        "/api/sanciones",
        json={
            "prestamo_id": prestamo.id,
            "motivo": "RETRASO",
            "detalle": "Registro de retraso de un caso anterior.",
        },
    )
    assert creada.status_code == 201, creada.text
    assert creada.json()["motivo"] == "RETRASO"
    assert creada.json()["usuario_id"] == prestatario.id
    assert len(api_usuario.get("/api/sanciones?mias=true").json()) == 1
    assert api_otro.get("/api/sanciones?mias=true").json() == []
    assert len(api_custodio.get("/api/sanciones").json()) == 1
    assert api_usuario.post(
        "/api/sanciones",
        json={"prestamo_id": prestamo.id, "motivo": "DANIO", "detalle": "No autorizado"},
    ).status_code == 403
