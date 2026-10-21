"""Schemas Pydantic para préstamos y garantías (RF3, issue #29)."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from ..models.enums import EstadoPrestamo, ModalidadUso, TipoPrestamo
from .recurso import RecursoPublico


class GarantiaCreate(BaseModel):
    """Datos de una garantía que acompaña al registro de un préstamo."""

    tipo: str = Field(min_length=1, max_length=60)
    valor: Decimal = Field(default=Decimal("0"), max_digits=10, decimal_places=2)


class GarantiaPublica(BaseModel):
    """Representación pública de una garantía."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    prestamo_id: int
    tipo: str
    valor: Decimal
    devuelta: bool


class PrestamoCreate(BaseModel):
    """Datos para registrar un préstamo."""

    recurso_id: int
    prestatario_id: int
    reserva_id: int | None = None
    # Opcional: el form del custodio (#33) no la pide. Si no llega,
    # prestamo_service (#30) la calcula según tipo_recurso/tipo_prestamo.
    fecha_limite: datetime | None = None
    tipo_prestamo: TipoPrestamo
    modalidad_uso: ModalidadUso
    condicion_entrega: str | None = None
    garantia: GarantiaCreate | None = None


class PrestamoPublico(BaseModel):
    """Representación pública de un préstamo."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    recurso_id: int
    recurso: RecursoPublico
    prestatario_id: int
    registrado_por_id: int
    reserva_id: int | None
    fecha_entrega: datetime
    fecha_limite: datetime
    fecha_devolucion: datetime | None
    estado: EstadoPrestamo
    tipo_prestamo: TipoPrestamo
    modalidad_uso: ModalidadUso
    condicion_entrega: str | None
    condicion_devolucion: str | None
    garantia: GarantiaPublica | None = None
