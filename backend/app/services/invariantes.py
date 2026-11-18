"""Invariantes de dominio compartidas entre servicios.

Cada servicio traduce TipoRecursoIncompatible/FueraDeHorarioLaboral a su propia
excepción de conflicto (ConflictoPrestamo, ConflictoReserva, ConflictoSolicitud),
que los routers mapean a 409.
"""
from datetime import date, time, timedelta, timezone

from ..models.enums import TipoPrestamo, TipoRecurso, TipoSolicitud
from ..models.recurso import Recurso

#: Perú no observa horario de verano; offset fijo (ver reserva_service, donde
#: vivía esta constante originalmente).
ZONA_LIMA = timezone(timedelta(hours=-5))


class TipoRecursoIncompatible(Exception):
    """El tipo (de préstamo o solicitud) no corresponde al tipo de recurso."""


def validar_tipo_recurso(tipo: TipoPrestamo | TipoSolicitud, recurso: Recurso) -> None:
    """Invariante estricto tipo ↔ recurso (docs/00-contexto §4 y §8, #4).

    SIMPLE solo para libros/deportivos; POR_CURSO y EXCEPCIONAL solo para
    implementos académicos. TipoPrestamo y TipoSolicitud comparten valores, por
    eso se compara por `.value`.
    """
    if tipo.value == "SIMPLE":
        if recurso.tipo_recurso not in (TipoRecurso.LIBRO, TipoRecurso.DEPORTIVO):
            raise TipoRecursoIncompatible(
                "El tipo SIMPLE solo se admite para libros e implementos deportivos"
            )
    elif recurso.tipo_recurso != TipoRecurso.ACADEMICO:
        raise TipoRecursoIncompatible(
            "Los tipos POR_CURSO y EXCEPCIONAL solo se admiten para implementos académicos"
        )


class FueraDeHorarioLaboral(Exception):
    """El día o la hora caen fuera de la atención de Centro de Estudiantes/Infraestructura."""


_HORA_APERTURA = time(8, 0)
_HORA_CIERRE = time(19, 0)


def validar_dia_laboral(fecha: date) -> None:
    """Centro de Estudiantes e Infraestructura no atienden sábado ni domingo.

    Aplica tanto al día en que se entrega un préstamo (el "ahora" de quien
    registra) como al día elegido para una reserva futura.
    """
    if fecha.weekday() >= 5:  # 5 = sábado, 6 = domingo
        raise FueraDeHorarioLaboral(
            "Centro de Estudiantes e Infraestructura no atienden sábados ni domingos"
        )


def validar_hora_laboral(inicio: time, fin: time | None = None) -> None:
    """Centro de Estudiantes e Infraestructura solo atienden de 8:00 a 19:00.

    `fin` es opcional: un préstamo valida un solo instante (el momento de la
    entrega); una franja de reserva valida que *todo* el rango quede dentro
    del horario, no solo el inicio.
    """
    mensaje = "Centro de Estudiantes e Infraestructura solo atienden de 8:00 a 19:00"
    if inicio < _HORA_APERTURA or inicio >= _HORA_CIERRE:
        raise FueraDeHorarioLaboral(mensaje)
    if fin is not None and fin > _HORA_CIERRE:
        raise FueraDeHorarioLaboral(mensaje)


def siguiente_dia_laboral(fecha: date) -> date:
    """Si `fecha` cae sábado o domingo, la corre al lunes siguiente.

    A diferencia de `validar_dia_laboral` (que rechaza), esto corrige: lo usa
    `prestamo_service._calcular_fecha_limite` para que un vencimiento calculado
    nunca caiga un día que nadie trabaja (si no, el prestatario no tendría
    forma de devolver a tiempo por un problema que no es suyo).
    """
    while fecha.weekday() >= 5:
        fecha += timedelta(days=1)
    return fecha
