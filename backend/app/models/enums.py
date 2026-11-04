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


class EstadoReserva(str, enum.Enum):
    """Estados del ciclo de vida de una reserva."""

    PENDIENTE = "PENDIENTE"
    CONFIRMADA = "CONFIRMADA"
    CANCELADA = "CANCELADA"
    VENCIDA = "VENCIDA"


class EstadoPrestamo(str, enum.Enum):
    """Estados del ciclo de vida de un préstamo."""

    ACTIVO = "ACTIVO"
    DEVUELTO = "DEVUELTO"
    ATRASADO = "ATRASADO"


class TipoPrestamo(str, enum.Enum):
    """Tipos de préstamo permitidos."""

    SIMPLE = "SIMPLE"
    POR_CURSO = "POR_CURSO"
    EXCEPCIONAL = "EXCEPCIONAL"


class ModalidadUso(str, enum.Enum):
    """Modalidad de uso del recurso prestado."""

    EN_SITIO = "EN_SITIO"
    RETIRO_TEMPORAL = "RETIRO_TEMPORAL"

class TipoSolicitud(str, enum.Enum):
    """Tipo de solicitud. Mismos valores que TipoPrestamo: el tipo de la
    solicitud es el tipo del préstamo que habilita."""
 
    SIMPLE = "SIMPLE"
    POR_CURSO = "POR_CURSO"
    EXCEPCIONAL = "EXCEPCIONAL"

class EstadoSolicitud(str, enum.Enum):
    """Ciclo de vida de una solicitud (flujo solicitud → aceptación)."""
 
    SOLICITADA = "SOLICITADA"
    AVALADA = "AVALADA"
    AUTORIZADA = "AUTORIZADA"
    ACEPTADA = "ACEPTADA"
    RECHAZADA = "RECHAZADA"

class TipoNotificacion(str, enum.Enum):
    """Qué evento originó la notificación al solicitante."""
 
    SOLICITUD_ACEPTADA = "SOLICITUD_ACEPTADA"
    SOLICITUD_RECHAZADA = "SOLICITUD_RECHAZADA"
