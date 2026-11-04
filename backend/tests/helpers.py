from app.models import (
    EstadoRecurso,
    Gestor,
    ImplementoAcademico,
    ImplementoDeportivo,
    Libro,
    TipoRecurso,
    Usuario,
)


def crear_usuario(db, sufijo: str) -> Usuario:
    usuario = Usuario(
        codigo=f"TEST-{sufijo}",
        nombres=f"Usuario {sufijo}",
        email=f"{sufijo.lower()}@test.local",
        password_hash="test-hash",
    )
    db.add(usuario)
    db.commit()
    return usuario


def crear_recurso(db, tipo: TipoRecurso, sufijo: str, *, estado=EstadoRecurso.DISPONIBLE):
    clases = {
        TipoRecurso.LIBRO: (Libro, Gestor.CENTRO_ESTUDIANTES),
        TipoRecurso.DEPORTIVO: (ImplementoDeportivo, Gestor.CENTRO_ESTUDIANTES),
        TipoRecurso.ACADEMICO: (ImplementoAcademico, Gestor.INFRAESTRUCTURA),
    }
    clase, gestor = clases[tipo]
    recurso = clase(
        codigo=f"{tipo.value}-{sufijo}",
        nombre=f"Recurso {sufijo}",
        estado=estado,
        gestor=gestor,
        tipo_recurso=tipo,
    )
    db.add(recurso)
    db.commit()
    return recurso
