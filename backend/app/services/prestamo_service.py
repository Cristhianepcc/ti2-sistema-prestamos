"""Reglas de negocio de préstamos (RF3, issue #30)."""

from datetime import datetime, time, timedelta, timezone
from typing import Any, Mapping

from sqlalchemy import update
from sqlalchemy.orm import Session

from ..models.enums import (
    EstadoPrestamo,
    EstadoRecurso,
    ModalidadUso,
    TipoPrestamo,
    TipoRecurso,
)
from ..models.prestamo import Garantia, Prestamo
from ..models.recurso import Recurso
from ..models.usuario import Usuario


class ErrorPrestamo(Exception):
    """Error de negocio o de registro relacionado con un préstamo."""


class ConflictoPrestamo(ErrorPrestamo):
    """La operación contradice una regla de negocio."""


class RegistroPrestamoNoEncontrado(ErrorPrestamo):
    """No se encontró el préstamo, recurso o usuario indicado."""


# Plazos provisionales hasta que el equipo defina duraciones oficiales (#30).
# DEPORTIVO no está acá: por docs/00-contexto-alcance-propuesta.md §5 es
# préstamo del mismo día y su plazo se calcula aparte (fin del día de entrega).
_PLAZOS_POR_DEFECTO: dict[tuple[TipoRecurso, TipoPrestamo], timedelta] = {
    (TipoRecurso.LIBRO, TipoPrestamo.SIMPLE): timedelta(days=7),
    (TipoRecurso.ACADEMICO, TipoPrestamo.POR_CURSO): timedelta(days=1),
    (TipoRecurso.ACADEMICO, TipoPrestamo.EXCEPCIONAL): timedelta(days=3),
}


def _calcular_fecha_limite(
    tipo_recurso: TipoRecurso,
    tipo_prestamo: TipoPrestamo,
    fecha_entrega: datetime,
) -> datetime:
    """Calcula el plazo cuando el custodio no envía `fecha_limite`."""
    if tipo_recurso == TipoRecurso.DEPORTIVO:
        return datetime.combine(
            fecha_entrega.date(), time(23, 59, 59), tzinfo=fecha_entrega.tzinfo
        )

    plazo = _PLAZOS_POR_DEFECTO.get((tipo_recurso, tipo_prestamo), timedelta(days=7))
    return fecha_entrega + plazo


def _validar_sancion_activa(db: Session, usuario_id: int) -> None:
    """Punto de extensión para el bloqueo por sanciones de RF5.

    El modelo Sancion aún no existe; por ahora no se aplica el bloqueo.
    """
    # TODO(RF5): comprobar si el usuario tiene una sanción activa y bloquear
    # el préstamo cuando se implemente el modelo y servicio de sanciones.
    pass


def crear_prestamo(
    db: Session,
    *,
    recurso_id: int,
    prestatario_id: int,
    registrado_por_id: int,
    tipo_prestamo: TipoPrestamo,
    modalidad_uso: ModalidadUso,
    fecha_limite: datetime | None = None,
    reserva_id: int | None = None,
    condicion_entrega: str | None = None,
    garantia: Mapping[str, Any] | None = None,
) -> Prestamo:
    """Registra un préstamo activo y marca el recurso como prestado."""
    if registrado_por_id == prestatario_id:
        raise ConflictoPrestamo("El registrador no puede ser el prestatario")

    recurso = db.get(Recurso, recurso_id)
    if recurso is None:
        raise RegistroPrestamoNoEncontrado("Recurso no encontrado")

    prestatario = db.get(Usuario, prestatario_id)
    if prestatario is None:
        raise RegistroPrestamoNoEncontrado("Prestatario no encontrado")

    registrador = db.get(Usuario, registrado_por_id)
    if registrador is None:
        raise RegistroPrestamoNoEncontrado("Registrador no encontrado")

    if not recurso.disponible:
        raise ConflictoPrestamo("El recurso no está disponible")

    if tipo_prestamo == TipoPrestamo.SIMPLE:
        if recurso.tipo_recurso not in (
            TipoRecurso.LIBRO,
            TipoRecurso.DEPORTIVO,
        ):
            raise ConflictoPrestamo(
                "El préstamo SIMPLE solo se admite para libros e implementos deportivos"
            )
    elif tipo_prestamo in (TipoPrestamo.POR_CURSO, TipoPrestamo.EXCEPCIONAL):
        if recurso.tipo_recurso != TipoRecurso.ACADEMICO:
            raise ConflictoPrestamo(
                "Los préstamos POR_CURSO y EXCEPCIONAL solo se admiten "
                "para implementos académicos"
            )

    if (
        tipo_prestamo == TipoPrestamo.EXCEPCIONAL
        and modalidad_uso != ModalidadUso.RETIRO_TEMPORAL
    ):
        raise ConflictoPrestamo(
            "El préstamo EXCEPCIONAL requiere modalidad RETIRO_TEMPORAL"
        )

    _validar_sancion_activa(db, prestatario_id)

    if fecha_limite is None:
        fecha_limite = _calcular_fecha_limite(
            recurso.tipo_recurso, tipo_prestamo, datetime.now(timezone.utc)
        )

    datos_garantia = Garantia(**dict(garantia)) if garantia is not None else None
    prestamo = Prestamo(
        recurso_id=recurso_id,
        prestatario_id=prestatario_id,
        registrado_por_id=registrado_por_id,
        reserva_id=reserva_id,
        fecha_limite=fecha_limite,
        tipo_prestamo=tipo_prestamo,
        modalidad_uso=modalidad_uso,
        condicion_entrega=condicion_entrega,
        garantia=datos_garantia,
    )
    recurso.estado = EstadoRecurso.PRESTADO
    db.add(prestamo)

    try:
        db.commit()
        db.refresh(prestamo)
    except Exception:
        db.rollback()
        raise

    return prestamo


def registrar_devolucion(
    db: Session,
    *,
    prestamo_id: int,
    condicion_devolucion: str | None = None,
    danado: bool = False,
) -> Prestamo:
    """Registra la devolución y actualiza el estado del recurso."""
    prestamo = db.get(Prestamo, prestamo_id)
    if prestamo is None:
        raise RegistroPrestamoNoEncontrado("Préstamo no encontrado")

    if prestamo.estado not in (EstadoPrestamo.ACTIVO, EstadoPrestamo.ATRASADO):
        raise ConflictoPrestamo("Solo se pueden devolver préstamos activos o atrasados")

    recurso = db.get(Recurso, prestamo.recurso_id)
    if recurso is None:
        raise RegistroPrestamoNoEncontrado("Recurso del préstamo no encontrado")

    prestamo.estado = EstadoPrestamo.DEVUELTO
    prestamo.fecha_devolucion = datetime.now(timezone.utc)
    prestamo.condicion_devolucion = condicion_devolucion
    recurso.estado = (
        EstadoRecurso.MANTENIMIENTO if danado else EstadoRecurso.DISPONIBLE
    )

    try:
        db.commit()
        db.refresh(prestamo)
    except Exception:
        db.rollback()
        raise

    return prestamo


def marcar_prestamos_atrasados(db: Session) -> int:
    """Marca como ATRASADOS los préstamos activos cuyo plazo ya venció."""
    consulta = (
        update(Prestamo)
        .where(
            Prestamo.estado == EstadoPrestamo.ACTIVO,
            Prestamo.fecha_limite < datetime.now(timezone.utc),
        )
        .values(estado=EstadoPrestamo.ATRASADO)
        .execution_options(synchronize_session=False)
    )

    try:
        resultado = db.execute(consulta)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return resultado.rowcount or 0
