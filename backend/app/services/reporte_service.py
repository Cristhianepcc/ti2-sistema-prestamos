"""Historial de préstamos y reportes de solo lectura (RF6).

Ver docs/plan-reportes-rf6.md. Todo se calcula en cada petición con `GROUP BY`
en la base de datos (RNF3): no se carga la tabla completa a Python para
contar. No se persiste nada nuevo; no hay tabla `reporte`.
"""
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..models.enums import (
    EstadoPrestamo,
    EstadoRecurso,
    Gestor,
    ModalidadUso,
    Rol,
    TipoPrestamo,
    TipoRecurso,
)
from ..models.prestamo import Garantia, Prestamo
from ..models.recurso import Recurso
from ..models.usuario import Usuario, UsuarioRol
from .invariantes import ZONA_LIMA


class ReporteError(Exception):
    """Error de negocio de historial/reportes."""


class UsuarioNoEncontrado(ReporteError):
    """El `usuario_id` pedido no existe."""


class RecursoNoEncontrado(ReporteError):
    """El `recurso_id` pedido no existe."""


class RangoInvalido(ReporteError):
    """`desde` es posterior a `hasta`."""


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _en_utc(valor: datetime) -> datetime:
    return valor if valor.tzinfo is not None else valor.replace(tzinfo=timezone.utc)


def _dia_lima(fecha: datetime) -> date:
    """Fecha calendario en hora de Arequipa (UTC-5), no UTC.

    `fecha` puede caer en el día UTC siguiente/anterior al día real en
    Arequipa (ej. 20:00 en Arequipa es ya 01:00 UTC del día siguiente); todo
    lo que agrupe o compare por "día" acá debe pasar por esta función, no por
    `.date()` directo sobre un datetime en UTC.
    """
    return _en_utc(fecha).astimezone(ZONA_LIMA).date()


def _inicio_del_dia(dia: date) -> datetime:
    """Medianoche de `dia` en Arequipa, no en UTC (son 5 horas de diferencia):
    así `desde`/`hasta` representan días de calendario reales, no un corte
    corrido a las 19:00 del día anterior."""
    return datetime.combine(dia, time.min, tzinfo=ZONA_LIMA)


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


def _validar_rango(desde: date | None, hasta: date | None, *, hoy: date) -> None:
    """Regla de rango compartida por `reporte_prestamos` y `evolucion_prestamos`."""
    if desde is not None and hasta is not None and desde > hasta:
        raise RangoInvalido("`desde` no puede ser posterior a `hasta`")
    if (desde is not None and desde > hoy) or (hasta is not None and hasta > hoy):
        raise RangoInvalido("El rango no puede ser una fecha futura")


# Prioridad para elegir el rol "dominante" de un prestatario con varios roles,
# así un préstamo nunca se cuenta dos veces en `distribucion_roles` (sección
# "Demanda de recursos" del rediseño de Reportes): gana el rol menos común.
_PRIORIDAD_ROL_DOMINANTE = [
    Rol.ADMINISTRADOR_SISTEMA,
    Rol.CUSTODIO_CE,
    Rol.CUSTODIO_INFRA,
    Rol.DOCENTE,
    Rol.ESTUDIANTE,
]


def _rol_dominante(roles: set[Rol]) -> Rol:
    for rol in _PRIORIDAD_ROL_DOMINANTE:
        if rol in roles:
            return rol
    return Rol.ESTUDIANTE


def _categoria_distribucion(rol: Rol) -> str:
    if rol in (Rol.CUSTODIO_CE, Rol.CUSTODIO_INFRA):
        return "CUSTODIO"
    return rol.value


def listar_historial(
    db: Session,
    *,
    usuario_id: int,
    estado: EstadoPrestamo | None = None,
    limite: int = 20,
    offset: int = 0,
) -> dict:
    """Historial de préstamos de un usuario, el más reciente primero.

    `estado` usa la misma regla única de "atrasado" que el resto de Reportes
    (`_condicion_atrasado`): filtrar por `ATRASADO` también trae los que
    siguen guardados como `ACTIVO` en BD pero ya vencieron (nada invoca
    `marcar_prestamos_atrasados()` todavía), y filtrar por `ACTIVO` los
    excluye. Sin esto, un préstamo vencido podía aparecer como "Activo" en
    Historial y no salir al filtrar "Atrasado", aunque su `dias_atraso` ya
    fuera positivo.
    """
    if db.get(Usuario, usuario_id) is None:
        raise UsuarioNoEncontrado("Usuario no encontrado")

    ahora = _ahora()
    filtros = [Prestamo.prestatario_id == usuario_id]
    if estado == EstadoPrestamo.ATRASADO:
        filtros.append(_condicion_atrasado(ahora))
    elif estado == EstadoPrestamo.ACTIVO:
        filtros.append(Prestamo.estado == EstadoPrestamo.ACTIVO)
        filtros.append(Prestamo.fecha_limite >= ahora)
    elif estado is not None:
        filtros.append(Prestamo.estado == estado)

    total = db.scalar(select(func.count()).select_from(Prestamo).where(*filtros)) or 0

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
            "estado": (
                EstadoPrestamo.ATRASADO
                if p.estado == EstadoPrestamo.ACTIVO and _en_utc(p.fecha_limite) < ahora
                else p.estado
            ),
            "fecha_entrega": p.fecha_entrega,
            "fecha_limite": p.fecha_limite,
            "fecha_devolucion": p.fecha_devolucion,
            "dias_atraso": _dias_atraso(p.fecha_limite, p.fecha_devolucion, ahora),
        }
        for p in prestamos
    ]
    return {"total": total, "limite": limite, "offset": offset, "items": items}


