"""Entidades ORM (SQLAlchemy). Ver docs/01-sdd.md §3."""

from .enums import (
    EstadoSolicitud,
    EstadoPrestamo,
    EstadoReserva,
    EstadoRecurso,
    Gestor,
    ModalidadUso,
    Rol,
    TipoNotificacion,
    TipoPrestamo,
    TipoRecurso,
    TipoSolicitud,
)
from .recurso import ImplementoAcademico, ImplementoDeportivo, Libro, Recurso
from .reserva import Reserva
from .usuario import Usuario, UsuarioRol
from .prestamo import Garantia, Prestamo
from .solicitud import Solicitud
from .notificacion import Notificacion

__all__ = [
    # Enums
    "EstadoPrestamo",
    "EstadoReserva",
    "EstadoRecurso",
    "EstadoSolicitud",
    "Gestor",
    "ModalidadUso",
    "Rol",
    "TipoNotificacion",
    "TipoPrestamo",
    "TipoRecurso",
    "TipoSolicitud",
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
    # Solicitudes y notificaciones
    "Solicitud",
    "Notificacion",
]
