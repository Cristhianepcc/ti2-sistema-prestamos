"""Schemas para la gestión administrativa de usuarios y roles (RF7)."""

from pydantic import BaseModel, EmailStr, Field, field_validator

from ..models.enums import Rol


class UsuarioCreate(BaseModel):
    """Datos para crear una cuenta desde el panel administrativo."""

    codigo: str = Field(min_length=1, max_length=20)
    nombres: str = Field(min_length=1, max_length=120)
    email: EmailStr = Field(max_length=120)
    password: str = Field(min_length=1)
    roles: list[Rol] = Field(min_length=1)

    @field_validator("codigo", "nombres", mode="before")
    @classmethod
    def _recortar_texto(cls, value):
        if not isinstance(value, str):
            return value
        value = value.strip()
        if not value:
            raise ValueError("Este campo no puede estar vacío")
        return value

    @field_validator("email", mode="before")
    @classmethod
    def _normalizar_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("roles")
    @classmethod
    def _roles_sin_repetir(cls, value: list[Rol]) -> list[Rol]:
        if len(set(value)) != len(value):
            raise ValueError("No se puede asignar el mismo rol más de una vez")
        return value

    @field_validator("password")
    @classmethod
    def _limite_bcrypt(cls, value: str) -> str:
        # bcrypt solo procesa 72 bytes; evitar que contraseñas más largas se
        # conviertan silenciosamente en la misma contraseña al almacenarlas.
        try:
            longitud = len(value.encode("utf-8"))
        except UnicodeEncodeError as error:
            raise ValueError(
                "La contraseña debe contener texto UTF-8 válido"
            ) from error
        if longitud > 72:
            raise ValueError("La contraseña no puede superar 72 bytes UTF-8")
        return value


class UsuarioRolesUpdate(BaseModel):
    """Lista completa de roles que reemplazará los roles actuales."""

    roles: list[Rol] = Field(min_length=1)

    @field_validator("roles")
    @classmethod
    def _roles_sin_repetir(cls, value: list[Rol]) -> list[Rol]:
        if len(set(value)) != len(value):
            raise ValueError("No se puede asignar el mismo rol más de una vez")
        return value