def historial_recurso(
    db: Session,
    *,
    recurso_id: int,
    limite: int = 20,
    offset: int = 0,
) -> dict:
    """Historial de préstamos de un recurso: quién lo tuvo, cuándo, y si volvió
    dañado o perdido (RF6). Simétrico a `listar_historial`, pero por recurso en
    vez de por usuario; lo usa el admin para rastrear incidencias de un ítem
    puntual del inventario.
    """
    recurso = db.get(Recurso, recurso_id)
    if recurso is None:
        raise RecursoNoEncontrado("Recurso no encontrado")

    filtros = [Prestamo.recurso_id == recurso_id]
    total = db.scalar(select(func.count()).select_from(Prestamo).where(*filtros)) or 0

    filas = db.execute(
        select(Prestamo, Usuario)
        .join(Usuario, Usuario.id == Prestamo.prestatario_id)
        .where(*filtros)
        .order_by(Prestamo.fecha_entrega.desc())
        .limit(limite)
        .offset(offset)
    ).all()

    items = [
        {
            "prestamo_id": p.id,
            "prestatario": {"id": u.id, "codigo": u.codigo, "nombres": u.nombres},
            "tipo_prestamo": p.tipo_prestamo,
            "modalidad_uso": p.modalidad_uso,
            "estado": p.estado,
            "fecha_entrega": p.fecha_entrega,
            "fecha_limite": p.fecha_limite,
            "fecha_devolucion": p.fecha_devolucion,
            "condicion_entrega": p.condicion_entrega,
            "condicion_devolucion": p.condicion_devolucion,
            "danado": p.danado,
            "perdido": p.perdido,
        }
        for p, u in filas
    ]
    return {
        "recurso": {
            "id": recurso.id,
            "codigo": recurso.codigo,
            "nombre": recurso.nombre,
            "tipo_recurso": recurso.tipo_recurso,
            "estado": recurso.estado,
        },
        "total": total,
        "limite": limite,
        "offset": offset,
        "items": items,
    }


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


def reporte_usuarios(db: Session) -> dict:
    """Resumen de cuentas para el admin: cuántas hay y con qué roles.

    `por_rol` cuenta filas de `usuario_rol`, no usuarios: alguien con dos
    roles suma en ambos (igual que el panel de Inicio que reemplaza).
    """
    total_usuarios = db.scalar(select(func.count()).select_from(Usuario)) or 0
    por_rol = _contar_enum(db, UsuarioRol.rol, Rol, [])
    return {
        "total_usuarios": total_usuarios,
        "por_rol": por_rol,
        "administradores": por_rol[Rol.ADMINISTRADOR_SISTEMA],
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
    ahora = _ahora()
    _validar_rango(desde, hasta, hoy=ahora.date())

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

    roles_por_prestamo: dict[int, set[Rol]] = defaultdict(set)
    for prestamo_id, rol in db.execute(
        select(Prestamo.id, UsuarioRol.rol)
        .join(UsuarioRol, UsuarioRol.usuario_id == Prestamo.prestatario_id)
        .where(*filtros_rango)
    ).all():
        roles_por_prestamo[prestamo_id].add(rol)
    distribucion_roles = {"ESTUDIANTE": 0, "DOCENTE": 0, "CUSTODIO": 0, "ADMINISTRADOR_SISTEMA": 0}
    for roles in roles_por_prestamo.values():
        distribucion_roles[_categoria_distribucion(_rol_dominante(roles))] += 1

    # Cuenta lo que haya en la tabla `garantia`, pero hoy nada la llena en uso
    # real: la pantalla de "Aceptar" del custodio no tiene campo de garantía
    # (ver TODO en frontend/js/solicitudes.js). Sin seeds de ejemplo, esto da 0.
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
        "distribucion_roles": distribucion_roles,
        "garantias": {
            "retenidas": retenidas or 0,
            "valor_retenido": valor_retenido if valor_retenido is not None else Decimal("0.00"),
        },
        "atrasados": {"total": total_atrasados, "items": items_atrasados},
    }


