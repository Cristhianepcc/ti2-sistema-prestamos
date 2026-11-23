from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_db
from app.models import EstadoRecurso, Rol, TipoRecurso, Usuario
from app.routers.auth import router as auth_router
from app.routers.recurso import router as recurso_router
from app.security import create_access_token
from .helpers import crear_recurso, crear_usuario


def crear_cliente(db_session, actor: Usuario | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(auth_router, prefix="/api")
    app.include_router(recurso_router, prefix="/api")

    def reemplazar_db():
        yield db_session

    app.dependency_overrides[get_db] = reemplazar_db
    headers = {}
    if actor is not None:
        token = create_access_token(subject=str(actor.id), roles=[])
        headers["Authorization"] = f"Bearer {token}"
    return TestClient(app, headers=headers)


def crear_custodio(db_session, rol: Rol, sufijo: str) -> Usuario:
    custodio = crear_usuario(db_session, sufijo)
    custodio.roles.append(rol)
    db_session.commit()
    return custodio


# --- POST /api/recursos ------------------------------------------------------


def test_crear_recurso_libro_ok(db_session):
    custodio = crear_custodio(db_session, Rol.CUSTODIO_CE, "CE-ALTA")
    client = crear_cliente(db_session, custodio)

    respuesta = client.post(
        "/api/recursos",
        json={"codigo": "LIB-900", "nombre": "Nuevo libro", "tipo_recurso": "LIBRO"},
    )

    assert respuesta.status_code == 201
    datos = respuesta.json()
    assert datos["gestor"] == "CENTRO_ESTUDIANTES"
    assert datos["estado"] == "DISPONIBLE"


def test_crear_recurso_con_gestor_equivocado_devuelve_403(db_session):
    custodio_ce = crear_custodio(db_session, Rol.CUSTODIO_CE, "CE-SINPERM")
    client = crear_cliente(db_session, custodio_ce)

    respuesta = client.post(
        "/api/recursos",
        json={"codigo": "ACA-900", "nombre": "Proyector", "tipo_recurso": "ACADEMICO"},
    )

    assert respuesta.status_code == 403


def test_crear_recurso_codigo_duplicado_devuelve_409(db_session):
    custodio = crear_custodio(db_session, Rol.CUSTODIO_CE, "CE-DUP")
    crear_recurso(db_session, TipoRecurso.LIBRO, "DUP-900")
    client = crear_cliente(db_session, custodio)

    respuesta = client.post(
        "/api/recursos",
        json={"codigo": "LIBRO-DUP-900", "nombre": "Repetido", "tipo_recurso": "LIBRO"},
    )

    assert respuesta.status_code == 409


# --- PUT /api/recursos/{id} ---------------------------------------------------


def test_actualizar_recurso_cambia_datos_basicos(db_session):
    custodio = crear_custodio(db_session, Rol.CUSTODIO_CE, "CE-EDIT")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "EDIT-900")
    client = crear_cliente(db_session, custodio)

    respuesta = client.put(
        f"/api/recursos/{recurso.id}",
        json={"nombre": "Nombre corregido", "ubicacion": "Estante Z"},
    )

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["nombre"] == "Nombre corregido"
    assert datos["ubicacion"] == "Estante Z"


def test_actualizar_recurso_de_otro_gestor_devuelve_403(db_session):
    custodio_ce = crear_custodio(db_session, Rol.CUSTODIO_CE, "CE-OTRO")
    recurso_academico = crear_recurso(db_session, TipoRecurso.ACADEMICO, "OTRO-900")
    client = crear_cliente(db_session, custodio_ce)

    respuesta = client.put(
        f"/api/recursos/{recurso_academico.id}", json={"nombre": "Intento"}
    )

    assert respuesta.status_code == 403


def test_actualizar_recurso_inexistente_devuelve_404(db_session):
    custodio = crear_custodio(db_session, Rol.CUSTODIO_CE, "CE-404")
    client = crear_cliente(db_session, custodio)

    respuesta = client.put("/api/recursos/999999", json={"nombre": "Nada"})

    assert respuesta.status_code == 404


def test_actualizar_recurso_codigo_duplicado_devuelve_409(db_session):
    custodio = crear_custodio(db_session, Rol.CUSTODIO_CE, "CE-EDITDUP")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "EDITDUP-A")
    crear_recurso(db_session, TipoRecurso.LIBRO, "EDITDUP-B")
    client = crear_cliente(db_session, custodio)

    respuesta = client.put(
        f"/api/recursos/{recurso.id}", json={"codigo": "LIBRO-EDITDUP-B"}
    )

    assert respuesta.status_code == 409


def test_dar_de_baja_recurso_via_put(db_session):
    custodio = crear_custodio(db_session, Rol.CUSTODIO_CE, "CE-BAJA")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "BAJA-900")
    client = crear_cliente(db_session, custodio)

    respuesta = client.put(f"/api/recursos/{recurso.id}", json={"estado": "BAJA"})

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["estado"] == "BAJA"
    assert datos["disponible"] is False


def test_no_se_puede_cambiar_estado_de_recurso_prestado(db_session):
    custodio = crear_custodio(db_session, Rol.CUSTODIO_CE, "CE-PRESTADO")
    recurso = crear_recurso(
        db_session, TipoRecurso.LIBRO, "PRESTADO-900", estado=EstadoRecurso.PRESTADO
    )
    client = crear_cliente(db_session, custodio)

    respuesta = client.put(
        f"/api/recursos/{recurso.id}", json={"estado": "MANTENIMIENTO"}
    )

    assert respuesta.status_code == 409


def test_actualizar_recurso_rechaza_estado_prestado_o_reservado(db_session):
    custodio = crear_custodio(db_session, Rol.CUSTODIO_CE, "CE-ESTADOINV")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "ESTADOINV-900")
    client = crear_cliente(db_session, custodio)

    respuesta = client.put(f"/api/recursos/{recurso.id}", json={"estado": "RESERVADO"})

    assert respuesta.status_code == 422


def test_estudiante_no_puede_editar_recurso(db_session):
    estudiante = crear_custodio(db_session, Rol.ESTUDIANTE, "EST-EDIT")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "ESTUDIANTE-900")
    client = crear_cliente(db_session, estudiante)

    respuesta = client.put(f"/api/recursos/{recurso.id}", json={"nombre": "Intento"})

    assert respuesta.status_code == 403


def test_sin_token_recibe_401(db_session):
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "SINTOKEN-900")
    client = crear_cliente(db_session)

    respuesta = client.put(f"/api/recursos/{recurso.id}", json={"nombre": "Intento"})

    assert respuesta.status_code == 401
