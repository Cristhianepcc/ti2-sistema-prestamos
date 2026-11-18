"""Tests de reporte_service (RF6, nivel 1). Ver docs/plan-reportes-rf6.md."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models import (
    EstadoPrestamo,
    EstadoRecurso,
    Garantia,
    Gestor,
    ModalidadUso,
    Prestamo,
    TipoPrestamo,
    TipoRecurso,
)
from app.services.reporte_service import (
    RangoInvalido,
    UsuarioNoEncontrado,
    listar_historial,
    reporte_inventario,
    reporte_prestamos,
    reporte_resumen,
)
from .helpers import crear_recurso, crear_usuario

AHORA = datetime.now(timezone.utc)


def _crear_prestamo(
    db,
    *,
    recurso,
    prestatario,
    registrador,
    estado=EstadoPrestamo.ACTIVO,
    tipo_prestamo=TipoPrestamo.SIMPLE,
    modalidad_uso=ModalidadUso.RETIRO_TEMPORAL,
    fecha_entrega=None,
    fecha_limite=None,
    fecha_devolucion=None,
) -> Prestamo:
    prestamo = Prestamo(
        recurso_id=recurso.id,
        prestatario_id=prestatario.id,
        registrado_por_id=registrador.id,
        estado=estado,
        tipo_prestamo=tipo_prestamo,
        modalidad_uso=modalidad_uso,
        fecha_entrega=fecha_entrega or AHORA,
        fecha_limite=fecha_limite or (AHORA + timedelta(days=7)),
        fecha_devolucion=fecha_devolucion,
    )
    db.add(prestamo)
    db.commit()
    return prestamo


def _agregar_garantia(db, prestamo, *, valor, devuelta=False) -> Garantia:
    garantia = Garantia(prestamo_id=prestamo.id, tipo="CARNET", valor=valor, devuelta=devuelta)
    db.add(garantia)
    db.commit()
    return garantia


# --- Inventario --------------------------------------------------------------


def test_reporte_inventario_vacio_devuelve_ceros_con_todas_las_claves(db_session):
    reporte = reporte_inventario(db_session)

    assert reporte["total_recursos"] == 0
    assert reporte["por_tipo"] == {t: 0 for t in TipoRecurso}
    assert reporte["por_estado"] == {e: 0 for e in EstadoRecurso}
    assert reporte["por_gestor"] == {g: 0 for g in Gestor}
    assert reporte["tipo_por_estado"][TipoRecurso.LIBRO] == {e: 0 for e in EstadoRecurso}


def test_reporte_inventario_cuenta_por_tipo_estado_y_gestor(db_session):
    crear_recurso(db_session, TipoRecurso.LIBRO, "INV-1", estado=EstadoRecurso.DISPONIBLE)
    crear_recurso(db_session, TipoRecurso.LIBRO, "INV-2", estado=EstadoRecurso.PRESTADO)
    crear_recurso(db_session, TipoRecurso.ACADEMICO, "INV-3", estado=EstadoRecurso.MANTENIMIENTO)

    reporte = reporte_inventario(db_session)

    assert reporte["total_recursos"] == 3
    assert reporte["por_tipo"][TipoRecurso.LIBRO] == 2
    assert reporte["por_tipo"][TipoRecurso.ACADEMICO] == 1
    assert reporte["por_gestor"][Gestor.CENTRO_ESTUDIANTES] == 2
    assert reporte["por_gestor"][Gestor.INFRAESTRUCTURA] == 1
    assert reporte["tipo_por_estado"][TipoRecurso.LIBRO][EstadoRecurso.DISPONIBLE] == 1
    assert reporte["tipo_por_estado"][TipoRecurso.LIBRO][EstadoRecurso.PRESTADO] == 1
    assert reporte["tipo_por_estado"][TipoRecurso.ACADEMICO][EstadoRecurso.MANTENIMIENTO] == 1


# --- Reporte de préstamos: vacío y regla de atraso ---------------------------


def test_reporte_prestamos_vacio_devuelve_ceros(db_session):
    reporte = reporte_prestamos(db_session)

    assert reporte["periodo"] == {"desde": None, "hasta": None}
    assert reporte["total_prestamos"] == 0
    assert reporte["por_estado"] == {e: 0 for e in EstadoPrestamo}
    assert reporte["mas_prestados"] == []
    assert reporte["garantias"] == {"retenidas": 0, "valor_retenido": Decimal("0")}
    assert reporte["atrasados"] == {"total": 0, "items": []}


def test_activo_vencido_se_cuenta_como_atrasado_en_reporte_y_resumen(db_session):
    prestatario = crear_usuario(db_session, "ATR-USR")
    registrador = crear_usuario(db_session, "ATR-REG")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "ATR")
    _crear_prestamo(
        db_session,
        recurso=recurso,
        prestatario=prestatario,
        registrador=registrador,
        estado=EstadoPrestamo.ACTIVO,
        fecha_limite=AHORA - timedelta(days=3),
    )

    reporte = reporte_prestamos(db_session)
    assert reporte["por_estado"][EstadoPrestamo.ACTIVO] == 0
    assert reporte["por_estado"][EstadoPrestamo.ATRASADO] == 1
    assert reporte["atrasados"]["total"] == 1
    item = reporte["atrasados"]["items"][0]
    assert item["prestamo_id"] is not None
    assert item["dias_atraso"] == 3
    assert item["recurso"]["codigo"] == recurso.codigo
    assert item["prestatario"]["codigo"] == prestatario.codigo

    resumen = reporte_resumen(db_session)
    assert resumen == {"prestamos_activos": 1, "prestamos_atrasados": 1}


def test_activo_sin_vencer_no_se_cuenta_como_atrasado(db_session):
    prestatario = crear_usuario(db_session, "NOATR-USR")
    registrador = crear_usuario(db_session, "NOATR-REG")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "NOATR")
    _crear_prestamo(
        db_session,
        recurso=recurso,
        prestatario=prestatario,
        registrador=registrador,
        estado=EstadoPrestamo.ACTIVO,
        fecha_limite=AHORA + timedelta(days=3),
    )

    reporte = reporte_prestamos(db_session)
    assert reporte["por_estado"][EstadoPrestamo.ACTIVO] == 1
    assert reporte["por_estado"][EstadoPrestamo.ATRASADO] == 0
    assert reporte["atrasados"]["total"] == 0

    resumen = reporte_resumen(db_session)
    assert resumen == {"prestamos_activos": 1, "prestamos_atrasados": 0}


# --- Filtro de rango ----------------------------------------------------------


def test_filtro_rango_es_inclusive_y_cubre_todo_el_dia_final(db_session):
    prestatario = crear_usuario(db_session, "RANGO-USR")
    registrador = crear_usuario(db_session, "RANGO-REG")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "RANGO")
    desde = (AHORA - timedelta(days=5)).date()
    hasta = AHORA.date()

    antes_del_rango = _crear_prestamo(
        db_session,
        recurso=recurso,
        prestatario=prestatario,
        registrador=registrador,
        fecha_entrega=AHORA - timedelta(days=10),
    )
    en_el_limite_inicial = _crear_prestamo(
        db_session,
        recurso=recurso,
        prestatario=prestatario,
        registrador=registrador,
        fecha_entrega=datetime.combine(desde, datetime.min.time(), tzinfo=timezone.utc),
    )
    al_final_del_dia_hasta = _crear_prestamo(
        db_session,
        recurso=recurso,
        prestatario=prestatario,
        registrador=registrador,
        fecha_entrega=datetime.combine(hasta, datetime.min.time(), tzinfo=timezone.utc)
        + timedelta(hours=23, minutes=59),
    )
    del antes_del_rango, en_el_limite_inicial, al_final_del_dia_hasta

    reporte = reporte_prestamos(db_session, desde=desde, hasta=hasta)

    assert reporte["periodo"] == {"desde": desde, "hasta": hasta}
    assert reporte["total_prestamos"] == 2


def test_desde_mayor_que_hasta_lanza_rango_invalido(db_session):
    with pytest.raises(RangoInvalido):
        reporte_prestamos(db_session, desde=AHORA.date(), hasta=(AHORA - timedelta(days=1)).date())


# --- top y limite_atrasados ---------------------------------------------------


def test_top_limita_mas_prestados_y_atrasados_limita_items_pero_no_el_total(db_session):
    prestatario = crear_usuario(db_session, "TOP-USR")
    registrador = crear_usuario(db_session, "TOP-REG")

    for i in range(3):
        recurso = crear_recurso(db_session, TipoRecurso.LIBRO, f"TOP-{i}")
        _crear_prestamo(db_session, recurso=recurso, prestatario=prestatario, registrador=registrador)

    recurso_atrasos = crear_recurso(db_session, TipoRecurso.LIBRO, "TOP-ATR")
    for i in range(3):
        _crear_prestamo(
            db_session,
            recurso=recurso_atrasos,
            prestatario=prestatario,
            registrador=registrador,
            fecha_limite=AHORA - timedelta(days=1 + i),
        )

    reporte = reporte_prestamos(db_session, top=2, limite_atrasados=2)

    assert len(reporte["mas_prestados"]) == 2
    assert reporte["atrasados"]["total"] == 3
    assert len(reporte["atrasados"]["items"]) == 2
    # Más días de atraso primero.
    dias = [item["dias_atraso"] for item in reporte["atrasados"]["items"]]
    assert dias == sorted(dias, reverse=True)


# --- Garantías retenidas -------------------------------------------------------


def test_garantias_retenidas_solo_cuenta_no_devueltas_de_prestamos_no_devueltos(db_session):
    prestatario = crear_usuario(db_session, "GAR-USR")
    registrador = crear_usuario(db_session, "GAR-REG")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "GAR")

    retenida = _crear_prestamo(
        db_session, recurso=recurso, prestatario=prestatario, registrador=registrador
    )
    _agregar_garantia(db_session, retenida, valor=Decimal("50.00"), devuelta=False)

    ya_devuelta = _crear_prestamo(
        db_session, recurso=recurso, prestatario=prestatario, registrador=registrador
    )
    _agregar_garantia(db_session, ya_devuelta, valor=Decimal("30.00"), devuelta=True)

    prestamo_devuelto = _crear_prestamo(
        db_session,
        recurso=recurso,
        prestatario=prestatario,
        registrador=registrador,
        estado=EstadoPrestamo.DEVUELTO,
        fecha_devolucion=AHORA,
    )
    _agregar_garantia(db_session, prestamo_devuelto, valor=Decimal("20.00"), devuelta=False)

    reporte = reporte_prestamos(db_session)

    assert reporte["garantias"] == {"retenidas": 1, "valor_retenido": Decimal("50.00")}


# --- Historial -----------------------------------------------------------------


def test_historial_calcula_dias_atraso_segun_el_caso(db_session):
    prestatario = crear_usuario(db_session, "HIST-USR")
    registrador = crear_usuario(db_session, "HIST-REG")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "HIST")

    _crear_prestamo(
        db_session,
        recurso=recurso,
        prestatario=prestatario,
        registrador=registrador,
        estado=EstadoPrestamo.DEVUELTO,
        fecha_limite=AHORA - timedelta(days=5),
        fecha_devolucion=AHORA - timedelta(days=6),
    )
    _crear_prestamo(
        db_session,
        recurso=recurso,
        prestatario=prestatario,
        registrador=registrador,
        estado=EstadoPrestamo.DEVUELTO,
        fecha_limite=AHORA - timedelta(days=5),
        fecha_devolucion=AHORA - timedelta(days=1),
    )
    _crear_prestamo(
        db_session,
        recurso=recurso,
        prestatario=prestatario,
        registrador=registrador,
        estado=EstadoPrestamo.ACTIVO,
        fecha_limite=AHORA - timedelta(days=2),
    )
    _crear_prestamo(
        db_session,
        recurso=recurso,
        prestatario=prestatario,
        registrador=registrador,
        estado=EstadoPrestamo.ACTIVO,
        fecha_limite=AHORA + timedelta(days=2),
    )

    historial = listar_historial(db_session, usuario_id=prestatario.id, limite=10)

    dias_por_estado_y_fecha = {
        (item["estado"], item["fecha_devolucion"] is not None): item["dias_atraso"]
        for item in historial["items"]
    }
    assert historial["total"] == 4
    assert dias_por_estado_y_fecha[(EstadoPrestamo.DEVUELTO, True)] in (0, 4)
    valores = [item["dias_atraso"] for item in historial["items"]]
    assert 0 in valores  # a tiempo o sin vencer
    assert any(v > 0 for v in valores)  # tarde o vencido sin devolver


def test_historial_filtra_por_estado_y_pagina(db_session):
    prestatario = crear_usuario(db_session, "HISTPAG-USR")
    registrador = crear_usuario(db_session, "HISTPAG-REG")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "HISTPAG")

    for i in range(3):
        _crear_prestamo(
            db_session,
            recurso=recurso,
            prestatario=prestatario,
            registrador=registrador,
            estado=EstadoPrestamo.DEVUELTO,
            fecha_entrega=AHORA - timedelta(days=i),
            fecha_devolucion=AHORA,
        )
    _crear_prestamo(
        db_session,
        recurso=recurso,
        prestatario=prestatario,
        registrador=registrador,
        estado=EstadoPrestamo.ACTIVO,
        fecha_entrega=AHORA,
    )

    solo_devueltos = listar_historial(
        db_session, usuario_id=prestatario.id, estado=EstadoPrestamo.DEVUELTO
    )
    assert solo_devueltos["total"] == 3

    pagina = listar_historial(db_session, usuario_id=prestatario.id, limite=2, offset=0)
    assert pagina["total"] == 4
    assert len(pagina["items"]) == 2
    # Más reciente primero.
    assert pagina["items"][0]["fecha_entrega"] >= pagina["items"][1]["fecha_entrega"]


def test_historial_usuario_inexistente_lanza_error(db_session):
    with pytest.raises(UsuarioNoEncontrado):
        listar_historial(db_session, usuario_id=999)
