"""Modelo ORM de solicitudes (flujo solicitud → aceptación → notificación).

Desde el hallazgo #13 todo préstamo, incluido SIMPLE, nace de una Solicitud.
Ver docs/01-sdd.md §3.1/§3.3 y el Anexo RF3/RF4 de docs/02-contrato-api.md.
"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .enums import EstadoSolicitud, TipoSolicitud


class Solicitud(Base):
    """Pedido de un usuario para obtener un recurso."""

    __tablename__ = "solicitud"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    solicitante_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuario.id"), nullable=False
    )
    recurso_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recurso.id"), nullable=False
    )
    recurso: Mapped["Recurso"] = relationship()
    # NULL en SIMPLE; obligatorio en POR_CURSO/EXCEPCIONAL (lo valida el schema
    # y lo revalida solicitud_service).
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )
    # Desajuste #1 del issue: la columna se llama igual que la clave JSON del
    # contrato (`tipo_solicitud`), así no hace falta alias en el schema.
    tipo_solicitud: Mapped[TipoSolicitud] = mapped_column(
        Enum(TipoSolicitud, name="tipo_solicitud"), nullable=False
    )
    estado: Mapped[EstadoSolicitud] = mapped_column(
        Enum(EstadoSolicitud, name="estado_solicitud"),
        nullable=False,
        default=EstadoSolicitud.SOLICITADA,
        server_default=text("'SOLICITADA'"),
    )
    avalado_por_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuario.id"), nullable=True
    )
    autorizado_por_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuario.id"), nullable=True
    )
    aceptado_por_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuario.id"), nullable=True
    )
    motivo_rechazo: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Desajuste #2: `fecha` es el día; `created_at` lleva la hora y ordena la bandeja.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Desajuste #3: la FK vive solo en prestamo.solicitud_id; acá va el lado inverso.
    prestamo: Mapped["Prestamo | None"] = relationship(
        back_populates="solicitud", uselist=False
    )

    @property
    def prestamo_id(self) -> int | None:
        """Campo calculado que expone SolicitudPublica."""
        return self.prestamo.id if self.prestamo is not None else None

    def __repr__(self) -> str:
        return f"<Solicitud id={self.id} recurso_id={self.recurso_id} estado={self.estado}>"
