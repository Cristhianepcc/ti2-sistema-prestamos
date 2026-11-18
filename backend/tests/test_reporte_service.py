"""Tests de reporte_service (RF6, nivel 1). Ver docs/plan-reportes-rf6.md."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models import (
    EstadoPrestamo,
    EstadoRecurso,
    Garantia,
    Gestor,
    ModalidadUso,
    Prestamo,
    Rol,
    TipoPrestamo,
    TipoRecurso,
)
from app.services.reporte_service import (
    RangoInvalido,
    UsuarioNoEncontrado,
    _dia_lima,
    _inicio_del_dia,
    evolucion_prestamos,
    listar_historial,
    reporte_inventario,
    reporte_prestamos,
    reporte_resumen,
    reporte_usuarios,
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


# --- Reporte de usuarios ------------------------------------------------------


def test_reporte_usuarios_vacio_devuelve_ceros_con_todas_las_claves(db_session):
    reporte = reporte_usuarios(db_session)

    assert reporte["total_usuarios"] == 0
    assert reporte["por_rol"] == {r: 0 for r in Rol}
    assert reporte["administradores"] == 0


def test_reporte_usuarios_cuenta_por_rol_y_multirol(db_session):
    estudiante = crear_usuario(db_session, "RU-EST")
    estudiante.roles.append(Rol.ESTUDIANTE)
    docente_custodio = crear_usuario(db_session, "RU-MULTI")
    docente_custodio.roles.extend([Rol.DOCENTE, Rol.CUSTODIO_CE])
    admin = crear_usuario(db_session, "RU-ADM")
    admin.roles.append(Rol.ADMINISTRADOR_SISTEMA)
    db_session.commit()

    reporte = reporte_usuarios(db_session)

    assert reporte["total_usuarios"] == 3
    assert reporte["por_rol"][Rol.ESTUDIANTE] == 1
    assert reporte["por_rol"][Rol.DOCENTE] == 1
    assert reporte["por_rol"][Rol.CUSTODIO_CE] == 1
    assert reporte["por_rol"][Rol.ADMINISTRADOR_SISTEMA] == 1
    assert reporte["administradores"] == 1


# --- Reporte de préstamos: vacío y regla de atraso ---------------------------


def test_reporte_prestamos_vacio_devuelve_ceros(db_session):
    reporte = reporte_prestamos(db_session)

    assert reporte["periodo"] == {"desde": None, "hasta": None}
    assert reporte["total_prestamos"] == 0
    assert reporte["por_estado"] == {e: 0 for e in EstadoPrestamo}
    assert reporte["mas_prestados"] == []
    assert reporte["distribucion_roles"] == {
        "ESTUDIANTE": 0,
        "DOCENTE": 0,
        "CUSTODIO": 0,
        "ADMINISTRADOR_SISTEMA": 0,
    }
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
    assert resumen["prestamos_activos"] == 1
    assert resumen["prestamos_atrasados"] == 1


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
    assert resumen["prestamos_activos"] == 1
    assert resumen["prestamos_atrasados"] == 0


# --- Límite de "día": Arequipa (UTC-5), no UTC --------------------------------
#
# Importante para quien toque esto: SQLite descarta el offset de timezone al
# guardar un DateTime(timezone=True) (confirmado con una prueba directa:
# '2026-11-13 00:00:00+00' y '2026-11-13 00:00:00-05' se guardan y se
# COMPARAN igual en SQLite, como si fueran el mismo instante — en PostgreSQL
# NO son el mismo instante, hay 5 horas de diferencia real). Por eso un test
# que arma un filtro de fecha y corre una consulta contra `db_session`
# (SQLite) no puede detectar un bug de offset: pasa igual con el offset bien
# o mal puesto. Estos dos tests prueban las funciones puras directamente, sin
# pasar por una consulta, que es el único nivel donde SQLite no puede mentir.


def test_inicio_del_dia_es_medianoche_de_arequipa_no_de_utc():
    inicio = _inicio_del_dia(date(2026, 11, 13))
    # Medianoche en Arequipa (UTC-5) es las 05:00 UTC, no las 00:00 UTC.
    assert inicio == datetime(2026, 11, 13, 5, 0, tzinfo=timezone.utc)


def test_dia_lima_no_confunde_el_dia_utc_con_el_dia_de_arequipa():
    # Las 20:00 en Arequipa del 17 de noviembre ya son las 01:00 UTC del 18.
    instante = datetime(2026, 11, 18, 1, 0, tzinfo=timezone.utc)
    assert _dia_lima(instante) == date(2026, 11, 17)


# --- Filtro de rango ----------------------------------------------------------


def test_filtro_rango_es_inclusive_y_cubre_todo_el_dia_final(db_session):
    # Nota: por la limitación de SQLite descrita arriba, este test no puede
    # detectar un corrimiento de huso horario en el límite — solo confirma
    # que el rango es inclusivo en términos generales. El límite real
    # (Arequipa vs. UTC) lo prueban test_inicio_del_dia_* y test_dia_lima_*.
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


def test_hasta_futuro_lanza_rango_invalido(db_session):
    with pytest.raises(RangoInvalido):
        reporte_prestamos(db_session, hasta=(AHORA + timedelta(days=7)).date())


def test_desde_futuro_lanza_rango_invalido(db_session):
    with pytest.raises(RangoInvalido):
        reporte_prestamos(db_session, desde=(AHORA + timedelta(days=1)).date())


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


# --- Distribución de préstamos por rol -----------------------------------------


def test_distribucion_roles_no_cuenta_dos_veces_a_un_prestatario_multirol(db_session):
    registrador = crear_usuario(db_session, "DR-REG")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "DR-1")
    docente_custodio = crear_usuario(db_session, "DR-MULTI")
    docente_custodio.roles.extend([Rol.DOCENTE, Rol.CUSTODIO_CE])
    db_session.commit()
    _crear_prestamo(db_session, recurso=recurso, prestatario=docente_custodio, registrador=registrador)

    reporte = reporte_prestamos(db_session)

    # Gana el rol menos común: CUSTODIO_CE pesa más que DOCENTE.
    assert reporte["distribucion_roles"]["CUSTODIO"] == 1
    assert reporte["distribucion_roles"]["DOCENTE"] == 0
    assert sum(reporte["distribucion_roles"].values()) == 1


def test_distribucion_roles_funde_custodio_ce_e_infra(db_session):
    registrador = crear_usuario(db_session, "DR-REG2")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "DR-2")
    custodio_ce = crear_usuario(db_session, "DR-CE")
    custodio_ce.roles.append(Rol.CUSTODIO_CE)
    custodio_infra = crear_usuario(db_session, "DR-INFRA")
    custodio_infra.roles.append(Rol.CUSTODIO_INFRA)
    db_session.commit()
    _crear_prestamo(db_session, recurso=recurso, prestatario=custodio_ce, registrador=registrador)
    _crear_prestamo(db_session, recurso=recurso, prestatario=custodio_infra, registrador=registrador)

    reporte = reporte_prestamos(db_session)

    assert reporte["distribucion_roles"]["CUSTODIO"] == 2


def test_distribucion_roles_admin_gana_sobre_cualquier_otro_rol(db_session):
    registrador = crear_usuario(db_session, "DR-REG3")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "DR-3")
    estudiante_admin = crear_usuario(db_session, "DR-ADM")
    estudiante_admin.roles.extend([Rol.ESTUDIANTE, Rol.ADMINISTRADOR_SISTEMA])
    db_session.commit()
    _crear_prestamo(db_session, recurso=recurso, prestatario=estudiante_admin, registrador=registrador)

    reporte = reporte_prestamos(db_session)

    assert reporte["distribucion_roles"]["ADMINISTRADOR_SISTEMA"] == 1
    assert reporte["distribucion_roles"]["ESTUDIANTE"] == 0


# --- Resumen general ------------------------------------------------------------


def test_reporte_resumen_cuenta_usuarios_recursos_y_prestamos(db_session):
    prestatario = crear_usuario(db_session, "RES-USR")
    registrador = crear_usuario(db_session, "RES-REG")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "RES")
    _crear_prestamo(db_session, recurso=recurso, prestatario=prestatario, registrador=registrador)

    resumen = reporte_resumen(db_session)

    assert resumen["total_usuarios"] == 2
    assert resumen["total_recursos"] == 1
    assert resumen["total_prestamos"] == 1


# --- Evolución de préstamos ------------------------------------------------------


def test_evolucion_vacio_devuelve_puntos_en_cero_ultimos_30_dias(db_session):
    reporte = evolucion_prestamos(db_session)

    assert reporte["granularidad"] == "dia"
    assert len(reporte["puntos"]) == 30
    assert all(p["prestamos"] == 0 and p["devoluciones"] == 0 for p in reporte["puntos"])


def test_evolucion_agrupa_por_dia_en_un_rango_corto(db_session):
    prestatario = crear_usuario(db_session, "EVO-USR")
    registrador = crear_usuario(db_session, "EVO-REG")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "EVO")
    hoy = AHORA.date()
    _crear_prestamo(
        db_session,
        recurso=recurso,
        prestatario=prestatario,
        registrador=registrador,
        fecha_entrega=AHORA - timedelta(days=2),
        estado=EstadoPrestamo.DEVUELTO,
        fecha_devolucion=AHORA,
    )

    reporte = evolucion_prestamos(db_session, desde=hoy - timedelta(days=6), hasta=hoy)

    assert reporte["granularidad"] == "dia"
    por_fecha = {p["fecha"]: p for p in reporte["puntos"]}
    assert por_fecha[(AHORA - timedelta(days=2)).date()]["prestamos"] == 1
    assert por_fecha[hoy]["devoluciones"] == 1


def test_evolucion_agrupa_por_mes_en_un_rango_largo(db_session):
    prestatario = crear_usuario(db_session, "EVOM-USR")
    registrador = crear_usuario(db_session, "EVOM-REG")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "EVOM")
    hoy = AHORA.date()
    _crear_prestamo(
        db_session, recurso=recurso, prestatario=prestatario, registrador=registrador, fecha_entrega=AHORA
    )

    reporte = evolucion_prestamos(db_session, desde=hoy - timedelta(days=120), hasta=hoy)

    assert reporte["granularidad"] == "mes"
    por_fecha = {p["fecha"]: p for p in reporte["puntos"]}
    assert por_fecha[hoy.replace(day=1)]["prestamos"] == 1


def test_evolucion_cuenta_devolucion_de_prestamo_entregado_antes_del_rango(db_session):
    """Regresión: un préstamo entregado antes de `desde` pero devuelto dentro
    del rango debe aparecer en la serie de devoluciones."""
    prestatario = crear_usuario(db_session, "EVOD-USR")
    registrador = crear_usuario(db_session, "EVOD-REG")
    recurso = crear_recurso(db_session, TipoRecurso.LIBRO, "EVOD")
    hoy = AHORA.date()
    _crear_prestamo(
        db_session,
        recurso=recurso,
        prestatario=prestatario,
        registrador=registrador,
        fecha_entrega=AHORA - timedelta(days=20),
        estado=EstadoPrestamo.DEVUELTO,
        fecha_devolucion=AHORA,
    )

    reporte = evolucion_prestamos(db_session, desde=hoy - timedelta(days=6), hasta=hoy)

    por_fecha = {p["fecha"]: p for p in reporte["puntos"]}
    assert por_fecha[hoy]["devoluciones"] == 1
    assert sum(p["prestamos"] for p in reporte["puntos"]) == 0


def test_evolucion_rango_invalido(db_session):
    hoy = AHORA.date()
    with pytest.raises(RangoInvalido):
        evolucion_prestamos(db_session, desde=hoy, hasta=hoy - timedelta(days=1))
    with pytest.raises(RangoInvalido):
        evolucion_prestamos(db_session, hasta=hoy + timedelta(days=1))


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
