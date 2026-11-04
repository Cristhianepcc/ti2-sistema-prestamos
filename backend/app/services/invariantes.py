"""Invariantes de dominio compartidas entre servicios.

Cada servicio traduce TipoRecursoIncompatible a su propia excepción de
conflicto (ConflictoPrestamo, ConflictoSolicitud), que los routers mapean a 409.
"""
from ..models.enums import TipoPrestamo, TipoRecurso, TipoSolicitud
from ..models.recurso import Recurso


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
