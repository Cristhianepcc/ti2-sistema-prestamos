"""Schemas Pydantic de solicitudes (flujo solicitud → aceptación).

Las formas exactas están fijadas en docs/02-contrato-api.md → Anexo RF3/RF4;
si cambia algo acá, hay que actualizar ese documento porque el frontend
programa contra él.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator

from ..models.enums import EstadoSolicitud, ModalidadUso, TipoSolicitud
from .prestamo import GarantiaCreate
from .recurso import RecursoPublico


class SolicitudCreate(BaseModel):
    """Datos que envía el cliente para solicitar un recurso (POST /api/solicitudes)."""

    recurso_id: int
    # Obligatorio en el contrato: sin default, para que falte → 422.
    tipo_solicitud: TipoSolicitud
    motivo: str | None = None

    @model_validator(mode="after")
    def _motivo_obligatorio_si_no_es_simple(self):
        # Texto en blanco cuenta como ausente.
        self.motivo = (self.motivo or "").strip() or None
        if self.tipo_solicitud != TipoSolicitud.SIMPLE and self.motivo is None:
            raise ValueError(
                "El motivo es obligatorio en solicitudes POR_CURSO y EXCEPCIONAL"
            )
        return self


class SolicitudPublica(BaseModel):
    """Representación pública de una solicitud.

    Los campos son exactamente los del contrato. `fecha` y `motivo_rechazo`
    existen en la tabla pero no se exponen (el motivo de rechazo le llega al
    solicitante dentro del mensaje de la Notificacion).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    solicitante_id: int
    recurso_id: int
    recurso: RecursoPublico
    tipo_solicitud: TipoSolicitud
    motivo: str | None
    estado: EstadoSolicitud
    avalado_por_id: int | None
    autorizado_por_id: int | None
    aceptado_por_id: int | None
    # Campo calculado: Solicitud.prestamo_id (property sobre la relación inversa).
    prestamo_id: int | None
    created_at: datetime


class AceptarSolicitud(BaseModel):
    """Body de POST /api/solicitudes/{id}/aceptar.

    "Mismos campos que POST /api/prestamos, sin recurso_id, prestatario_id ni
    tipo_prestamo" (se toman de la solicitud). `modalidad_uso` es obligatorio,
    igual que en PrestamoCreate.
    """

    modalidad_uso: ModalidadUso
    reserva_id: int | None = None
    fecha_limite: datetime | None = None
    condicion_entrega: str | None = None
    garantia: GarantiaCreate | None = None


class RechazarSolicitud(BaseModel):
    """Body de POST /api/solicitudes/{id}/rechazar."""

    motivo_rechazo: str | None = None