def reporte_resumen(db: Session) -> dict:
    """Resumen liviano para la tarjeta de Inicio del administrador y los 4 KPIs
    de "Resumen general" en Reportes (una sola llamada para los cuatro)."""
    ahora = _ahora()
    total_usuarios = db.scalar(select(func.count()).select_from(Usuario)) or 0
    total_recursos = db.scalar(select(func.count()).select_from(Recurso)) or 0
    total_prestamos = db.scalar(select(func.count()).select_from(Prestamo)) or 0
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
    return {
        "total_usuarios": total_usuarios,
        "total_recursos": total_recursos,
        "total_prestamos": total_prestamos,
        "prestamos_activos": prestamos_activos,
        "prestamos_atrasados": prestamos_atrasados,
    }


def evolucion_prestamos(db: Session, *, desde: date | None = None, hasta: date | None = None) -> dict:
    """Serie temporal de préstamos entregados vs. devueltos, para el gráfico
    de líneas de "Actividad de préstamos". Por defecto, últimos 30 días.

    Bucketing en Python (no SQL) a propósito: las consultas de `reporte_service`
    evitan funciones de fecha específicas de un motor (tests en SQLite,
    producción en PostgreSQL). Solo se traen las 2 columnas de fecha que hacen
    falta, no filas completas (RNF3).
    """
    ahora = _ahora()
    hoy = ahora.date()
    _validar_rango(desde, hasta, hoy=hoy)
    if hasta is None:
        hasta = hoy
    if desde is None:
        desde = hasta - timedelta(days=29)

    inicio_rango = _inicio_del_dia(desde)
    fin_rango = _inicio_del_dia(hasta + timedelta(days=1))
    filas = db.execute(
        select(Prestamo.fecha_entrega, Prestamo.fecha_devolucion).where(
            or_(
                (Prestamo.fecha_entrega >= inicio_rango) & (Prestamo.fecha_entrega < fin_rango),
                (Prestamo.fecha_devolucion >= inicio_rango) & (Prestamo.fecha_devolucion < fin_rango),
            )
        )
    ).all()

    dias_en_rango = (hasta - desde).days + 1
    granularidad = "dia" if dias_en_rango <= 62 else "mes"

    def _bucket(fecha: datetime) -> date:
        fecha = _dia_lima(fecha)
        return fecha if granularidad == "dia" else fecha.replace(day=1)

    # Un préstamo puede aparecer en `filas` por su entrega, por su devolución,
    # o por ambas (si las dos cayeron en el rango): cada serie se cuenta por
    # separado y cada una revisa su propia fecha contra `[desde, hasta]`, así
    # que una devolución tardía de un préstamo entregado antes del rango sí
    # se grafica, y un préstamo entregado en el rango pero devuelto después no
    # infla la serie de devoluciones.
    prestamos_por_bucket: dict[date, int] = defaultdict(int)
    devoluciones_por_bucket: dict[date, int] = defaultdict(int)
    for fecha_entrega, fecha_devolucion in filas:
        fecha_entrega_dia = _dia_lima(fecha_entrega)
        if desde <= fecha_entrega_dia <= hasta:
            prestamos_por_bucket[_bucket(fecha_entrega)] += 1
        if fecha_devolucion is not None:
            fecha_devolucion_dia = _dia_lima(fecha_devolucion)
            if desde <= fecha_devolucion_dia <= hasta:
                devoluciones_por_bucket[_bucket(fecha_devolucion)] += 1

    buckets: list[date] = []
    cursor = desde if granularidad == "dia" else desde.replace(day=1)
    paso = timedelta(days=1)
    limite = hasta if granularidad == "dia" else hasta.replace(day=1)
    while cursor <= limite:
        buckets.append(cursor)
        if granularidad == "dia":
            cursor += paso
        else:
            siguiente_mes = cursor.month % 12 + 1
            siguiente_anio = cursor.year + (1 if cursor.month == 12 else 0)
            cursor = cursor.replace(year=siguiente_anio, month=siguiente_mes)

    puntos = [
        {
            "fecha": bucket,
            "prestamos": prestamos_por_bucket.get(bucket, 0),
            "devoluciones": devoluciones_por_bucket.get(bucket, 0),
        }
        for bucket in buckets
    ]

    return {
        "granularidad": granularidad,
        "periodo": {"desde": desde, "hasta": hasta},
        "puntos": puntos,
    }
