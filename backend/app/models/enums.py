"""Enumeraciones del dominio (se mapean a tipos ENUM de PostgreSQL).

Fuente de verdad: docs/00-contexto-alcance-propuesta.md §4 y docs/01-sdd.md §3.1.
Aquí solo están las del issue #2 (identidad y catálogo); las de reservas, préstamos
y sanciones se agregan con sus modelos.
"""
import enum


class Rol(str, enum.Enum):
    """Roles del sistema. Un usuario puede tener varios a la vez."""

    ESTUDIANTE = "ESTUDIANTE"
    DOCENTE = "DOCENTE"
    CUSTODIO_CE = "CUSTODIO_CE"
    CUSTODIO_INFRA = "CUSTODIO_INFRA"
    DIRECCION_ESCUELA = "DIRECCION_ESCUELA"
    ADMINISTRADOR_SISTEMA = "ADMINISTRADOR_SISTEMA"


class Gestor(str, enum.Enum):
    """Quién administra el recurso."""

    CENTRO_ESTUDIANTES = "CENTRO_ESTUDIANTES"
    INFRAESTRUCTURA = "INFRAESTRUCTURA"


class TipoRecurso(str, enum.Enum):
    """Discriminador de la herencia de Recurso (tabla única)."""

    LIBRO = "LIBRO"
    DEPORTIVO = "DEPORTIVO"
    ACADEMICO = "ACADEMICO"


class EstadoRecurso(str, enum.Enum):
    """Disponibilidad del recurso en el catálogo."""

    DISPONIBLE = "DISPONIBLE"
    RESERVADO = "RESERVADO"
    PRESTADO = "PRESTADO"
    MANTENIMIENTO = "MANTENIMIENTO"
