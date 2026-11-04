from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_db
from app.models import ModalidadUso, Rol, TipoRecurso
from app.routers.notificacion import router as notificacion_router
from app.routers.solicitud import router as solicitud_router
from app.security import create_access_token
from .helpers import crear_recurso, crear_usuario


def cliente(db_session, actor=None):
    app = FastAPI()
    app.include_router(solicitud_router, prefix="/api")
    app.include_router(notificacion_router, prefix="/api")

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


def test_crear_solicitud_exige_autenticacion_y_modo_de_consulta(db_session):
    solicitante = crear_actor(db_session, "API-SOL")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "API-SOL")
    sin_sesion = cliente(db_session)
    autenticado = cliente(db_session, solicitante)

    assert sin_sesion.post(
        "/api/solicitudes",
        json={"recurso_id": recurso.id, "tipo_solicitud": "SIMPLE"},
    ).status_code == 401

    creada = autenticado.post(
        "/api/solicitudes",
        json={"recurso_id": recurso.id, "tipo_solicitud": "SIMPLE"},
    )
    assert creada.status_code == 201
    assert creada.json()["estado"] == "SOLICITADA"
    assert autenticado.get("/api/solicitudes").status_code == 403
    assert len(autenticado.get("/api/solicitudes?mias=true").json()) == 1


def test_bandeja_incluye_union_de_roles_y_orden_fifo(db_session):
    solicitante = crear_actor(db_session, "API-BANDEJA-SOL")
    docente_custodio = crear_actor(
        db_session, "API-BANDEJA-ACTOR", Rol.DOCENTE, Rol.CUSTODIO_CE
    )
    libro = crear_recurso(db_session, TipoRecurso.LIBRO, "API-BANDEJA")
    academico = crear_recurso(db_session, TipoRecurso.ACADEMICO, "API-BANDEJA")
    solicitante_client = cliente(db_session, solicitante)
    solicitante_client.post(
        "/api/solicitudes",
        json={"recurso_id": libro.id, "tipo_solicitud": "SIMPLE"},
    )
    solicitante_client.post(
        "/api/solicitudes",
        json={
            "recurso_id": academico.id,
            "tipo_solicitud": "POR_CURSO",
            "motivo": "Clase",
        },
    )

    pendientes = cliente(db_session, docente_custodio).get(
        "/api/solicitudes?pendientes=true"
    )

    assert pendientes.status_code == 200
    assert [item["tipo_solicitud"] for item in pendientes.json()] == [
        "SIMPLE",
        "POR_CURSO",
    ]


def test_aceptar_notifica_al_dueño_y_protege_patch_de_otro_usuario(db_session):
    solicitante = crear_actor(db_session, "API-ACEPTA-SOL")
    custodio = crear_actor(db_session, "API-ACEPTA-CUST", Rol.CUSTODIO_CE)
    ajeno = crear_actor(db_session, "API-ACEPTA-AJENO")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "API-ACEPTA")
    client_solicitante = cliente(db_session, solicitante)
    creada = client_solicitante.post(
        "/api/solicitudes",
        json={"recurso_id": recurso.id, "tipo_solicitud": "SIMPLE"},
    )
    solicitud_id = creada.json()["id"]

    aceptada = cliente(db_session, custodio).post(
        f"/api/solicitudes/{solicitud_id}/aceptar",
        json={"modalidad_uso": ModalidadUso.RETIRO_TEMPORAL.value},
    )
    assert aceptada.status_code == 201
    assert aceptada.json()["estado"] == "ACEPTADA"
    assert aceptada.json()["prestamo_id"] is not None

    notificaciones = client_solicitante.get("/api/notificaciones")
    assert notificaciones.status_code == 200
    assert len(notificaciones.json()) == 1
    notificacion_id = notificaciones.json()[0]["id"]
    assert cliente(db_session, ajeno).get("/api/notificaciones").json() == []
    assert cliente(db_session, ajeno).patch(
        f"/api/notificaciones/{notificacion_id}", json={"leida": True}
    ).status_code == 403

    marcada = client_solicitante.patch(
        f"/api/notificaciones/{notificacion_id}", json={"leida": True}
    )
    assert marcada.status_code == 200
    assert marcada.json() == {"leida": True}
    assert client_solicitante.get("/api/notificaciones?leidas=false").json() == []
