"""Endpoints del flujo de solicitudes académicas (RF3/RF4)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.enums import EstadoSolicitud, Rol, TipoSolicitud
from ..models.solicitud import Solicitud
from ..schemas.solicitud import (
    AceptarSolicitud,
    RechazarSolicitud,
    SolicitudCreate,
    SolicitudPublica,
)
from ..security import UsuarioActual, require_role
from ..services.solicitud_service import (
    ConflictoSolicitud,
    DatosSolicitudInvalidos,
    PermisoSolicitud,
    SolicitudNoEncontrada,
    aceptar_solicitud,
    avalar_solicitud,
    autorizar_solicitud,
    crear_solicitud,
    listar_solicitudes,
    paso_pendiente,
    rechazar_solicitud,
)
from ..services.prestamo_service import ConflictoPrestamo, RegistroPrestamoNoEncontrado

router = APIRouter(prefix="/solicitudes", tags=["solicitudes"])


def _traducir_error(error: Exception) -> HTTPException:
    if isinstance(error, SolicitudNoEncontrada):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(error))
    if isinstance(error, PermisoSolicitud):
        return HTTPException(status.HTTP_403_FORBIDDEN, str(error))
    if isinstance(error, (ConflictoSolicitud, ConflictoPrestamo)):
        return HTTPException(status.HTTP_409_CONFLICT, str(error))
    if isinstance(error, RegistroPrestamoNoEncontrado):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(error))
    if isinstance(error, DatosSolicitudInvalidos):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error))
    raise error


@router.post(
    "",
    response_model=SolicitudPublica,
    status_code=status.HTTP_201_CREATED,
)
def crear(
    datos: SolicitudCreate,
    usuario: UsuarioActual,
    db: Annotated[Session, Depends(get_db)],
) -> Solicitud:
    """Crea una solicitud para el usuario autenticado."""
    try:
        return crear_solicitud(
            db,
            solicitante_id=usuario.id,
            recurso_id=datos.recurso_id,
            tipo_solicitud=datos.tipo_solicitud,
            motivo=datos.motivo,
        )
    except (SolicitudNoEncontrada, PermisoSolicitud, ConflictoSolicitud, DatosSolicitudInvalidos) as error:
        raise _traducir_error(error) from error


@router.get("", response_model=list[SolicitudPublica])
def listar(
    usuario: UsuarioActual,
    db: Annotated[Session, Depends(get_db)],
    mias: bool | None = Query(default=None),
    pendientes: bool | None = Query(default=None),
    estado: EstadoSolicitud | None = Query(default=None),
) -> list[Solicitud]:
    """Devuelve solicitudes propias o las que esperan un rol del usuario."""
    roles_aprobadores = {
        Rol.DOCENTE,
        Rol.DIRECCION_ESCUELA,
        Rol.CUSTODIO_CE,
        Rol.CUSTODIO_INFRA,
    }
    if not mias and not pendientes and not any(
        usuario.tiene_rol(rol) for rol in roles_aprobadores
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Usa mias=true o pendientes=true para consultar solicitudes",
        )

    solicitudes = listar_solicitudes(db, estado=estado)
    roles_usuario = set(usuario.roles)
    seleccionadas: dict[int, Solicitud] = {}
    if mias:
        seleccionadas.update(
            (solicitud.id, solicitud)
            for solicitud in solicitudes
            if solicitud.solicitante_id == usuario.id
        )
    if pendientes:
        seleccionadas.update(
            (solicitud.id, solicitud)
            for solicitud in solicitudes
            if paso_pendiente(solicitud) in roles_usuario
        )
    if not mias and not pendientes:
        seleccionadas.update((solicitud.id, solicitud) for solicitud in solicitudes)
    return sorted(
        seleccionadas.values(),
        key=lambda solicitud: (solicitud.created_at, solicitud.id),
    )


@router.post(
    "/{solicitud_id}/avalar",
    response_model=SolicitudPublica,
    dependencies=[Depends(require_role(Rol.DOCENTE))],
)
def avalar(
    solicitud_id: int,
    usuario: UsuarioActual,
    db: Annotated[Session, Depends(get_db)],
) -> Solicitud:
    try:
        return avalar_solicitud(db, solicitud_id=solicitud_id, docente_id=usuario.id)
    except (SolicitudNoEncontrada, PermisoSolicitud, ConflictoSolicitud) as error:
        raise _traducir_error(error) from error


@router.post(
    "/{solicitud_id}/autorizar",
    response_model=SolicitudPublica,
    dependencies=[Depends(require_role(Rol.DIRECCION_ESCUELA))],
)
def autorizar(
    solicitud_id: int,
    usuario: UsuarioActual,
    db: Annotated[Session, Depends(get_db)],
) -> Solicitud:
    try:
        return autorizar_solicitud(
            db, solicitud_id=solicitud_id, direccion_id=usuario.id
        )
    except (SolicitudNoEncontrada, PermisoSolicitud, ConflictoSolicitud) as error:
        raise _traducir_error(error) from error


@router.post(
    "/{solicitud_id}/aceptar",
    response_model=SolicitudPublica,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_role(Rol.CUSTODIO_CE, Rol.CUSTODIO_INFRA))
    ],
)
def aceptar(
    solicitud_id: int,
    datos: AceptarSolicitud,
    usuario: UsuarioActual,
    db: Annotated[Session, Depends(get_db)],
) -> Solicitud:
    try:
        return aceptar_solicitud(
            db,
            solicitud_id=solicitud_id,
            custodio_id=usuario.id,
            modalidad_uso=datos.modalidad_uso,
            reserva_id=datos.reserva_id,
            fecha_limite=datos.fecha_limite,
            condicion_entrega=datos.condicion_entrega,
            garantia=datos.garantia.model_dump() if datos.garantia else None,
        )
    except (
        SolicitudNoEncontrada,
        PermisoSolicitud,
        ConflictoSolicitud,
        ConflictoPrestamo,
        RegistroPrestamoNoEncontrado,
    ) as error:
        raise _traducir_error(error) from error


@router.post(
    "/{solicitud_id}/rechazar",
    response_model=SolicitudPublica,
    dependencies=[
        Depends(
            require_role(
                Rol.DOCENTE,
                Rol.DIRECCION_ESCUELA,
                Rol.CUSTODIO_CE,
                Rol.CUSTODIO_INFRA,
            )
        )
    ],
)
def rechazar(
    solicitud_id: int,
    datos: RechazarSolicitud,
    usuario: UsuarioActual,
    db: Annotated[Session, Depends(get_db)],
) -> Solicitud:
    try:
        return rechazar_solicitud(
            db,
            solicitud_id=solicitud_id,
            usuario_id=usuario.id,
            motivo_rechazo=datos.motivo_rechazo,
        )
    except (SolicitudNoEncontrada, PermisoSolicitud, ConflictoSolicitud) as error:
        raise _traducir_error(error) from error
