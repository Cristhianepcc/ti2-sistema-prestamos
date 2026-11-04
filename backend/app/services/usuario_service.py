"""Reglas de negocio para la gestión de usuarios y roles (RF7)."""

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import Rol, Usuario, UsuarioRol
from ..security import hash_password


class UsuarioDuplicado(Exception):
    """Ya existe una cuenta con ese código o correo."""


class UsuarioNoEncontrado(Exception):
    """No existe el usuario solicitado."""


class UltimoAdministrador(Exception):
    """No se puede quitar el último rol de administrador activo."""


def listar_usuarios(db: Session) -> list[Usuario]:
    """Lista usuarios de forma estable; el schema público excluye datos sensibles."""
    consulta = select(Usuario).order_by(Usuario.nombres.asc(), Usuario.id.asc())
    return list(db.scalars(consulta))


def crear_usuario(
    db: Session,
    *,
    codigo: str,
    nombres: str,
    email: str,
    password: str,
    roles: list[Rol],
) -> Usuario:
    """Crea una cuenta activa y guarda solamente el hash de su contraseña."""
    codigo = codigo.strip()
    nombres = nombres.strip()
    email = email.strip().lower()

    duplicado = db.scalar(
        select(Usuario.id).where(
            or_(
                Usuario.codigo == codigo,
                func.lower(Usuario.email) == email,
            )
        )
    )
    if duplicado is not None:
        raise UsuarioDuplicado("Ya existe un usuario con ese código o correo")

    usuario = Usuario(
        codigo=codigo,
        nombres=nombres,
        email=email,
        password_hash=hash_password(password),
        activo=True,
    )
    usuario.roles.extend(roles)
    db.add(usuario)

    try:
        db.commit()
        db.refresh(usuario)
    except IntegrityError as error:
        db.rollback()
        # La comprobación previa cubre el caso habitual; esto también evita un
        # 500 si dos administradores intentan crear el mismo código/correo a la vez.
        raise UsuarioDuplicado("Ya existe un usuario con ese código o correo") from error

    return usuario


def actualizar_roles(db: Session, *, usuario_id: int, roles: list[Rol]) -> Usuario:
    """Reemplaza la lista completa de roles de una cuenta existente."""
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise UsuarioNoEncontrado("Usuario no encontrado")

    roles_deseados = set(roles)
    roles_actuales = set(usuario.roles)
    if (
        usuario.activo
        and Rol.ADMINISTRADOR_SISTEMA in roles_actuales
        and Rol.ADMINISTRADOR_SISTEMA not in roles_deseados
    ):
        administradores_activos = db.scalar(
            select(func.count())
            .select_from(UsuarioRol)
            .join(Usuario, Usuario.id == UsuarioRol.usuario_id)
            .where(
                Usuario.activo.is_(True),
                UsuarioRol.rol == Rol.ADMINISTRADOR_SISTEMA,
            )
        )
        if administradores_activos <= 1:
            raise UltimoAdministrador(
                "No se puede quitar el rol del último administrador activo"
            )

    for rol in roles_actuales - roles_deseados:
        usuario.roles.remove(rol)
    for rol in roles:
        if rol not in roles_actuales:
            usuario.roles.append(rol)

    try:
        db.commit()
        db.refresh(usuario)
    except IntegrityError:
        db.rollback()
        raise

    return usuario
