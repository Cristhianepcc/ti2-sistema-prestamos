"""Modelos de sanciones y su historial de eventos (RF5)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .enums import MotivoSancion
from .recurso import Recurso


class Sancion(Base):
    """Una sanción por causa y préstamo; un préstamo puede generar varias."""

    __tablename__ = "sancion"
    __table_args__ = (
        UniqueConstraint("prestamo_id", "motivo", name="uq_sancion_prestamo_motivo"),
        CheckConstraint("monto IS NULL OR monto >= 0", name="chk_sancion_monto_no_negativo"),
        Index("ix_sancion_usuario_activa", "usuario_id", "activa"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuario.id"), nullable=False, index=True
    )
    prestamo_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("prestamo.id"), nullable=False
    )
    motivo: Mapped[MotivoSancion] = mapped_column(
        Enum(MotivoSancion, name="motivo_sancion"), nullable=False
    )
    inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activa: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")
    # La regla económica sigue pendiente. NULL significa que no se ha fijado
    # una multa; el sistema no inventa ni calcula montos.
    monto: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    detalle: Mapped[str | None] = mapped_column(Text, nullable=True)

    usuario: Mapped["Usuario"] = relationship(foreign_keys=[usuario_id])
    prestamo: Mapped["Prestamo"] = relationship()
    eventos: Mapped[list["SancionEvento"]] = relationship(
        back_populates="sancion",
        cascade="all, delete-orphan",
        order_by="SancionEvento.created_at, SancionEvento.id",
    )

    def __repr__(self) -> str:
        return f"<Sancion id={self.id} prestamo_id={self.prestamo_id} motivo={self.motivo}>"


class SancionEvento(Base):
    """Registro inmutable de la creación, vencimiento o resolución."""

    __tablename__ = "sancion_evento"
    __table_args__ = (
        UniqueConstraint(
            "recurso_reposicion_id", name="uq_sancion_evento_recurso_reposicion"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sancion_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sancion.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    detalle: Mapped[str] = mapped_column(Text, nullable=False)
    actor_usuario_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuario.id"), nullable=True
    )
    recurso_reposicion_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("recurso.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    sancion: Mapped[Sancion] = relationship(back_populates="eventos")
    actor: Mapped["Usuario | None"] = relationship(foreign_keys=[actor_usuario_id])
    recurso_reposicion: Mapped["Recurso | None"] = relationship(
        foreign_keys=[recurso_reposicion_id]
    )

    def __repr__(self) -> str:
        return f"<SancionEvento id={self.id} sancion_id={self.sancion_id} tipo={self.tipo}>"
