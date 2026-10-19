"""Modelo ORM de reservas (RF2)."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .enums import EstadoReserva


class Reserva(Base):
    """Reserva de un recurso por un usuario."""

    __tablename__ = "reserva"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuario.id"), nullable=False
    )
    recurso_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recurso.id"), nullable=False
    )
    recurso: Mapped["Recurso"] = relationship()
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    franja: Mapped[str] = mapped_column(String(30), nullable=False)
    estado: Mapped[EstadoReserva] = mapped_column(
        Enum(EstadoReserva, name="estado_reserva"),
        nullable=False,
        default=EstadoReserva.PENDIENTE,
        server_default=text("'PENDIENTE'"),
    )
    prioridad: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Reserva id={self.id} usuario_id={self.usuario_id} recurso_id={self.recurso_id}>"
