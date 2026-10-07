"""Modelos ORM de préstamos y garantías (RF3, issue #29)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .enums import EstadoPrestamo, ModalidadUso, TipoPrestamo


class Prestamo(Base):
    """Préstamo registrado para un recurso."""

    __tablename__ = "prestamo"
    __table_args__ = (
        CheckConstraint(
            "registrado_por_id <> prestatario_id",
            name="chk_registrador_distinto",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recurso_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recurso.id"), nullable=False
    )
    prestatario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuario.id"), nullable=False
    )
    registrado_por_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuario.id"), nullable=False
    )
    reserva_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("reserva.id"), nullable=True
    )
    fecha_entrega: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_limite: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    fecha_devolucion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    estado: Mapped[EstadoPrestamo] = mapped_column(
        Enum(EstadoPrestamo, name="estado_prestamo"),
        nullable=False,
        default=EstadoPrestamo.ACTIVO,
        server_default=text("'ACTIVO'"),
    )
    tipo_prestamo: Mapped[TipoPrestamo] = mapped_column(
        Enum(TipoPrestamo, name="tipo_prestamo"), nullable=False
    )
    modalidad_uso: Mapped[ModalidadUso] = mapped_column(
        Enum(ModalidadUso, name="modalidad_uso"), nullable=False
    )
    condicion_entrega: Mapped[str | None] = mapped_column(Text, nullable=True)
    condicion_devolucion: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Prestamo id={self.id} recurso_id={self.recurso_id} prestatario_id={self.prestatario_id}>"


class Garantia(Base):
    """Garantía asociada a un préstamo."""

    __tablename__ = "garantia"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prestamo_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("prestamo.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    tipo: Mapped[str] = mapped_column(String(60), nullable=False)
    valor: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0"),
        server_default=text("0"),
    )
    devuelta: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    def __repr__(self) -> str:
        return f"<Garantia id={self.id} prestamo_id={self.prestamo_id}>"
