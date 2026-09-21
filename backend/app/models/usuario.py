"""Identidad y roles: Usuario y su relación N–N con Rol.

Ver docs/01-sdd.md §3.3 (tablas `usuario` y `usuario_rol`).
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .enums import Rol


class UsuarioRol(Base):
    """Fila de la tabla puente usuario ↔ rol.

    `Rol` es una enumeración, no una entidad, así que la relación N–N se modela
    con esta tabla de dos columnas en vez de un `secondary`.
    """

    __tablename__ = "usuario_rol"

    usuario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuario.id", ondelete="CASCADE"), primary_key=True
    )
    rol: Mapped[Rol] = mapped_column(Enum(Rol, name="rol"), primary_key=True)

    usuario: Mapped["Usuario"] = relationship(back_populates="roles_rel")

    def __repr__(self) -> str:
        return f"<UsuarioRol usuario_id={self.usuario_id} rol={self.rol.value}>"


class Usuario(Base):
    """Persona que usa el sistema (estudiante, docente, custodio, ...)."""

    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nombres: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    # No está en el modelo de dominio; lo necesita el login JWT (issue #4).
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    roles_rel: Mapped[list[UsuarioRol]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", lazy="selectin"
    )

    #: Acceso directo a los roles como lista de `Rol`: `usuario.roles.append(Rol.DOCENTE)`.
    roles = association_proxy(
        "roles_rel", "rol", creator=lambda rol: UsuarioRol(rol=rol)
    )

    def tiene_rol(self, *roles: Rol) -> bool:
        """True si el usuario tiene al menos uno de los roles indicados."""
        return any(rol in self.roles for rol in roles)

    def __repr__(self) -> str:
        return f"<Usuario {self.codigo} {self.email}>"
