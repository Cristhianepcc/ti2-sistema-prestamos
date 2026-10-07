"""Schemas Pydantic para reservas (RF2, issue #24)."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from ..models.enums import EstadoReserva


class ReservaCreate(BaseModel):
    """Datos que envía el cliente para solicitar una reserva."""

    recurso_id: int
    fecha: date
    franja: str = Field(min_length=1, max_length=30)


class ReservaPublica(BaseModel):
    """Representación pública de una reserva."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    recurso_id: int
    fecha: date
    franja: str
    estado: EstadoReserva
    prioridad: int
    created_at: datetime
