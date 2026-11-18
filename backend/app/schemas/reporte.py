"""Esquemas Pydantic de Historial y Reportes (RF6, nivel 1).

Formas fijadas en docs/02-contrato-api.md, Anexo RF6; si algo cambia acá, hay
que actualizar ese documento porque el frontend programa contra él.

A diferencia de otros schemas, `reporte_service` construye directamente estos
objetos como diccionarios (no son espejo 1:1 de una fila de BD), así que no
necesitan `model_config = ConfigDict(from_attributes=True)`.
"""
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from ..models.enums import (
    EstadoPrestamo,
    EstadoRecurso,
    Gestor,
    ModalidadUso,
    TipoPrestamo,
    TipoRecurso,
)


class RecursoHistorial(BaseModel):
    """Recurso reducido que acompaña cada ítem del historial."""

    id: int
    codigo: str
    nombre: str
    tipo_recurso: TipoRecurso


class HistorialItem(BaseModel):
    prestamo_id: int
    recurso: RecursoHistorial
    tipo_prestamo: TipoPrestamo
    modalidad_uso: ModalidadUso
    estado: EstadoPrestamo
    fecha_entrega: datetime
    fecha_limite: datetime
    fecha_devolucion: datetime | None
    dias_atraso: int


class HistorialResponse(BaseModel):
    total: int
    limite: int
    offset: int
    items: list[HistorialItem]


class ReporteInventario(BaseModel):
    total_recursos: int
    por_tipo: dict[TipoRecurso, int]
    por_estado: dict[EstadoRecurso, int]
    por_gestor: dict[Gestor, int]
    tipo_por_estado: dict[TipoRecurso, dict[EstadoRecurso, int]]


class PeriodoReporte(BaseModel):
    desde: date | None
    hasta: date | None


class RecursoMasPrestado(BaseModel):
    recurso_id: int
    codigo: str
    nombre: str
    total: int


class GarantiasResumen(BaseModel):
    retenidas: int
    valor_retenido: Decimal


class RecursoAtraso(BaseModel):
    """Recurso reducido que acompaña cada ítem de `atrasados`."""

    id: int
    codigo: str
    nombre: str


class PrestatarioAtraso(BaseModel):
    """Datos personales mínimos del prestatario (sin email ni roles)."""

    id: int
    codigo: str
    nombres: str


class PrestamoAtrasado(BaseModel):
    prestamo_id: int
    recurso: RecursoAtraso
    prestatario: PrestatarioAtraso
    fecha_limite: datetime
    dias_atraso: int


class AtrasadosResumen(BaseModel):
    total: int
    items: list[PrestamoAtrasado]


class ReportePrestamos(BaseModel):
    periodo: PeriodoReporte
    total_prestamos: int
    por_estado: dict[EstadoPrestamo, int]
    por_tipo: dict[TipoPrestamo, int]
    por_modalidad: dict[ModalidadUso, int]
    mas_prestados: list[RecursoMasPrestado]
    garantias: GarantiasResumen
    atrasados: AtrasadosResumen


class ReporteResumen(BaseModel):
    prestamos_activos: int
    prestamos_atrasados: int
