"""Endpoints del catalogo de recursos (RF1, issues #7 y #8).

Contrato: docs/02-contrato-api.md Seccion 3.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ImplementoAcademico, ImplementoDeportivo, Libro, Recurso
from ..models.enums import EstadoRecurso, Gestor, Rol, TipoRecurso
from ..schemas.recurso import RecursoCreate, RecursoPublico
from ..security import UsuarioActual, require_role

router = APIRouter(prefix="/recursos", tags=["recursos"])

#: Que gestor le corresponde a cada tipo (misma regla que la constraint
#: `chk_gestor_tipo` de la base de datos).
_GESTOR_POR_TIPO = {
    TipoRecurso.LIBRO: Gestor.CENTRO_ESTUDIANTES,
    TipoRecurso.DEPORTIVO: Gestor.CENTRO_ESTUDIANTES,
    TipoRecurso.ACADEMICO: Gestor.INFRAESTRUCTURA,
}


@router.get("", response_model=list[RecursoPublico])
def listar_recursos(
    usuario: UsuarioActual,
    db: Annotated[Session, Depends(get_db)],
    tipo: TipoRecurso | None = None,
    estado: EstadoRecurso | None = None,
    disponible: bool | None = None,
    q: Annotated[str | None, Query(min_length=1)] = None,
) -> list[Recurso]:
    """Catalogo de recursos (RF1). Requiere estar autenticado, cualquier rol."""
    stmt = select(Recurso)

    if tipo is not None:
        stmt = stmt.where(Recurso.tipo_recurso == tipo)

    # `estado` explicito gana sobre `disponible`, tal como dice el contrato.
    if estado is not None:
        stmt = stmt.where(Recurso.estado == estado)
    elif disponible is not None:
        if disponible:
            stmt = stmt.where(Recurso.estado == EstadoRecurso.DISPONIBLE)
        else:
            stmt = stmt.where(Recurso.estado != EstadoRecurso.DISPONIBLE)

    if q:
        patron = f"%{q}%"
        stmt = stmt.where(or_(Recurso.nombre.ilike(patron), Recurso.codigo.ilike(patron)))

    return list(db.scalars(stmt))


@router.post(
    "",
    response_model=RecursoPublico,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(Rol.CUSTODIO_CE, Rol.CUSTODIO_INFRA))],
)
def crear_recurso(
    datos: RecursoCreate,
    usuario: UsuarioActual,
    db: Annotated[Session, Depends(get_db)],
) -> Recurso:
    """Alta de un recurso (issue #8, opcional).

    El custodio del CE solo da de alta libros/deportivos; el de
    Infraestructura, solo academicos.
    """
    gestor = _GESTOR_POR_TIPO[datos.tipo_recurso]

    if gestor is Gestor.CENTRO_ESTUDIANTES and not usuario.tiene_rol(Rol.CUSTODIO_CE):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo un custodio del Centro de Estudiantes puede dar de alta este tipo de recurso",
        )
    if gestor is Gestor.INFRAESTRUCTURA and not usuario.tiene_rol(Rol.CUSTODIO_INFRA):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo un custodio de Infraestructura puede dar de alta este tipo de recurso",
        )

    campos_comunes = dict(
        codigo=datos.codigo,
        nombre=datos.nombre,
        descripcion=datos.descripcion,
        ubicacion=datos.ubicacion,
        estado=datos.estado,
        gestor=gestor,
    )

    if datos.tipo_recurso is TipoRecurso.LIBRO:
        recurso = Libro(**campos_comunes, isbn=datos.isbn, autor=datos.autor, categoria=datos.categoria)
    elif datos.tipo_recurso is TipoRecurso.DEPORTIVO:
        recurso = ImplementoDeportivo(**campos_comunes, tipo_deportivo=datos.tipo_deportivo)
    else:
        recurso = ImplementoAcademico(
            **campos_comunes,
            codigo_patrimonial=datos.codigo_patrimonial,
            requiere_aval=datos.requiere_aval,
        )

    db.add(recurso)
    db.commit()
    db.refresh(recurso)
    return recurso
