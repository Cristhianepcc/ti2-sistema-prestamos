"""Tests de /api/reportes/* (RF6, nivel 1): solo ADMINISTRADOR_SISTEMA."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_db
from app.models import EstadoPrestamo, ModalidadUso, Prestamo, Rol, TipoPrestamo, TipoRecurso
from app.routers.reporte import router as reporte_router
from app.security import create_access_token
from .helpers import crear_recurso, crear_usuario

AHORA = datetime.now(timezone.utc)

ENDPOINTS = [
    "/api/reportes/inventario",
    "/api/reportes/prestamos",
    "/api/reportes/prestamos/evolucion",
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


def test_evolucion_prestamos_hasta_futuro_recibe_422(db_session):
    admin = crear_actor(db_session, "REP-422-EVOFUT", Rol.ADMINISTRADOR_SISTEMA)

    respuesta = cliente(db_session, admin).get(
        "/api/reportes/prestamos/evolucion", params={"hasta": "2099-01-01"}
    )

    assert respuesta.status_code == 422


# --- GET /api/reportes/recursos/{codigo}/historial ---------------------------


def test_historial_recurso_admin_recibe_200_con_el_danio_marcado(db_session):
    admin = crear_actor(db_session, "REP-RECHIST-OK", Rol.ADMINISTRADOR_SISTEMA)
    prestatario = crear_usuario(db_session, "REP-RECHIST-PREST")
    registrador = crear_usuario(db_session, "REP-RECHIST-REG")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "REP-RECHIST")
    prestamo = Prestamo(
        recurso_id=recurso.id,
        prestatario_id=prestatario.id,
        registrado_por_id=registrador.id,
        estado=EstadoPrestamo.DEVUELTO,
        tipo_prestamo=TipoPrestamo.SIMPLE,
        modalidad_uso=ModalidadUso.RETIRO_TEMPORAL,
        fecha_entrega=AHORA - timedelta(days=5),
        fecha_limite=AHORA + timedelta(days=2),
        fecha_devolucion=AHORA,
        danado=True,
    )
    db_session.add(prestamo)
    db_session.commit()

    respuesta = cliente(db_session, admin).get(f"/api/reportes/recursos/{recurso.codigo}/historial")

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["recurso"]["codigo"] == recurso.codigo
    assert datos["total"] == 1
    assert datos["items"][0]["danado"] is True
    assert datos["items"][0]["perdido"] is False


@pytest.mark.parametrize("rol", [Rol.ESTUDIANTE, Rol.DOCENTE])
def test_historial_recurso_rol_sin_custodia_recibe_403(db_session, rol):
    usuario = crear_actor(db_session, f"REP-RECHIST-403-{rol.value[:4]}", rol)
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, f"REP-RECHIST-403-{rol.value[:4]}")

    respuesta = cliente(db_session, usuario).get(f"/api/reportes/recursos/{recurso.codigo}/historial")

    assert respuesta.status_code == 403


def test_historial_recurso_custodio_ce_ve_el_de_su_gestor(db_session):
    custodio = crear_actor(db_session, "REP-RECHIST-CE-OK", Rol.CUSTODIO_CE)
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "REP-RECHIST-CE-OK")

    respuesta = cliente(db_session, custodio).get(f"/api/reportes/recursos/{recurso.codigo}/historial")

    assert respuesta.status_code == 200


def test_historial_recurso_custodio_infra_ve_el_de_su_gestor(db_session):
    custodio = crear_actor(db_session, "REP-RECHIST-INFRA-OK", Rol.CUSTODIO_INFRA)
    recurso = crear_recurso(db_session, TipoRecurso.ACADEMICO, "REP-RECHIST-INFRA-OK")

    respuesta = cliente(db_session, custodio).get(f"/api/reportes/recursos/{recurso.codigo}/historial")

    assert respuesta.status_code == 200


def test_historial_recurso_custodio_de_otro_gestor_recibe_403(db_session):
    custodio_ce = crear_actor(db_session, "REP-RECHIST-CE-OTRO", Rol.CUSTODIO_CE)
    recurso_academico = crear_recurso(db_session, TipoRecurso.ACADEMICO, "REP-RECHIST-CE-OTRO")

    respuesta = cliente(db_session, custodio_ce).get(
        f"/api/reportes/recursos/{recurso_academico.codigo}/historial"
    )

    assert respuesta.status_code == 403


def test_historial_recurso_sin_token_recibe_401(db_session):
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "REP-RECHIST-401")

    respuesta = cliente(db_session).get(f"/api/reportes/recursos/{recurso.codigo}/historial")

    assert respuesta.status_code == 401


def test_historial_recurso_codigo_inexistente_recibe_404(db_session):
    admin = crear_actor(db_session, "REP-RECHIST-404", Rol.ADMINISTRADOR_SISTEMA)

    respuesta = cliente(db_session, admin).get("/api/reportes/recursos/NO-EXISTE/historial")

    assert respuesta.status_code == 404
