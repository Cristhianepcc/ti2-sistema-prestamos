"""Historial de préstamos y reportes de solo lectura (RF6).

Ver docs/plan-reportes-rf6.md. Todo se calcula en cada petición con `GROUP BY`
en la base de datos (RNF3): no se carga la tabla completa a Python para
contar. No se persiste nada nuevo; no hay tabla `reporte`.
"""
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..models.enums import (
    EstadoPrestamo,
    EstadoRecurso,
    Gestor,
    ModalidadUso,
    TipoPrestamo,
    TipoRecurso,
)
from ..models.prestamo import Garantia, Prestamo
from ..models.recurso import Recurso
from ..models.usuario import Usuario


class ReporteError(Exception):
    """Error de negocio de historial/reportes."""


class UsuarioNoEncontrado(ReporteError):
    """El `usuario_id` pedido no existe."""


class RangoInvalido(ReporteError):
    """`desde` es posterior a `hasta`."""


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _en_utc(valor: datetime) -> datetime:
    return valor if valor.tzinfo is not None else valor.replace(tzinfo=timezone.utc)


def _inicio_del_dia(dia: date) -> datetime:
    return datetime.combine(dia, time.min, tzinfo=timezone.utc)


def _condicion_atrasado(ahora: datetime):
    """`estado IN (ACTIVO, ATRASADO)` y `fecha_limite < ahora`.

    Regla única de "atrasado" (plan §5): el estado `ATRASADO` guardado en BD
    no es fiable porque nada invoca `marcar_prestamos_atrasados()` todavía.
    La usan `por_estado`, `atrasados`, `reporte_resumen` e `historial`
    (`dias_atraso`) por igual.
    """
    return Prestamo.estado.in_((EstadoPrestamo.ACTIVO, EstadoPrestamo.ATRASADO)) & (
        Prestamo.fecha_limite < ahora
    )


def _dias_atraso(fecha_limite: datetime, fecha_devolucion: datetime | None, ahora: datetime) -> int:
    referencia = _en_utc(fecha_devolucion) if fecha_devolucion else ahora
    return max((referencia - _en_utc(fecha_limite)).days, 0)


def _contar_enum(db: Session, columna, enum_cls, filtros: Sequence) -> dict:
    conteo = {valor: 0 for valor in enum_cls}
    filas = db.execute(select(columna, func.count()).where(*filtros).group_by(columna)).all()
    for valor, total in filas:
        conteo[valor] = total
    return conteo


def listar_historial(
    db: Session,
    *,
    usuario_id: int,
    estado: EstadoPrestamo | None = None,
    limite: int = 20,
    offset: int = 0,
) -> dict:
    """Historial de préstamos de un usuario, el más reciente primero."""
    if db.get(Usuario, usuario_id) is None:
        raise UsuarioNoEncontrado("Usuario no encontrado")

    filtros = [Prestamo.prestatario_id == usuario_id]
    if estado is not None:
        filtros.append(Prestamo.estado == estado)

    total = db.scalar(select(func.count()).select_from(Prestamo).where(*filtros)) or 0

    ahora = _ahora()
    prestamos = db.scalars(
        select(Prestamo)
        .where(*filtros)
        .options(selectinload(Prestamo.recurso))
        .order_by(Prestamo.fecha_entrega.desc())
        .limit(limite)
        .offset(offset)
    ).all()

    items = [
        {
            "prestamo_id": p.id,
            "recurso": {
                "id": p.recurso.id,
                "codigo": p.recurso.codigo,
                "nombre": p.recurso.nombre,
                "tipo_recurso": p.recurso.tipo_recurso,
            },
            "tipo_prestamo": p.tipo_prestamo,
            "modalidad_uso": p.modalidad_uso,
            "estado": p.estado,
            "fecha_entrega": p.fecha_entrega,
            "fecha_limite": p.fecha_limite,
            "fecha_devolucion": p.fecha_devolucion,
            "dias_atraso": _dias_atraso(p.fecha_limite, p.fecha_devolucion, ahora),
        }
        for p in prestamos
    ]
    return {"total": total, "limite": limite, "offset": offset, "items": items}


def reporte_inventario(db: Session) -> dict:
    """Foto del inventario al momento de la consulta."""
    total_recursos = db.scalar(select(func.count()).select_from(Recurso)) or 0
    por_tipo = _contar_enum(db, Recurso.tipo_recurso, TipoRecurso, [])
    por_estado = _contar_enum(db, Recurso.estado, EstadoRecurso, [])
    por_gestor = _contar_enum(db, Recurso.gestor, Gestor, [])

    tipo_por_estado = {tipo: {estado: 0 for estado in EstadoRecurso} for tipo in TipoRecurso}
    filas = db.execute(
        select(Recurso.tipo_recurso, Recurso.estado, func.count()).group_by(
            Recurso.tipo_recurso, Recurso.estado
        )
    ).all()
    for tipo, estado, total in filas:
        tipo_por_estado[tipo][estado] = total

    return {
        "total_recursos": total_recursos,
        "por_tipo": por_tipo,
        "por_estado": por_estado,
        "por_gestor": por_gestor,
        "tipo_por_estado": tipo_por_estado,
    }


