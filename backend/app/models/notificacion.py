"""Modelo ORM de notificaciones dentro de la plataforma (sin correo ni push)."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .enums import TipoNotificacion


class Notificacion(Base):
    """Aviso al solicitante cuando su solicitud se acepta o se rechaza."""

    __tablename__ = "notificacion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # El solicitante, destinatario de la notificación.
    usuario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuario.id"), nullable=False
    )
    solicitud_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("solicitud.id"), nullable=False
    )
    tipo: Mapped[TipoNotificacion] = mapped_column(
        Enum(TipoNotificacion, name="tipo_notificacion"), nullable=False
    )
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    leida: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Notificacion id={self.id} usuario_id={self.usuario_id} tipo={self.tipo}>"
