"""Esquemas Pydantic del catalogo de recursos (RF1, issues #7 y #8).

Las formas exactas estan fijadas en docs/02-contrato-api.md Seccion 3; si
cambia algo aca, hay que actualizar ese documento porque el frontend
programa contra el.
"""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from ..models.enums import EstadoRecurso, Gestor, TipoRecurso


class _RecursoBase(BaseModel):
    """Campos comunes a cualquier recurso, sin importar el tipo."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    descripcion: str | None
    ubicacion: str | None
    estado: EstadoRecurso
    gestor: Gestor
    disponible: bool


class LibroPublico(_RecursoBase):
    tipo_recurso: Literal[TipoRecurso.LIBRO] = TipoRecurso.LIBRO
    isbn: str | None
    autor: str | None
    categoria: str | None


class ImplementoDeportivoPublico(_RecursoBase):
    tipo_recurso: Literal[TipoRecurso.DEPORTIVO] = TipoRecurso.DEPORTIVO
    tipo_deportivo: str | None


class ImplementoAcademicoPublico(_RecursoBase):
    tipo_recurso: Literal[TipoRecurso.ACADEMICO] = TipoRecurso.ACADEMICO
    codigo_patrimonial: str | None
    requiere_aval: bool | None


#: Union discriminado: Pydantic elige el sub-schema segun el valor real de
#: `tipo_recurso` del objeto ORM, asi un DEPORTIVO nunca serializa la clave
#: `autor` (ni siquiera en null), tal como exige el contrato.
RecursoPublico = Annotated[
    LibroPublico | ImplementoDeportivoPublico | ImplementoAcademicoPublico,
    Field(discriminator="tipo_recurso"),
]


class RecursoCreate(BaseModel):
    """Alta de un recurso (POST /api/recursos, issue #8, opcional).

    `gestor` no se acepta del cliente: el router lo deriva de
    `tipo_recurso` (LIBRO/DEPORTIVO -> CENTRO_ESTUDIANTES, ACADEMICO ->
    INFRAESTRUCTURA) para que sea imposible violar la constraint
    `chk_gestor_tipo` de la base de datos.
    """

    codigo: str = Field(min_length=1, max_length=30)
    nombre: str = Field(min_length=1, max_length=120)
    descripcion: str | None = None
    ubicacion: str | None = None
    estado: EstadoRecurso = EstadoRecurso.DISPONIBLE
    tipo_recurso: TipoRecurso

    isbn: str | None = None
    autor: str | None = None
    categoria: str | None = None
    tipo_deportivo: str | None = None
    codigo_patrimonial: str | None = None
    requiere_aval: bool | None = None
