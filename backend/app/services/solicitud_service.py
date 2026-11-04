"""Reglas de negocio del flujo solicitud → aprobación → préstamo."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models.enums import (
    EstadoReserva,
    EstadoSolicitud,
    Gestor,
    ModalidadUso,
    Rol,
    TipoNotificacion,
    TipoSolicitud,
    TipoPrestamo,
)
from ..models.notificacion import Notificacion
from ..models.recurso import Recurso
from ..models.solicitud import Solicitud
from ..models.usuario import Usuario
from .invariantes import TipoRecursoIncompatible, validar_tipo_recurso
from .prestamo_service import (
    ConflictoPrestamo,
    RegistroPrestamoNoEncontrado,
    crear_prestamo,
)


class ErrorSolicitud(Exception):
    """Error de negocio relacionado con una solicitud."""


class ConflictoSolicitud(ErrorSolicitud):
    """La operación contradice el estado o las reglas del flujo."""


class SolicitudNoEncontrada(ErrorSolicitud):
    """No se encontró la solicitud o el recurso indicado."""


class DatosSolicitudInvalidos(ErrorSolicitud):
    """Datos inválidos que el schema no atrapó."""


class PermisoSolicitud(ErrorSolicitud):
    """El usuario autenticado no tiene permiso para la transición."""


def _validar_sancion_activa(db: Session, usuario_id: int) -> None:
    """Punto de extensión para el módulo de sanciones RF5, aún no implementado."""
    # TODO(RF5): comprobar si el usuario tiene una sanción activa y bloquear la solicitud.
    pass


def _rol_custodio(solicitud: Solicitud) -> Rol:
    if solicitud.recurso.gestor == Gestor.CENTRO_ESTUDIANTES:
        return Rol.CUSTODIO_CE
    return Rol.CUSTODIO_INFRA


def paso_pendiente(solicitud: Solicitud) -> Rol | None:
    """Devuelve el rol que debe actuar a continuación según tipo, estado y gestor."""
    estado = solicitud.estado
    tipo = solicitud.tipo_solicitud
    if estado in (EstadoSolicitud.ACEPTADA, EstadoSolicitud.RECHAZADA):
        return None
    if estado == EstadoSolicitud.SOLICITADA:
        if tipo in (TipoSolicitud.POR_CURSO, TipoSolicitud.EXCEPCIONAL):
            return Rol.DOCENTE
        if tipo == TipoSolicitud.SIMPLE:
            return _rol_custodio(solicitud)
    if estado == EstadoSolicitud.AVALADA:
        if tipo == TipoSolicitud.EXCEPCIONAL:
            return Rol.DIRECCION_ESCUELA
        if tipo == TipoSolicitud.POR_CURSO:
            return _rol_custodio(solicitud)
    if estado == EstadoSolicitud.AUTORIZADA and tipo == TipoSolicitud.EXCEPCIONAL:
        return _rol_custodio(solicitud)
    return None


def _obtener_solicitud(db: Session, solicitud_id: int) -> Solicitud:
    solicitud = db.scalar(
        select(Solicitud)
        .options(
            selectinload(Solicitud.recurso),
            selectinload(Solicitud.prestamo),
            selectinload(Solicitud.solicitante),
        )
        .where(Solicitud.id == solicitud_id)
        .with_for_update()
    )
    if solicitud is None:
        raise SolicitudNoEncontrada("Solicitud no encontrada")
    return solicitud


def _obtener_actor(db: Session, actor_id: int) -> Usuario:
    actor = db.get(Usuario, actor_id)
    if actor is None or not actor.activo:
        raise PermisoSolicitud("Usuario no autorizado")
    return actor


def _guardar(db: Session, solicitud: Solicitud) -> Solicitud:
    try:
        db.commit()
        db.refresh(solicitud)
    except Exception:
        db.rollback()
        raise
    return solicitud


def _validar_sancion_activa_para_crear(db: Session, usuario_id: int) -> None:
    _validar_sancion_activa(db, usuario_id)


def crear_solicitud(
    db: Session,
    *,
    solicitante_id: int,
    recurso_id: int,
    tipo_solicitud: TipoSolicitud,
    motivo: str | None = None,
) -> Solicitud:
    """Crea una solicitud sin cambiar el estado del recurso."""
    motivo = (motivo or "").strip() or None
    if tipo_solicitud != TipoSolicitud.SIMPLE and motivo is None:
        raise DatosSolicitudInvalidos(
            "El motivo es obligatorio en solicitudes POR_CURSO y EXCEPCIONAL"
        )
    recurso = db.get(Recurso, recurso_id)
    if recurso is None:
        raise SolicitudNoEncontrada("Recurso no encontrado")
    if not recurso.disponible:
        raise ConflictoSolicitud(
            "El recurso no está disponible; crea una reserva para una fecha futura"
        )
    _validar_sancion_activa_para_crear(db, solicitante_id)
    try:
        validar_tipo_recurso(tipo_solicitud, recurso)
    except TipoRecursoIncompatible as error:
        raise ConflictoSolicitud(str(error)) from error

    solicitud = Solicitud(
        solicitante_id=solicitante_id,
        recurso_id=recurso_id,
        tipo_solicitud=tipo_solicitud,
        motivo=motivo,
        estado=EstadoSolicitud.SOLICITADA,
    )
    db.add(solicitud)
    return _guardar(db, solicitud)


def listar_solicitudes(
    db: Session,
    *,
    solicitante_id: int | None = None,
    estado: EstadoSolicitud | None = None,
    mas_recientes_primero: bool = False,
) -> list[Solicitud]:
    """Lista solicitudes por solicitante y/o estado."""
    consulta = select(Solicitud).options(
        selectinload(Solicitud.recurso),
        selectinload(Solicitud.prestamo),
        selectinload(Solicitud.solicitante),
    )
    if solicitante_id is not None:
        consulta = consulta.where(Solicitud.solicitante_id == solicitante_id)
    if estado is not None:
        consulta = consulta.where(Solicitud.estado == estado)
    if mas_recientes_primero:
        consulta = consulta.order_by(Solicitud.created_at.desc(), Solicitud.id.desc())
    else:
        consulta = consulta.order_by(Solicitud.created_at.asc(), Solicitud.id.asc())
    return list(db.scalars(consulta))


def avalar_solicitud(db: Session, *, solicitud_id: int, docente_id: int) -> Solicitud:
    solicitud = _obtener_solicitud(db, solicitud_id)
    docente = _obtener_actor(db, docente_id)
    if not docente.tiene_rol(Rol.DOCENTE):
        raise PermisoSolicitud("Solo un docente puede avalar solicitudes")
    if solicitud.tipo_solicitud == TipoSolicitud.SIMPLE:
        raise ConflictoSolicitud("La solicitud SIMPLE no requiere aval")
    if solicitud.estado != EstadoSolicitud.SOLICITADA:
        raise ConflictoSolicitud("Solo se puede avalar una solicitud SOLICITADA")
    # TODO: el contrato aún no define si se bloquea avalar una solicitud propia.
    solicitud.estado = EstadoSolicitud.AVALADA
    solicitud.avalado_por_id = docente_id
    return _guardar(db, solicitud)


def autorizar_solicitud(
    db: Session, *, solicitud_id: int, direccion_id: int
) -> Solicitud:
    solicitud = _obtener_solicitud(db, solicitud_id)
    direccion = _obtener_actor(db, direccion_id)
    if not direccion.tiene_rol(Rol.DIRECCION_ESCUELA):
        raise PermisoSolicitud("Solo Dirección de Escuela puede autorizar")
    if solicitud.tipo_solicitud != TipoSolicitud.EXCEPCIONAL:
        raise ConflictoSolicitud("Solo las solicitudes EXCEPCIONAL requieren autorización")
    if solicitud.estado != EstadoSolicitud.AVALADA:
        raise ConflictoSolicitud("La solicitud debe estar AVALADA antes de autorizarse")
    # TODO: el contrato aún no define si se bloquea autorizar una solicitud propia.
    solicitud.estado = EstadoSolicitud.AUTORIZADA
    solicitud.autorizado_por_id = direccion_id
    return _guardar(db, solicitud)


def _mensaje_rechazo(solicitud: Solicitud, motivo: str | None) -> str:
    nombre = solicitud.recurso.nombre
    mensaje = f'Tu solicitud de "{nombre}" fue rechazada.'
    if motivo:
        mensaje += f" Motivo: {motivo}"
    return mensaje


def rechazar_solicitud(
    db: Session,
    *,
    solicitud_id: int,
    usuario_id: int,
    motivo_rechazo: str | None = None,
) -> Solicitud:
    solicitud = _obtener_solicitud(db, solicitud_id)
    actor = _obtener_actor(db, usuario_id)
    if solicitud.estado not in (
        EstadoSolicitud.SOLICITADA,
        EstadoSolicitud.AVALADA,
        EstadoSolicitud.AUTORIZADA,
    ):
        raise ConflictoSolicitud("La solicitud ya no puede rechazarse")

    turno = paso_pendiente(solicitud)
    custodio = _rol_custodio(solicitud)
    if not actor.tiene_rol(*(role for role in (turno, custodio) if role is not None)):
        raise PermisoSolicitud(
            "Solo quien tiene el paso pendiente o el custodio del recurso puede rechazar"
        )

    motivo = (motivo_rechazo or "").strip() or None
    solicitud.estado = EstadoSolicitud.RECHAZADA
    solicitud.motivo_rechazo = motivo
    db.add(
        Notificacion(
            usuario_id=solicitud.solicitante_id,
            solicitud_id=solicitud.id,
            tipo=TipoNotificacion.SOLICITUD_RECHAZADA,
            mensaje=_mensaje_rechazo(solicitud, motivo),
        )
    )
    return _guardar(db, solicitud)


def _mensaje_aceptacion(solicitud: Solicitud, fecha_limite: datetime) -> str:
    lugares = {
        Gestor.CENTRO_ESTUDIANTES: "el Centro de Estudiantes",
        Gestor.INFRAESTRUCTURA: "Infraestructura",
    }
    if fecha_limite.tzinfo is None:
        fecha_limite = fecha_limite.replace(tzinfo=timezone.utc)
    limite_local = fecha_limite.astimezone(ZoneInfo("America/Lima"))
    hoy_local = datetime.now(ZoneInfo("America/Lima")).date()
    referencia_fecha = (
        "de hoy"
        if limite_local.date() == hoy_local
        else f"del {limite_local:%d/%m/%Y}"
    )
    lugar = lugares[solicitud.recurso.gestor]
    return (
        f'Tu solicitud de "{solicitud.recurso.nombre}" fue aceptada. '
        f"Preséntate en {lugar} antes de las {limite_local:%H:%M} "
        f"{referencia_fecha} para recogerlo."
    )


def aceptar_solicitud(
    db: Session,
    *,
    solicitud_id: int,
    custodio_id: int,
    modalidad_uso: ModalidadUso,
    reserva_id: int | None = None,
    fecha_limite: datetime | None = None,
    condicion_entrega: str | None = None,
    garantia: dict | None = None,
) -> Solicitud:
    """Acepta la solicitud y crea préstamo + notificación en una transacción."""
    solicitud = _obtener_solicitud(db, solicitud_id)
    custodio = _obtener_actor(db, custodio_id)
    rol_custodio = _rol_custodio(solicitud)
    if not custodio.tiene_rol(rol_custodio):
        raise PermisoSolicitud("El custodio no administra el recurso solicitado")

    estado_requerido = {
        TipoSolicitud.SIMPLE: EstadoSolicitud.SOLICITADA,
        TipoSolicitud.POR_CURSO: EstadoSolicitud.AVALADA,
        TipoSolicitud.EXCEPCIONAL: EstadoSolicitud.AUTORIZADA,
    }[solicitud.tipo_solicitud]
    if solicitud.estado != estado_requerido:
        raise ConflictoSolicitud(
            f"La solicitud debe estar en estado {estado_requerido.value} para aceptarse"
        )

    if reserva_id is not None:
        from ..models.reserva import Reserva

        reserva = db.get(Reserva, reserva_id)
        if (
            reserva is None
            or reserva.usuario_id != solicitud.solicitante_id
            or reserva.recurso_id != solicitud.recurso_id
            or reserva.estado
            not in (EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA)
        ):
            # La reserva no es requisito del flujo RF4. La validación detallada de
            # su ciclo corresponde a la integración RF2.
            raise ConflictoSolicitud("La reserva no corresponde a esta solicitud")

    try:
        prestamo = crear_prestamo(
            db,
            recurso_id=solicitud.recurso_id,
            prestatario_id=solicitud.solicitante_id,
            registrado_por_id=custodio_id,
            tipo_prestamo=TipoPrestamo(solicitud.tipo_solicitud.value),
            modalidad_uso=modalidad_uso,
            fecha_limite=fecha_limite,
            reserva_id=reserva_id,
            solicitud_id=solicitud.id,
            condicion_entrega=condicion_entrega,
            garantia=garantia,
            commit=False,
        )
        prestamo.solicitud = solicitud
        solicitud.estado = EstadoSolicitud.ACEPTADA
        solicitud.aceptado_por_id = custodio_id
        db.add(
            Notificacion(
                usuario_id=solicitud.solicitante_id,
                solicitud_id=solicitud.id,
                tipo=TipoNotificacion.SOLICITUD_ACEPTADA,
                mensaje=_mensaje_aceptacion(solicitud, prestamo.fecha_limite),
            )
        )
        db.commit()
        db.refresh(solicitud)
    except (ConflictoPrestamo, RegistroPrestamoNoEncontrado):
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    return solicitud
