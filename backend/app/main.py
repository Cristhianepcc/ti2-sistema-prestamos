"""Punto de entrada de la API del Sistema de Préstamos."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db
from .routers import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Sistema de Préstamos — API",
    description="API REST del Sistema de Préstamos (EPCC · UNSA · TI2). Ver docs/01-sdd.md",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers por feature (se irán agregando: auth, recursos, reservas, ...)
app.include_router(health.router, prefix="/api")


@app.get("/")
def root():
    return {
        "name": "Sistema de Préstamos — API",
        "version": app.version,
        "docs": "/docs",
        "health": "/api/health",
    }
