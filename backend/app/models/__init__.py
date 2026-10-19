"""Entidades ORM (SQLAlchemy). Ver docs/01-sdd.md §3."""

from .enums import EstadoReserva, EstadoRecurso, Gestor, Rol, TipoRecurso
from .recurso import ImplementoAcademico, ImplementoDeportivo, Libro, Recurso
from .reserva import Reserva
from .usuario import Usuario, UsuarioRol

__all__ = [
    # Enums
    "EstadoReserva",
    "EstadoRecurso",
    "Gestor",
    "Rol",
    "TipoRecurso",
    # Identidad y roles
    "Usuario",
    "UsuarioRol",
    # Catálogo
    "Recurso",
    "Libro",
    "ImplementoDeportivo",
    "ImplementoAcademico",
    # Reservas
    "Reserva",
]
