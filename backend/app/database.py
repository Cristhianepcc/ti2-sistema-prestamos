"""Configuración de SQLAlchemy: engine, sesión, Base y migraciones idempotentes."""
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def _tiene_rol_direccion_escuela(conexion) -> bool:
    """Detecta el valor legado antes de ejecutar la migración que lo elimina."""
    resultado = conexion.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM pg_enum AS etiqueta
                JOIN pg_type AS tipo ON tipo.oid = etiqueta.enumtypid
                WHERE tipo.typname = 'rol'
                  AND etiqueta.enumlabel = 'DIRECCION_ESCUELA'
            )
            """
        )
    )
    return bool(resultado.scalar_one())


def _aplicar_migraciones() -> None:
    """Aplica scripts pendientes; omite limpieza histórica si no hay datos legados."""
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

            # Este script solo aplica a bases antiguas que todavía tienen el rol retirado.
            tiene_rol_legacy = archivo.name == "001_fusionar_direccion_en_administrador.sql"
            if tiene_rol_legacy and not _tiene_rol_direccion_escuela(conexion):
                conexion.execute(
                    text("INSERT INTO schema_migration (version) VALUES (:version)"),
                    {"version": archivo.name},
                )
                continue

            contenido = archivo.read_text(encoding="utf-8")
            contenido_sql = "\n".join(
                linea.split("--", 1)[0] for linea in contenido.splitlines()
            )
            for sentencia in contenido_sql.split(";"):
                # Las migraciones se ejecutan dentro de engine.begin(); ignora wrappers
                # BEGIN/COMMIT heredados para conservar una única transacción.
                sin_comentarios = sentencia.strip()
                if sin_comentarios.upper() in {
                    "BEGIN",
                    "BEGIN TRANSACTION",
                    "COMMIT",
                    "END",
                }:
                    continue
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
