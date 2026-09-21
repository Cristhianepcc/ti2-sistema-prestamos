"""Catálogo de recursos: Recurso (base) y sus tres especializaciones.

La herencia se resuelve con **tabla única + discriminador** (`tipo_recurso`),
según docs/01-sdd.md §3. Las columnas propias de cada subtipo viven en la misma
tabla y quedan en NULL para los demás.
"""
from sqlalchemy import Boolean, CheckConstraint, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .enums import EstadoRecurso, Gestor, TipoRecurso


class Recurso(Base):
    """Recurso prestable. Clase base: no se instancia directamente."""

    __tablename__ = "recurso"
    __table_args__ = (
        # Un recurso académico lo gestiona Infraestructura; libros y deportivos, el CE.
        CheckConstraint(
            "(tipo_recurso = 'ACADEMICO' AND gestor = 'INFRAESTRUCTURA')"
            " OR (tipo_recurso IN ('LIBRO', 'DEPORTIVO') AND gestor = 'CENTRO_ESTUDIANTES')",
            name="chk_gestor_tipo",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    ubicacion: Mapped[str | None] = mapped_column(String(120))
    estado: Mapped[EstadoRecurso] = mapped_column(
        Enum(EstadoRecurso, name="estado_recurso"),
        nullable=False,
        default=EstadoRecurso.DISPONIBLE,
    )
    gestor: Mapped[Gestor] = mapped_column(Enum(Gestor, name="gestor"), nullable=False)
    tipo_recurso: Mapped[TipoRecurso] = mapped_column(
        Enum(TipoRecurso, name="tipo_recurso"), nullable=False
    )

    __mapper_args__ = {
        "polymorphic_on": tipo_recurso,
        "polymorphic_abstract": True,
    }

    @property
    def disponible(self) -> bool:
        """Atajo para el catálogo (RF1): si se puede prestar ahora mismo."""
        return self.estado == EstadoRecurso.DISPONIBLE

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.codigo} {self.nombre}>"


class Libro(Recurso):
    """Libro gestionado por el Centro de Estudiantes."""

    isbn: Mapped[str | None] = mapped_column(String(20))
    autor: Mapped[str | None] = mapped_column(String(120))
    categoria: Mapped[str | None] = mapped_column(String(60))

    __mapper_args__ = {"polymorphic_identity": TipoRecurso.LIBRO}


class ImplementoDeportivo(Recurso):
    """Implemento deportivo gestionado por el Centro de Estudiantes."""

    # `tipo` en el dominio; se renombra para no chocar con `tipo_recurso`.
    tipo_deportivo: Mapped[str | None] = mapped_column(String(60))

    __mapper_args__ = {"polymorphic_identity": TipoRecurso.DEPORTIVO}


class ImplementoAcademico(Recurso):
    """Implemento académico gestionado por Infraestructura.

    Es el único tipo que admite préstamos POR_CURSO y EXCEPCIONAL.
    """

    codigo_patrimonial: Mapped[str | None] = mapped_column(String(60))
    requiere_aval: Mapped[bool | None] = mapped_column(Boolean)

    __mapper_args__ = {"polymorphic_identity": TipoRecurso.ACADEMICO}