def reporte_prestamos(
    db: Session,
    *,
    desde: date | None = None,
    hasta: date | None = None,
    top: int = 5,
    limite_atrasados: int = 50,
) -> dict:
    """Totales de préstamos en `[desde, hasta]`, más la foto actual de atrasados."""
    if desde is not None and hasta is not None and desde > hasta:
        raise RangoInvalido("`desde` no puede ser posterior a `hasta`")

    ahora = _ahora()
    filtros_rango = []
    if desde is not None:
        filtros_rango.append(Prestamo.fecha_entrega >= _inicio_del_dia(desde))
    if hasta is not None:
        filtros_rango.append(Prestamo.fecha_entrega < _inicio_del_dia(hasta + timedelta(days=1)))

    total_prestamos = (
        db.scalar(select(func.count()).select_from(Prestamo).where(*filtros_rango)) or 0
    )

    por_estado = _contar_enum(db, Prestamo.estado, EstadoPrestamo, filtros_rango)
    vencidos_activos = (
        db.scalar(
            select(func.count())
            .select_from(Prestamo)
            .where(
                *filtros_rango,
                Prestamo.estado == EstadoPrestamo.ACTIVO,
                Prestamo.fecha_limite < ahora,
            )
        )
        or 0
    )
    por_estado[EstadoPrestamo.ACTIVO] -= vencidos_activos
    por_estado[EstadoPrestamo.ATRASADO] += vencidos_activos

    por_tipo = _contar_enum(db, Prestamo.tipo_prestamo, TipoPrestamo, filtros_rango)
    por_modalidad = _contar_enum(db, Prestamo.modalidad_uso, ModalidadUso, filtros_rango)

    mas_prestados = [
        {"recurso_id": id_, "codigo": codigo, "nombre": nombre, "total": total}
        for id_, codigo, nombre, total in db.execute(
            select(Recurso.id, Recurso.codigo, Recurso.nombre, func.count(Prestamo.id))
            .join(Prestamo, Prestamo.recurso_id == Recurso.id)
            .where(*filtros_rango)
            .group_by(Recurso.id, Recurso.codigo, Recurso.nombre)
            .order_by(func.count(Prestamo.id).desc())
            .limit(top)
        ).all()
    ]

    retenidas, valor_retenido = db.execute(
        select(func.count(Garantia.id), func.sum(Garantia.valor))
        .join(Prestamo, Prestamo.id == Garantia.prestamo_id)
        .where(
            *filtros_rango,
            Garantia.devuelta.is_(False),
            Prestamo.estado != EstadoPrestamo.DEVUELTO,
        )
    ).one()

    condicion_atraso = _condicion_atrasado(ahora)
    total_atrasados = (
        db.scalar(select(func.count()).select_from(Prestamo).where(condicion_atraso)) or 0
    )
    filas_atrasados = db.execute(
        select(Prestamo, Recurso, Usuario)
        .join(Recurso, Prestamo.recurso_id == Recurso.id)
        .join(Usuario, Prestamo.prestatario_id == Usuario.id)
        .where(condicion_atraso)
        .order_by(Prestamo.fecha_limite.asc())
        .limit(limite_atrasados)
    ).all()
    items_atrasados = [
        {
            "prestamo_id": prestamo.id,
            "recurso": {"id": recurso.id, "codigo": recurso.codigo, "nombre": recurso.nombre},
            "prestatario": {
                "id": usuario.id,
                "codigo": usuario.codigo,
                "nombres": usuario.nombres,
            },
            "fecha_limite": prestamo.fecha_limite,
            "dias_atraso": _dias_atraso(prestamo.fecha_limite, None, ahora),
        }
        for prestamo, recurso, usuario in filas_atrasados
    ]

    return {
        "periodo": {"desde": desde, "hasta": hasta},
        "total_prestamos": total_prestamos,
        "por_estado": por_estado,
        "por_tipo": por_tipo,
        "por_modalidad": por_modalidad,
        "mas_prestados": mas_prestados,
        "garantias": {
            "retenidas": retenidas or 0,
            "valor_retenido": valor_retenido if valor_retenido is not None else Decimal("0.00"),
        },
        "atrasados": {"total": total_atrasados, "items": items_atrasados},
    }


def reporte_resumen(db: Session) -> dict:
    """Resumen liviano para la tarjeta de Inicio del administrador."""
    ahora = _ahora()
    prestamos_activos = (
        db.scalar(
            select(func.count())
            .select_from(Prestamo)
            .where(Prestamo.estado != EstadoPrestamo.DEVUELTO)
        )
        or 0
    )
    prestamos_atrasados = (
        db.scalar(select(func.count()).select_from(Prestamo).where(_condicion_atrasado(ahora)))
        or 0
    )
    return {"prestamos_activos": prestamos_activos, "prestamos_atrasados": prestamos_atrasados}
