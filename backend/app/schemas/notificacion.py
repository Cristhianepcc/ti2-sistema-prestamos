"""Schemas Pydantic de notificaciones (Anexo — Notificaciones del contrato)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from ..models.enums import TipoNotificacion


class NotificacionPublica(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    solicitud_id: int
    tipo: TipoNotificacion
    mensaje: str
    leida: bool
    created_at: datetime


class NotificacionUpdate(BaseModel):
    """PATCH de una notificación: `{ "leida": true }`."""

    leida: bool
