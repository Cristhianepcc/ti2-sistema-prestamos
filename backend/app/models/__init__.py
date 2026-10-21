"""Entidades ORM (SQLAlchemy). Ver docs/01-sdd.md §3."""

from .enums import (
    EstadoPrestamo,
    EstadoReserva,
    EstadoRecurso,
    Gestor,
    ModalidadUso,
    Rol,
    TipoPrestamo,
    TipoRecurso,
)
from .recurso import ImplementoAcademico, ImplementoDeportivo, Libro, Recurso
from .reserva import Reserva
from .usuario import Usuario, UsuarioRol
from .prestamo import Garantia, Prestamo

__all__ = [
    # Enums
    "EstadoPrestamo",
    "EstadoReserva",
    "EstadoRecurso",
    "Gestor",
    "ModalidadUso",
    "Rol",
    "TipoPrestamo",
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
    # Préstamos
    "Prestamo",
    "Garantia",
]
