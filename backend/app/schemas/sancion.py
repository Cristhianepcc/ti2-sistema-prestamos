"""Schemas Pydantic para sanciones (RF5)."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.enums import Gestor, MotivoSancion, TipoRecurso


class SancionCreate(BaseModel):
    """Registro administrativo de una sanción sobre un préstamo existente."""

    prestamo_id: int
    motivo: MotivoSancion
    detalle: str = Field(min_length=3, max_length=1000)

    @field_validator("detalle")
    @classmethod
    def validar_detalle(cls, valor: str) -> str:
        valor = valor.strip()
        if len(valor) < 3:
            raise ValueError("El detalle debe tener al menos 3 caracteres útiles")
        return valor


class SancionResolucionCreate(BaseModel):
    """Datos de la reparación/reposición que cierra una sanción."""

    detalle: str = Field(min_length=3, max_length=1000)
    recurso_reposicion_id: int | None = None

    @field_validator("detalle")
    @classmethod
    def validar_detalle(cls, valor: str) -> str:
        valor = valor.strip()
        if len(valor) < 3:
            raise ValueError("El detalle debe tener al menos 3 caracteres útiles")
        return valor


class UsuarioSancionPublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombres: str


class RecursoSancionPublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    tipo_recurso: TipoRecurso
    gestor: Gestor


class PrestamoSancionPublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha_limite: datetime
    fecha_devolucion: datetime | None
    recurso: RecursoSancionPublico


class SancionEventoPublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: str
    detalle: str
    actor_usuario_id: int | None
    actor: UsuarioSancionPublico | None = None
    recurso_reposicion_id: int | None
    created_at: datetime
    recurso_reposicion: RecursoSancionPublico | None = None


class SancionPublica(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    usuario: UsuarioSancionPublico
    prestamo_id: int
    prestamo: PrestamoSancionPublico
    motivo: MotivoSancion
    inicio: datetime
    fin: datetime | None
    activa: bool
    monto: Decimal | None
    detalle: str | None
    eventos: list[SancionEventoPublico]
