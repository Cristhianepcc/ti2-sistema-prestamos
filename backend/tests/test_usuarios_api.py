import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import get_db
from app.models import Rol, Usuario
from app.routers.auth import router as auth_router
from app.routers.usuarios import router as usuarios_router
from app.security import create_access_token, verify_password
from .helpers import crear_usuario


def crear_cliente(db_session, actor: Usuario | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(auth_router, prefix="/api")
    app.include_router(usuarios_router, prefix="/api")

    def reemplazar_db():
        yield db_session

    app.dependency_overrides[get_db] = reemplazar_db
    headers = {}
    if actor is not None:
        token = create_access_token(subject=str(actor.id), roles=[])
        headers["Authorization"] = f"Bearer {token}"
    return TestClient(app, headers=headers)


def crear_admin(db_session) -> Usuario:
    admin = crear_usuario(db_session, "ADMIN")
    admin.roles.append(Rol.ADMINISTRADOR_SISTEMA)
    db_session.commit()
    return admin


def test_listar_usuarios_devuelve_datos_publicos_ordenados(db_session):
    admin = crear_admin(db_session)
    segundo = crear_usuario(db_session, "B")
    segundo.roles.append(Rol.ESTUDIANTE)
    primero = crear_usuario(db_session, "A")
    primero.roles.append(Rol.DOCENTE)
    db_session.commit()
    client = crear_cliente(db_session, admin)

    respuesta = client.get("/api/usuarios")

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert [usuario["codigo"] for usuario in datos] == [
        primero.codigo,
        admin.codigo,
        segundo.codigo,
    ]
    assert datos[0]["roles"] == ["DOCENTE"]
    assert "password_hash" not in datos[0]
    assert "password" not in datos[0]
    assert "activo" not in datos[0]


def test_crear_usuario_normaliza_email_y_guarda_hash(db_session):
    admin = crear_admin(db_session)
    client = crear_cliente(db_session, admin)

    respuesta = client.post(
        "/api/usuarios",
        json={
            "codigo": "  ALU-001  ",
            "nombres": "  Ana Pérez  ",
            "email": " ANA.PEREZ@UNSA.EDU.PE ",
            "password": "clave-inicial",
            "roles": ["ESTUDIANTE", "DOCENTE"],
        },
    )

    assert respuesta.status_code == 201
    datos = respuesta.json()
    assert datos["codigo"] == "ALU-001"
    assert datos["nombres"] == "Ana Pérez"
    assert datos["email"] == "ana.perez@unsa.edu.pe"
    assert set(datos["roles"]) == {"ESTUDIANTE", "DOCENTE"}
    assert "password_hash" not in datos

    usuario = db_session.scalar(select(Usuario).where(Usuario.codigo == "ALU-001"))
    assert usuario is not None
    assert usuario.password_hash != "clave-inicial"
    assert verify_password("clave-inicial", usuario.password_hash)

    login = client.post(
        "/api/auth/login",
        json={"email": " ANA.PEREZ@UNSA.EDU.PE ", "password": "clave-inicial"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["email"] == "ana.perez@unsa.edu.pe"


@pytest.mark.parametrize(
    ("campo", "valor"),
    [("codigo", "TEST-EXISTENTE"), ("email", "existente@example.com")],
)
def test_crear_usuario_rechaza_codigo_o_correo_duplicado(
    db_session, campo, valor
):
    admin = crear_admin(db_session)
    crear_usuario(db_session, "EXISTENTE")
    client = crear_cliente(db_session, admin)
    datos = {
        "codigo": "NUEVO",
        "nombres": "Usuario nuevo",
        "email": "nuevo@example.com",
        "password": "clave-inicial",
        "roles": ["ESTUDIANTE"],
    }
    datos[campo] = valor

    respuesta = client.post("/api/usuarios", json=datos)

    assert respuesta.status_code == 409


def test_actualizar_roles_reemplaza_la_lista_completa(db_session):
    admin = crear_admin(db_session)
    usuario = crear_usuario(db_session, "CAMBIO")
    usuario.roles.extend([Rol.ESTUDIANTE, Rol.DOCENTE])
    db_session.commit()
    client = crear_cliente(db_session, admin)

    respuesta = client.put(
        f"/api/usuarios/{usuario.id}/roles", json={"roles": ["DOCENTE"]}
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["roles"] == ["DOCENTE"]
    db_session.refresh(usuario)
    assert usuario.roles == [Rol.DOCENTE]


def test_actualizar_roles_de_usuario_inexistente_devuelve_404(db_session):
    admin = crear_admin(db_session)
    client = crear_cliente(db_session, admin)

    respuesta = client.put("/api/usuarios/999/roles", json={"roles": ["DOCENTE"]})

    assert respuesta.status_code == 404


def test_no_se_puede_quitar_el_ultimo_administrador_activo(db_session):
    admin = crear_admin(db_session)
    client = crear_cliente(db_session, admin)

    respuesta = client.put(
        f"/api/usuarios/{admin.id}/roles", json={"roles": ["DOCENTE"]}
    )

    assert respuesta.status_code == 409
    assert "último administrador" in respuesta.json()["detail"]


def test_usuario_sin_rol_administrador_recibe_403(db_session):
    estudiante = crear_usuario(db_session, "SIN-ADMIN")
    estudiante.roles.append(Rol.ESTUDIANTE)
    db_session.commit()
    client = crear_cliente(db_session, estudiante)

    respuesta = client.get("/api/usuarios")

    assert respuesta.status_code == 403


def test_sin_token_recibe_401(db_session):
    client = crear_cliente(db_session)

    respuesta = client.get("/api/usuarios")

    assert respuesta.status_code == 401


def test_validacion_rechaza_lista_vacia_o_rol_desconocido(db_session):
    admin = crear_admin(db_session)
    client = crear_cliente(db_session, admin)

    vacia = client.post(
        "/api/usuarios",
        json={
            "codigo": "VACIO",
            "nombres": "Sin roles",
            "email": "sin.roles@example.com",
            "password": "clave-inicial",
            "roles": [],
        },
    )
    desconocido = client.put("/api/usuarios/1/roles", json={"roles": ["SUPERUSER"]})
    repetido = client.put(
        "/api/usuarios/1/roles", json={"roles": ["DOCENTE", "DOCENTE"]}
    )

    assert vacia.status_code == 422
    assert desconocido.status_code == 422
    assert repetido.status_code == 422
