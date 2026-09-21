"""Esquemas Pydantic de autenticación (RF7).

Las formas exactas están fijadas en docs/02-contrato-api.md §2; si cambia algo acá,
hay que actualizar ese documento porque el frontend programa contra él.
"""
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from ..models.enums import Rol


class LoginRequest(BaseModel):
    """Credenciales del login. El identificador es el email, no el código."""

    email: EmailStr
    password: str = Field(min_length=1)


class UsuarioPublico(BaseModel):
    """Datos del usuario que sí se exponen en las respuestas.

    Deja fuera `password_hash` y `activo` a propósito.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombres: str
    email: EmailStr
    roles: list[Rol]

    @field_validator("roles", mode="before")
    @classmethod
    def _lista_de_roles(cls, v):
        """`Usuario.roles` es un association proxy, no una lista; se normaliza acá."""
        return list(v)


class TokenResponse(BaseModel):
    """Respuesta del login: el token y, de yapa, el usuario.

    Se incluye `user` para que el frontend sepa a qué pantalla redirigir sin tener
    que llamar a `/auth/me` justo después.
    """

    access_token: str
    token_type: str = "bearer"
    user: UsuarioPublico
