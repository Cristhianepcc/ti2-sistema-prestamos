"""Reglas de negocio de solicitudes (flujo solicitud → aceptación).

Esta primera mitad cubre crear y listar. Aval, autorización, aceptar y
rechazar van en las issues siguientes.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.enums import EstadoSolicitud, TipoSolicitud
from ..models.recurso import Recurso
from ..models.solicitud import Solicitud
from .invariantes import TipoRecursoIncompatible, validar_tipo_recurso


class ErrorSolicitud(Exception):
    """Error de negocio relacionado con una solicitud."""


class ConflictoSolicitud(ErrorSolicitud):
    """La operación contradice una regla de negocio (el router responde 409)."""


class SolicitudNoEncontrada(ErrorSolicitud):
    """No se encontró la solicitud o el recurso indicado (el router responde 404)."""


class DatosSolicitudInvalidos(ErrorSolicitud):
    """Datos inválidos que el schema no atrapó (el router responde 422)."""


def _validar_sancion_activa(db: Session, usuario_id: int) -> None:
    """Punto de extensión para el bloqueo por sanciones de RF5.

    El modelo Sancion aún no existe; por ahora no se aplica el bloqueo.
    Mismo patrón que prestamo_service y reserva_service.
    """
    # TODO(RF5): si el usuario tiene una sanción activa, lanzar
    # ConflictoSolicitud("Tienes una sanción activa").
    pass


def crear_solicitud(
    db: Session,
    *,
    solicitante_id: int,
    recurso_id: int,
    tipo_solicitud: TipoSolicitud,
    motivo: str | None = None,
) -> Solicitud:
    """Crea una solicitud en estado SOLICITADA.

    No toca `recurso.estado` (pasa a PRESTADO recién cuando el custodio acepta)
    ni exige que el recurso esté DISPONIBLE al solicitar.
    """
    motivo = (motivo or "").strip() or None
    if tipo_solicitud != TipoSolicitud.SIMPLE and motivo is None:
        raise DatosSolicitudInvalidos(
            "El motivo es obligatorio en solicitudes POR_CURSO y EXCEPCIONAL"
        )

    recurso = db.get(Recurso, recurso_id)
    if recurso is None:
        raise SolicitudNoEncontrada("Recurso no encontrado")

    _validar_sancion_activa(db, solicitante_id)

    try:
        validar_tipo_recurso(tipo_solicitud, recurso)
    except TipoRecursoIncompatible as e:
        raise ConflictoSolicitud(str(e)) from e

    solicitud = Solicitud(
        solicitante_id=solicitante_id,
        recurso_id=recurso_id,
        tipo_solicitud=tipo_solicitud,
        motivo=motivo,
        estado=EstadoSolicitud.SOLICITADA,
    )
    db.add(solicitud)

    try:
        db.commit()
        db.refresh(solicitud)
    except Exception:
        db.rollback()
        raise

    return solicitud


def listar_solicitudes(
    db: Session,
    *,
    solicitante_id: int | None = None,
    estado: EstadoSolicitud | None = None,
    mas_recientes_primero: bool = False,
) -> list[Solicitud]:
    """Lista solicitudes, filtrando por solicitante (`mias=true`) y/o estado.

    Por defecto del más antiguo al más nuevo (FIFO, como la bandeja del
    custodio); `mas_recientes_primero=True` para "mis solicitudes".
    """
    consulta = select(Solicitud)
    if solicitante_id is not None:
        consulta = consulta.where(Solicitud.solicitante_id == solicitante_id)
    if estado is not None:
        consulta = consulta.where(Solicitud.estado == estado)

    if mas_recientes_primero:
        consulta = consulta.order_by(Solicitud.created_at.desc(), Solicitud.id.desc())
    else:
        consulta = consulta.order_by(Solicitud.created_at.asc(), Solicitud.id.asc())
    return list(db.scalars(consulta))
