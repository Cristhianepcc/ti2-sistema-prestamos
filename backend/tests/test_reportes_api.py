"""Tests de /api/reportes/* (RF6, nivel 1): solo ADMINISTRADOR_SISTEMA."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_db
from app.models import Rol
from app.routers.reporte import router as reporte_router
from app.security import create_access_token
from .helpers import crear_usuario

ENDPOINTS = [
    "/api/reportes/inventario",
    "/api/reportes/prestamos",
    "/api/reportes/resumen",
    "/api/reportes/usuarios",
]


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


@pytest.mark.parametrize("ruta", ENDPOINTS)
def test_admin_recibe_200(db_session, ruta):
    admin = crear_actor(db_session, f"REP-OK-{ruta[-5:]}", Rol.ADMINISTRADOR_SISTEMA)
    respuesta = cliente(db_session, admin).get(ruta)

    assert respuesta.status_code == 200


@pytest.mark.parametrize("ruta", ENDPOINTS)
@pytest.mark.parametrize(
    "rol",
    [Rol.ESTUDIANTE, Rol.DOCENTE, Rol.CUSTODIO_CE, Rol.CUSTODIO_INFRA],
)
def test_rol_no_admin_recibe_403(db_session, ruta, rol):
    sufijo = f"REP-403-{rol.value[:4]}-{ruta[-5:]}"
    usuario = crear_actor(db_session, sufijo, rol)
    respuesta = cliente(db_session, usuario).get(ruta)

    assert respuesta.status_code == 403


@pytest.mark.parametrize("ruta", ENDPOINTS)
def test_sin_token_recibe_401(db_session, ruta):
    respuesta = cliente(db_session).get(ruta)

    assert respuesta.status_code == 401


def test_reporte_prestamos_desde_mayor_que_hasta_recibe_422(db_session):
    admin = crear_actor(db_session, "REP-422-RANGO", Rol.ADMINISTRADOR_SISTEMA)

    respuesta = cliente(db_session, admin).get(
        "/api/reportes/prestamos", params={"desde": "2026-11-10", "hasta": "2026-11-01"}
    )

    assert respuesta.status_code == 422


def test_reporte_prestamos_fecha_invalida_recibe_422(db_session):
    admin = crear_actor(db_session, "REP-422-FECHA", Rol.ADMINISTRADOR_SISTEMA)

    respuesta = cliente(db_session, admin).get(
        "/api/reportes/prestamos", params={"desde": "no-es-una-fecha"}
    )

    assert respuesta.status_code == 422


def test_reporte_prestamos_hasta_futuro_recibe_422(db_session):
    admin = crear_actor(db_session, "REP-422-FUTURO", Rol.ADMINISTRADOR_SISTEMA)

    respuesta = cliente(db_session, admin).get(
        "/api/reportes/prestamos", params={"hasta": "2099-01-01"}
    )

    assert respuesta.status_code == 422
