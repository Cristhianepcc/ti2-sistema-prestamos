"""Tests de GET /api/historial (RF6, nivel 1)."""
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_db
from app.models import EstadoPrestamo, ModalidadUso, Prestamo, Rol, TipoPrestamo, TipoRecurso
from app.routers.reporte import router as reporte_router
from app.security import create_access_token
from .helpers import crear_recurso, crear_usuario

AHORA = datetime.now(timezone.utc)


def cliente(db_session, actor=None):
    app = FastAPI()
    app.include_router(reporte_router, prefix="/api")

    def reemplazar_db():
        yield db_session

    app.dependency_overrides[get_db] = reemplazar_db
    headers = {}
    if actor is not None:
        token = create_access_token(subject=str(actor.id), roles=[])
        headers["Authorization"] = f"Bearer {token}"
    return TestClient(app, headers=headers)


def crear_actor(db_session, sufijo, *roles):
    usuario = crear_usuario(db_session, sufijo)
    usuario.roles.extend(roles)
    db_session.commit()
    return usuario


def _crear_prestamo(db, *, recurso, prestatario, registrador, **extra):
    prestamo = Prestamo(
        recurso_id=recurso.id,
        prestatario_id=prestatario.id,
        registrado_por_id=registrador.id,
        estado=extra.pop("estado", EstadoPrestamo.ACTIVO),
        tipo_prestamo=extra.pop("tipo_prestamo", TipoPrestamo.SIMPLE),
        modalidad_uso=extra.pop("modalidad_uso", ModalidadUso.RETIRO_TEMPORAL),
        fecha_entrega=extra.pop("fecha_entrega", AHORA),
        fecha_limite=extra.pop("fecha_limite", AHORA + timedelta(days=7)),
        fecha_devolucion=extra.pop("fecha_devolucion", None),
    )
    db.add(prestamo)
    db.commit()
    return prestamo


def test_usuario_ve_su_propio_historial(db_session):
    usuario = crear_actor(db_session, "HAPI-PROPIO", Rol.ESTUDIANTE)
    registrador = crear_usuario(db_session, "HAPI-REG")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "HAPI-PROPIO")
    _crear_prestamo(db_session, recurso=recurso, prestatario=usuario, registrador=registrador)

    respuesta = cliente(db_session, usuario).get("/api/historial")

    assert respuesta.status_code == 200
    assert respuesta.json()["total"] == 1


def test_no_puede_ver_el_historial_de_otro_sin_ser_admin(db_session):
    usuario = crear_actor(db_session, "HAPI-A", Rol.ESTUDIANTE)
    otro = crear_actor(db_session, "HAPI-B", Rol.ESTUDIANTE)

    respuesta = cliente(db_session, usuario).get(
        "/api/historial", params={"codigo": otro.codigo}
    )

    assert respuesta.status_code == 403


def test_admin_ve_el_historial_de_cualquier_usuario(db_session):
    admin = crear_actor(db_session, "HAPI-ADMIN", Rol.ADMINISTRADOR_SISTEMA)
    otro = crear_actor(db_session, "HAPI-OTRO", Rol.ESTUDIANTE)
    registrador = crear_usuario(db_session, "HAPI-ADMIN-REG")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "HAPI-ADMIN")
    _crear_prestamo(db_session, recurso=recurso, prestatario=otro, registrador=registrador)

    respuesta = cliente(db_session, admin).get(
        "/api/historial", params={"codigo": otro.codigo}
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["total"] == 1


def test_admin_puede_ver_historial_de_un_custodio(db_session):
    """Un custodio nunca es `prestatario_id` en el flujo normal, pero su
    historial (vía código) debe igual poder consultarse y dar vacío, no 404."""
    admin = crear_actor(db_session, "HAPI-ADMIN2", Rol.ADMINISTRADOR_SISTEMA)
    custodio = crear_actor(db_session, "HAPI-CUST", Rol.CUSTODIO_CE)

    respuesta = cliente(db_session, admin).get(
        "/api/historial", params={"codigo": custodio.codigo}
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["total"] == 0


def test_codigo_inexistente_recibe_404(db_session):
    admin = crear_actor(db_session, "HAPI-404", Rol.ADMINISTRADOR_SISTEMA)

    respuesta = cliente(db_session, admin).get(
        "/api/historial", params={"codigo": "NO-EXISTE"}
    )

    assert respuesta.status_code == 404


def test_sin_token_recibe_401(db_session):
    respuesta = cliente(db_session).get("/api/historial")

    assert respuesta.status_code == 401


def test_pagina_y_filtra_por_estado(db_session):
    usuario = crear_actor(db_session, "HAPI-PAG", Rol.ESTUDIANTE)
    registrador = crear_usuario(db_session, "HAPI-PAG-REG")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "HAPI-PAG")
    for i in range(3):
        _crear_prestamo(
            db_session,
            recurso=recurso,
            prestatario=usuario,
            registrador=registrador,
            estado=EstadoPrestamo.DEVUELTO,
            fecha_entrega=AHORA - timedelta(days=i),
            fecha_devolucion=AHORA,
        )
    _crear_prestamo(
        db_session,
        recurso=recurso,
        prestatario=usuario,
        registrador=registrador,
        estado=EstadoPrestamo.ACTIVO,
    )
    client = cliente(db_session, usuario)

    pagina = client.get("/api/historial", params={"limite": 2, "offset": 0}).json()
    assert pagina["total"] == 4
    assert len(pagina["items"]) == 2

    solo_devueltos = client.get("/api/historial", params={"estado": "DEVUELTO"}).json()
    assert solo_devueltos["total"] == 3
