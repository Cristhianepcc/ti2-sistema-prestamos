"""Entidades ORM (SQLAlchemy). Ver docs/01-sdd.md §3.

Importar los módulos aquí es lo que registra las tablas en `Base.metadata`,
así que cualquier modelo nuevo (reserva, préstamo, sanción, ...) debe añadirse
a este archivo además de a su propio módulo.
"""
from .enums import EstadoRecurso, Gestor, Rol, TipoRecurso
from .recurso import ImplementoAcademico, ImplementoDeportivo, Libro, Recurso
from .usuario import Usuario, UsuarioRol

__all__ = [
    # Enums
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
]
