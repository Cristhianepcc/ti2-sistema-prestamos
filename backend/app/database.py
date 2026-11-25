"""Configuración de SQLAlchemy: engine, sesión, Base y migraciones idempotentes."""
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def _aplicar_migraciones() -> None:
    """Aplica una vez cada script SQL versionado en backend/migrations."""
    if engine.dialect.name != "postgresql":
        return

    with engine.begin() as conexion:
        conexion.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migration (
                    version VARCHAR(120) PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        )
        aplicadas = set(
            conexion.execute(text("SELECT version FROM schema_migration")).scalars()
        )

        for archivo in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if archivo.name in aplicadas:
                continue
            contenido = archivo.read_text(encoding="utf-8")
            for sentencia in contenido.split(";"):
                if sentencia.strip():
                    conexion.execute(text(sentencia))
            conexion.execute(
                text("INSERT INTO schema_migration (version) VALUES (:version)"),
                {"version": archivo.name},
            )


def init_db() -> None:
    """Crea tablas faltantes y aplica las migraciones pendientes."""
    from . import models  # noqa: F401 — registra las tablas en Base.metadata

    Base.metadata.create_all(bind=engine)
    _aplicar_migraciones()


def get_db():
    """Dependencia FastAPI: entrega una sesión de BD y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
