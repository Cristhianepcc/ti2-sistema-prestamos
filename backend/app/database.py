"""Configuración de SQLAlchemy: engine, sesión y Base declarativa."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from .config import settings

engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def init_db() -> None:
    """Crea las tablas que falten a partir de los modelos.

    Sustituto simple de las migraciones mientras el esquema se estabiliza: no
    altera tablas ya existentes, así que un cambio de columna exige recrear la BD
    (`docker compose down -v`). Si el esquema se vuelve inestable, migrar a Alembic.
    """
    from . import models  # noqa: F401  — registra las tablas en Base.metadata

    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependencia FastAPI: entrega una sesión de BD y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
