"""Reglas del módulo de sanciones y bloqueo de usuarios (RF5)."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from ..models.enums import EstadoPrestamo, EstadoRecurso, Gestor, MotivoSancion, Rol
from ..models.prestamo import Prestamo
from ..models.recurso import Recurso
from ..models.sancion import Sancion, SancionEvento
from ..models.usuario import Usuario

DURACION_BLOQUEO_RETRASO = timedelta(hours=72)
ZONA_LIMA = ZoneInfo("America/Lima")


class ErrorSancion(Exception):
    """Error de negocio del módulo de sanciones."""


class SancionNoEncontrada(ErrorSancion):
    """No existe el préstamo o la sanción solicitada."""


class ConflictoSancion(ErrorSancion):
    """La acción contradice la política de sanciones."""


class PermisoSancion(ErrorSancion):
    """El usuario no administra el recurso relacionado."""


def _normalizar_datetime(valor: datetime) -> datetime:
    return valor if valor.tzinfo is not None else valor.replace(tzinfo=timezone.utc)


def _ahora_utc(ahora: datetime | None = None) -> datetime:
    return _normalizar_datetime(ahora or datetime.now(timezone.utc)).astimezone(timezone.utc)


def _gestores_del_custodio(usuario: Usuario) -> list[Gestor]:
    gestores: list[Gestor] = []
    if usuario.tiene_rol(Rol.CUSTODIO_CE):
        gestores.append(Gestor.CENTRO_ESTUDIANTES)
    if usuario.tiene_rol(Rol.CUSTODIO_INFRA):
        gestores.append(Gestor.INFRAESTRUCTURA)
    return gestores


def _obtener_prestamo(db: Session, prestamo_id: int) -> Prestamo:
    prestamo = db.scalar(
        select(Prestamo)
        .options(selectinload(Prestamo.recurso))
        .where(Prestamo.id == prestamo_id)
        .with_for_update()
    )
    if prestamo is None:
        raise SancionNoEncontrada("Préstamo no encontrado")
    return prestamo


def _validar_custodio_del_recurso(actor: Usuario, prestamo: Prestamo) -> None:
    if actor.tiene_rol(Rol.ADMINISTRADOR_SISTEMA):
        return
    requerido = (
        Rol.CUSTODIO_CE
        if prestamo.recurso.gestor == Gestor.CENTRO_ESTUDIANTES
        else Rol.CUSTODIO_INFRA
    )
    if not actor.tiene_rol(requerido):
        raise PermisoSancion("El custodio no administra el recurso de este préstamo")


def _registrar_evento(
    db: Session,
    sancion: Sancion,
    *,
    tipo: str,
    detalle: str,
    actor_usuario_id: int | None,
    recurso_reposicion_id: int | None = None,
) -> SancionEvento:
    evento = SancionEvento(
        sancion=sancion,
        tipo=tipo,
        detalle=detalle,
        actor_usuario_id=actor_usuario_id,
        recurso_reposicion_id=recurso_reposicion_id,
    )
    db.add(evento)
    return evento


def _crear_registro(
    db: Session,
    *,
    prestamo: Prestamo,
    motivo: MotivoSancion,
    inicio: datetime,
    actor_usuario_id: int | None,
    detalle: str,
) -> Sancion | None:
    existente = db.scalar(
        select(Sancion).where(
            Sancion.prestamo_id == prestamo.id,
            Sancion.motivo == motivo,
        )
    )
    if existente is not None:
        return None

    inicio = _ahora_utc(inicio)
    fin = inicio + DURACION_BLOQUEO_RETRASO if motivo == MotivoSancion.RETRASO else None
    sancion = Sancion(
        usuario_id=prestamo.prestatario_id,
        prestamo_id=prestamo.id,
        motivo=motivo,
        inicio=inicio,
        fin=fin,
        activa=True,
        detalle=detalle.strip() or None,
    )
    db.add(sancion)
    db.flush()
    _registrar_evento(
        db,
        sancion,
        tipo="REGISTRADA",
        detalle=detalle.strip() or f"Sanción por {motivo.value.lower()}.",
        actor_usuario_id=actor_usuario_id,
    )
    return sancion


def registrar_sanciones_por_devolucion(
    db: Session,
    *,
    prestamo: Prestamo,
    danado: bool,
    perdido: bool,
    actor_usuario_id: int | None,
    ahora: datetime,
) -> list[Sancion]:
    """Agrega una sanción por cada causa independiente detectada al devolver.

    La pérdida prevalece sobre el daño (un objeto perdido no puede repararse),
    pero el retraso se registra aparte si también ocurrió.
    """
    ahora = _ahora_utc(ahora)
    causas: list[tuple[MotivoSancion, str]] = []
    if perdido:
        causas.append((MotivoSancion.PERDIDA, "El recurso fue reportado como perdido."))
    elif danado:
        causas.append((MotivoSancion.DANIO, "El recurso fue reportado como dañado."))

    fecha_limite = _normalizar_datetime(prestamo.fecha_limite)
    if fecha_limite < ahora:
        causas.append((MotivoSancion.RETRASO, "La devolución se registró después del plazo."))

    sanciones: list[Sancion] = []
    for motivo, descripcion in causas:
        detalle = descripcion
        if prestamo.condicion_devolucion:
            detalle += f" Condición registrada: {prestamo.condicion_devolucion.strip()}"
        sancion = _crear_registro(
            db,
            prestamo=prestamo,
            motivo=motivo,
            inicio=ahora,
            actor_usuario_id=actor_usuario_id,
            detalle=detalle,
        )
        if sancion is not None:
            sanciones.append(sancion)
    return sanciones


def _vencer_sanciones_expiradas(
    db: Session, ahora: datetime, *, usuario_id: int | None = None
) -> list[Sancion]:
    """Cierra bloqueos temporales vencidos y agrega un evento por cada uno."""
    consulta = select(Sancion).where(
        Sancion.activa.is_(True),
        Sancion.fin.is_not(None),
        Sancion.fin <= ahora,
    )
    if usuario_id is not None:
        consulta = consulta.where(Sancion.usuario_id == usuario_id)

    vencidas = list(db.scalars(consulta.with_for_update()))
    for sancion in vencidas:
        sancion.activa = False
        _registrar_evento(
            db,
            sancion,
            tipo="VENCIDA",
            detalle="El bloqueo temporal de 72 horas terminó automáticamente.",
            actor_usuario_id=None,
        )
    if vencidas:
        db.flush()
    return vencidas


def sancion_bloqueante(
    db: Session, usuario_id: int, *, ahora: datetime | None = None
) -> Sancion | None:
    """Devuelve la sanción vigente que determina cuándo (o si) se desbloquea el usuario."""
    ahora = _ahora_utc(ahora)
    _vencer_sanciones_expiradas(db, ahora, usuario_id=usuario_id)

    return db.scalar(
        select(Sancion)
        .where(
            Sancion.usuario_id == usuario_id,
            Sancion.activa.is_(True),
            or_(Sancion.fin.is_(None), Sancion.fin > ahora),
        )
        .order_by(
            Sancion.fin.is_(None).desc(),  # indefinida (DANIO/PERDIDA sin resolver) manda
            Sancion.fin.desc(),            # entre fechadas, la de vencimiento más tardío
            Sancion.inicio.asc(),
            Sancion.id.asc(),              # desempate estable entre indefinidas simultáneas
        )
        .limit(1)
    )


def estado_bloqueo(
    db: Session, usuario_id: int, *, ahora: datetime | None = None
) -> Sancion | None:
    """Sanción bloqueante vigente, persistiendo cualquier vencimiento detectado al consultar.

    sancion_bloqueante no commitea (lo llaman los 3 servicios de negocio dentro de su propia
    transacción); un GET de solo lectura no tiene ese commit envolvente, así que sin esto un
    vencimiento detectado acá se perdería al cerrar la sesión (mismo motivo por el que
    listar_sanciones commitea).
    """
    sancion = sancion_bloqueante(db, usuario_id, ahora=ahora)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return sancion


def mensaje_bloqueo(sancion: Sancion) -> str:
    """Mensaje consistente para solicitudes, reservas y préstamos."""
    motivo = sancion.motivo.value.lower()
    if sancion.motivo == MotivoSancion.RETRASO and sancion.fin is not None:
        fin_lima = _normalizar_datetime(sancion.fin).astimezone(ZONA_LIMA)
        return (
            f"Tienes una sanción activa por retraso. Podrás volver a solicitar, "
            f"reservar o recibir préstamos desde el {fin_lima:%d/%m/%Y %H:%M} (hora de Lima)."
        )
    accion = "la reparación" if sancion.motivo == MotivoSancion.DANIO else "la reposición"
    return (
        f"Tienes una sanción activa por {motivo}. El bloqueo termina cuando "
        f"el custodio registre {accion} del recurso."
    )


def listar_sanciones(
    db: Session,
    *,
    actor: Usuario,
    mias: bool = False,
    activas: bool | None = None,
    ahora: datetime | None = None,
) -> list[Sancion]:
    ahora = _ahora_utc(ahora)
    # Actualiza los estados que verá el usuario, custodio o administrador.
    # El listado administrativo también refleja vencimientos de terceros.
    _vencer_sanciones_expiradas(db, ahora)
    consulta = select(Sancion).options(
        selectinload(Sancion.usuario),
        selectinload(Sancion.prestamo).selectinload(Prestamo.recurso),
        selectinload(Sancion.eventos).selectinload(SancionEvento.actor),
        selectinload(Sancion.eventos).selectinload(SancionEvento.recurso_reposicion),
    )

    if mias or not actor.tiene_rol(
        Rol.CUSTODIO_CE, Rol.CUSTODIO_INFRA, Rol.ADMINISTRADOR_SISTEMA
    ):
        consulta = consulta.where(Sancion.usuario_id == actor.id)
    elif not actor.tiene_rol(Rol.ADMINISTRADOR_SISTEMA):
        gestores = _gestores_del_custodio(actor)
        consulta = (
            consulta.join(Sancion.prestamo)
            .join(Prestamo.recurso)
            .where(Recurso.gestor.in_(gestores))
        )

    if activas is not None:
        consulta = consulta.where(Sancion.activa.is_(activas))
    resultado = list(
        db.scalars(consulta.order_by(Sancion.inicio.desc(), Sancion.id.desc()))
    )
    try:
        db.commit()  # persiste eventos VENCIDA creados al consultar el historial.
    except Exception:
        db.rollback()
        raise
    return resultado


def crear_sancion_manual(
    db: Session,
    *,
    prestamo_id: int,
    motivo: MotivoSancion,
    detalle: str,
    actor_id: int,
    ahora: datetime | None = None,
) -> Sancion:
    ahora = _ahora_utc(ahora)
    prestamo = _obtener_prestamo(db, prestamo_id)
    actor = db.get(Usuario, actor_id)
    if actor is None or not actor.activo:
        raise PermisoSancion("Usuario no autorizado")
    _validar_custodio_del_recurso(actor, prestamo)

    existente = db.scalar(
        select(Sancion.id).where(
            Sancion.prestamo_id == prestamo.id,
            Sancion.motivo == motivo,
        )
    )
    if existente is not None:
        raise ConflictoSancion("Ya existe una sanción de ese motivo para este préstamo")

    if motivo in (MotivoSancion.DANIO, MotivoSancion.PERDIDA):
        motivo_opuesto = (
            MotivoSancion.PERDIDA
            if motivo == MotivoSancion.DANIO
            else MotivoSancion.DANIO
        )
        if db.scalar(
            select(Sancion.id).where(
                Sancion.prestamo_id == prestamo.id,
                Sancion.motivo == motivo_opuesto,
            )
        ) is not None:
            raise ConflictoSancion(
                "Daño y pérdida no se registran juntos para el mismo préstamo"
            )

    inicio = ahora
    if motivo == MotivoSancion.RETRASO:
        if prestamo.fecha_devolucion is None:
            raise ConflictoSancion("El retraso se registra cuando se devuelve el préstamo")
        referencia = _normalizar_datetime(prestamo.fecha_devolucion)
        if _normalizar_datetime(prestamo.fecha_limite) >= referencia:
            raise ConflictoSancion("El préstamo todavía no está atrasado")
        inicio = referencia
    else:
        if prestamo.estado != EstadoPrestamo.DEVUELTO:
            raise ConflictoSancion("Daño o pérdida se registra al devolver el préstamo")
        recurso = prestamo.recurso
        if motivo == MotivoSancion.DANIO:
            if prestamo.perdido:
                raise ConflictoSancion("Una pérdida no puede registrarse también como daño")
            if recurso.estado != EstadoRecurso.MANTENIMIENTO:
                raise ConflictoSancion(
                    "El recurso debe estar en MANTENIMIENTO para registrar daño"
                )
            prestamo.danado = True
        else:
            if prestamo.danado and not prestamo.perdido:
                raise ConflictoSancion(
                    "El préstamo ya está registrado como daño, no como pérdida"
                )
            if recurso.estado not in (EstadoRecurso.BAJA, EstadoRecurso.MANTENIMIENTO):
                raise ConflictoSancion(
                    "El recurso debe estar retirado o en MANTENIMIENTO para registrar pérdida"
                )
            prestamo.perdido = True
            recurso.estado = EstadoRecurso.BAJA
    sancion = _crear_registro(
        db,
        prestamo=prestamo,
        motivo=motivo,
        inicio=inicio,
        actor_usuario_id=actor.id,
        detalle=detalle,
    )
    if sancion is None:
        raise ConflictoSancion("Ya existe una sanción de ese motivo para este préstamo")
    if sancion.fin is not None and sancion.fin <= ahora:
        sancion.activa = False
        _registrar_evento(
            db,
            sancion,
            tipo="VENCIDA",
            detalle="El bloqueo temporal de 72 horas ya había terminado al registrar el caso.",
            actor_usuario_id=None,
        )
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return sancion


def resolver_sancion(
    db: Session,
    *,
    sancion_id: int,
    actor_id: int,
    detalle: str,
    recurso_reposicion_id: int | None = None,
    ahora: datetime | None = None,
) -> Sancion:
    ahora = _ahora_utc(ahora)
    sancion = db.scalar(
        select(Sancion)
        .options(selectinload(Sancion.prestamo).selectinload(Prestamo.recurso))
        .where(Sancion.id == sancion_id)
        .with_for_update()
    )
    if sancion is None:
        raise SancionNoEncontrada("Sanción no encontrada")
    actor = db.get(Usuario, actor_id)
    if actor is None or not actor.activo:
        raise PermisoSancion("Usuario no autorizado")
    _validar_custodio_del_recurso(actor, sancion.prestamo)

    if sancion.motivo == MotivoSancion.RETRASO:
        raise ConflictoSancion("El bloqueo por retraso vence automáticamente a las 72 horas")
    if not sancion.activa:
        raise ConflictoSancion("La sanción ya fue resuelta o venció")

    tipo_evento = "REPARACION_REGISTRADA"
    if sancion.motivo == MotivoSancion.DANIO:
        if recurso_reposicion_id is not None:
            raise ConflictoSancion("Una sanción por daño debe resolverse con una reparación")
        recurso = sancion.prestamo.recurso
        if sancion.prestamo.perdido:
            raise ConflictoSancion("El préstamo está registrado como pérdida, no como daño")
        if recurso.estado == EstadoRecurso.MANTENIMIENTO:
            recurso.estado = EstadoRecurso.DISPONIBLE
        elif recurso.estado != EstadoRecurso.DISPONIBLE:
            raise ConflictoSancion(
                "El recurso debe estar en mantenimiento o reparado antes de cerrar la sanción"
            )
    else:
        tipo_evento = "REPOSICION_REGISTRADA"
        original = sancion.prestamo.recurso
        if not sancion.prestamo.perdido or original.estado != EstadoRecurso.BAJA:
            raise ConflictoSancion(
                "La pérdida debe permanecer en BAJA hasta registrar la reposición"
            )
        if recurso_reposicion_id is None:
            raise ConflictoSancion("Registra primero el ejemplar de reposición en inventario")
        reposicion = db.get(Recurso, recurso_reposicion_id)
        if reposicion is None:
            raise SancionNoEncontrada("Recurso de reposición no encontrado")
        if reposicion.id == original.id:
            raise ConflictoSancion("El recurso de reposición debe ser otro ejemplar")
        if (
            reposicion.gestor != original.gestor
            or reposicion.tipo_recurso != original.tipo_recurso
        ):
            raise ConflictoSancion("La reposición debe corresponder al mismo gestor y tipo de recurso")
        if reposicion.estado != EstadoRecurso.DISPONIBLE:
            raise ConflictoSancion("El recurso de reposición debe estar disponible en inventario")
        if db.scalar(
            select(SancionEvento.id).where(
                SancionEvento.recurso_reposicion_id == reposicion.id
            )
        ) is not None:
            raise ConflictoSancion("Este ejemplar ya fue usado como reposición")

    sancion.fin = ahora
    sancion.activa = False
    _registrar_evento(
        db,
        sancion,
        tipo=tipo_evento,
        detalle=detalle.strip(),
        actor_usuario_id=actor.id,
        recurso_reposicion_id=recurso_reposicion_id,
    )
    try:
        db.commit()
        db.refresh(sancion)
    except Exception:
        db.rollback()
        raise
    return sancion
