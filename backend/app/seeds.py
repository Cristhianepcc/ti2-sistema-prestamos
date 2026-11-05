"""Carga de datos de ejemplo para la demo (issue #3).

Crea un usuario por cada rol y un catálogo variado (libros, implementos deportivos
y académicos) en distintos estados, para que el frontend tenga qué mostrar.

Es **idempotente**: se puede correr las veces que haga falta, porque solo inserta
lo que falta (compara por `codigo`/`email`). No actualiza lo ya existente.

Uso:
    python -m app.seeds            # inserta lo que falte
    python -m app.seeds --reset    # borra usuarios y recursos, y vuelve a insertar

Con Docker:
    docker compose exec api python -m app.seeds
"""
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import SessionLocal, init_db
from .models import (
    EstadoSolicitud,
    EstadoRecurso,
    EstadoReserva,
    Garantia,
    Gestor,
    ImplementoAcademico,
    ImplementoDeportivo,
    Libro,
    ModalidadUso,
    Prestamo,
    Recurso,
    Reserva,
    Rol,
    TipoNotificacion,
    TipoSolicitud,
    Solicitud,
    Notificacion,
    Usuario,
    UsuarioRol,
)
from .security import hash_password
from .services.solicitud_service import aceptar_solicitud, crear_solicitud

#: Contraseña de todos los usuarios de ejemplo. Solo para desarrollo y la demo.
PASSWORD_DEMO = "prestamos123"

#: Un usuario por rol (el último tiene dos, para probar la relación N–N y las
#: dependencias de rol del issue #4).
USUARIOS = [
    ("20200001", "Diego Ramírez Cusi", "diego@unsa.edu.pe", [Rol.ESTUDIANTE]),
    ("20200002", "Lucía Mamani Torres", "lucia@unsa.edu.pe", [Rol.DOCENTE]),
    ("20200003", "Pedro Huamán Salas", "pedro@unsa.edu.pe", [Rol.CUSTODIO_CE]),
    ("20200004", "Rosa Ccama Apaza", "rosa@unsa.edu.pe", [Rol.CUSTODIO_INFRA]),
    ("20200005", "Elena Vargas Pinto", "elena@unsa.edu.pe", [Rol.DIRECCION_ESCUELA]),
    ("20200006", "Iván Choque Flores", "ivan@unsa.edu.pe", [Rol.ADMINISTRADOR_SISTEMA]),
    ("20200007", "Marta Quispe León", "marta@unsa.edu.pe", [Rol.DOCENTE, Rol.CUSTODIO_CE]),
]


def _recursos() -> list[Recurso]:
    """Catálogo de ejemplo.

    Los estados están variados a propósito para que la pantalla de catálogo (#10)
    muestre los cuatro casos y no solo DISPONIBLE.
    """
    return [
        # Libros — Centro de Estudiantes
        Libro(
            codigo="LIB-001", nombre="Clean Code",
            descripcion="Manual de estilo y buenas prácticas de programación",
            ubicacion="Estante B-2", gestor=Gestor.CENTRO_ESTUDIANTES,
            estado=EstadoRecurso.DISPONIBLE,
            isbn="9780132350884", autor="Robert C. Martin", categoria="Software",
        ),
        Libro(
            codigo="LIB-002", nombre="Introduction to Algorithms",
            descripcion="Algoritmos y estructuras de datos (CLRS)",
            ubicacion="Estante B-3", gestor=Gestor.CENTRO_ESTUDIANTES,
            estado=EstadoRecurso.DISPONIBLE,
            isbn="9780262046305", autor="Thomas H. Cormen", categoria="Algoritmos",
        ),
        Libro(
            codigo="LIB-003", nombre="Ingeniería de Software",
            descripcion="Texto base del curso de Ingeniería de Software",
            ubicacion="Estante A-1", gestor=Gestor.CENTRO_ESTUDIANTES,
            estado=EstadoRecurso.DISPONIBLE,
            isbn="9786073238885", autor="Ian Sommerville", categoria="Ingeniería",
        ),
        Libro(
            codigo="LIB-004", nombre="Fundamentos de Bases de Datos",
            descripcion="Modelo relacional, SQL y diseño de esquemas",
            ubicacion="Estante A-4", gestor=Gestor.CENTRO_ESTUDIANTES,
            estado=EstadoRecurso.DISPONIBLE,
            isbn="9788448190330", autor="Abraham Silberschatz", categoria="Bases de datos",
        ),
        # Implementos deportivos — Centro de Estudiantes
        ImplementoDeportivo(
            codigo="DEP-001", nombre="Balón de fútbol",
            descripcion="Balón n.º 5 para cancha de grass sintético",
            ubicacion="Depósito CE", gestor=Gestor.CENTRO_ESTUDIANTES,
            estado=EstadoRecurso.DISPONIBLE, tipo_deportivo="Fútbol",
        ),
        ImplementoDeportivo(
            codigo="DEP-002", nombre="Balón de vóley",
            descripcion="Balón oficial de vóley",
            ubicacion="Depósito CE", gestor=Gestor.CENTRO_ESTUDIANTES,
            estado=EstadoRecurso.DISPONIBLE, tipo_deportivo="Vóley",
        ),
        ImplementoDeportivo(
            codigo="DEP-003", nombre="Juego de ajedrez",
            descripcion="Tablero y piezas completas",
            ubicacion="Sala de estudiantes", gestor=Gestor.CENTRO_ESTUDIANTES,
            estado=EstadoRecurso.MANTENIMIENTO, tipo_deportivo="Ajedrez",
        ),
        # Implementos académicos — Infraestructura
        ImplementoAcademico(
            codigo="ACA-001", nombre="Proyector Epson X05",
            descripcion="Proyector portátil con cable HDMI",
            ubicacion="Oficina de Infraestructura", gestor=Gestor.INFRAESTRUCTURA,
            estado=EstadoRecurso.DISPONIBLE,
            codigo_patrimonial="PAT-9981", requiere_aval=True,
        ),
        ImplementoAcademico(
            codigo="ACA-002", nombre="Laptop Lenovo ThinkPad",
            descripcion="Laptop para laboratorio, uso en sitio",
            ubicacion="Laboratorio 2", gestor=Gestor.INFRAESTRUCTURA,
            estado=EstadoRecurso.DISPONIBLE,
            codigo_patrimonial="PAT-1042", requiere_aval=True,
        ),
        ImplementoAcademico(
            codigo="ACA-003", nombre="Kit Arduino UNO",
            descripcion="Placa, sensores y protoboard para prácticas",
            ubicacion="Laboratorio 1", gestor=Gestor.INFRAESTRUCTURA,
            estado=EstadoRecurso.DISPONIBLE,
            codigo_patrimonial="PAT-2210", requiere_aval=False,
        ),
    ]


def _sembrar_usuarios(db: Session) -> int:
    existentes = set(db.scalars(select(Usuario.email)))
    nuevos = 0
    for codigo, nombres, email, roles in USUARIOS:
        if email in existentes:
            continue
        usuario = Usuario(
            codigo=codigo, nombres=nombres, email=email,
            password_hash=hash_password(PASSWORD_DEMO),
        )
        for rol in roles:
            usuario.roles.append(rol)
        db.add(usuario)
        nuevos += 1
    return nuevos


def _sembrar_recursos(db: Session) -> int:
    existentes = set(db.scalars(select(Recurso.codigo)))
    nuevos = 0
    for recurso in _recursos():
        if recurso.codigo in existentes:
            continue
        db.add(recurso)
        nuevos += 1
    return nuevos


def _sembrar_solicitudes(db: Session) -> int:
    """Inserta ejemplos para la bandeja de aprobación y notificaciones."""
    solicitante = db.scalar(select(Usuario).where(Usuario.email == "diego@unsa.edu.pe"))
    docente = db.scalar(select(Usuario).where(Usuario.email == "lucia@unsa.edu.pe"))
    if solicitante is None:
        return 0

    ejemplos = (
        ("LIB-001", TipoSolicitud.SIMPLE, None, EstadoSolicitud.SOLICITADA, None),
        (
            "ACA-003",
            TipoSolicitud.POR_CURSO,
            "Práctica del curso de Arquitectura de Computadores",
            EstadoSolicitud.AVALADA,
            docente.id if docente else None,
        ),
        ("DEP-001", TipoSolicitud.SIMPLE, None, EstadoSolicitud.RECHAZADA, None),
    )
    nuevos = 0
    for codigo, tipo, motivo, estado, avalado_por_id in ejemplos:
        recurso = db.scalar(select(Recurso).where(Recurso.codigo == codigo))
        if recurso is None:
            continue
        existente = db.scalar(
            select(Solicitud.id)
            .where(
                Solicitud.solicitante_id == solicitante.id,
                Solicitud.recurso_id == recurso.id,
                Solicitud.tipo_solicitud == tipo,
            )
            .limit(1)
        )
        if existente is not None:
            continue

        motivo_rechazo = (
            "El recurso no está disponible para la fecha solicitada."
            if estado == EstadoSolicitud.RECHAZADA
            else None
        )
        solicitud = Solicitud(
            solicitante_id=solicitante.id,
            recurso_id=recurso.id,
            tipo_solicitud=tipo,
            motivo=motivo,
            estado=estado,
            avalado_por_id=avalado_por_id,
            motivo_rechazo=motivo_rechazo,
        )
        db.add(solicitud)
        db.flush()
        if estado == EstadoSolicitud.RECHAZADA:
            db.add(
                Notificacion(
                    usuario_id=solicitante.id,
                    solicitud_id=solicitud.id,
                    tipo=TipoNotificacion.SOLICITUD_RECHAZADA,
                    mensaje=(
                        f'Tu solicitud de "{recurso.nombre}" fue rechazada. '
                        f"Motivo: {motivo_rechazo}"
                    ),
                )
            )
        nuevos += 1
    return nuevos


def _sembrar_prestamos(db: Session) -> int:
    """Crea préstamos aceptando solicitudes, sin estados PRESTADO ficticios."""
    solicitante = db.scalar(select(Usuario).where(Usuario.email == "diego@unsa.edu.pe"))
    custodio = db.scalar(select(Usuario).where(Usuario.email == "pedro@unsa.edu.pe"))
    if solicitante is None or custodio is None:
        return 0

    ejemplos = (
        ("LIB-002", ModalidadUso.RETIRO_TEMPORAL, 2),
        ("DEP-002", ModalidadUso.EN_SITIO, 1),
    )
    nuevos = 0
    for codigo, modalidad, dias in ejemplos:
        recurso = db.scalar(select(Recurso).where(Recurso.codigo == codigo))
        if recurso is None:
            continue
        existe = db.scalar(
            select(Prestamo.id)
            .where(Prestamo.recurso_id == recurso.id)
            .limit(1)
        )
        if existe is not None:
            continue

        solicitud = db.scalar(
            select(Solicitud).where(
                Solicitud.solicitante_id == solicitante.id,
                Solicitud.recurso_id == recurso.id,
                Solicitud.tipo_solicitud == TipoSolicitud.SIMPLE,
            )
        )
        if solicitud is None:
            solicitud = crear_solicitud(
                db,
                solicitante_id=solicitante.id,
                recurso_id=recurso.id,
                tipo_solicitud=TipoSolicitud.SIMPLE,
            )
        if solicitud.estado != EstadoSolicitud.SOLICITADA:
            continue
        aceptar_solicitud(
            db,
            solicitud_id=solicitud.id,
            custodio_id=custodio.id,
            modalidad_uso=modalidad,
            fecha_limite=datetime.now(timezone.utc) + timedelta(days=dias),
            condicion_entrega="Buen estado",
        )
        nuevos += 1
    return nuevos


def _sembrar_reserva(db: Session) -> int:
    """Crea una reserva futura para un recurso con préstamo activo."""
    usuario = db.scalar(select(Usuario).where(Usuario.email == "diego@unsa.edu.pe"))
    recurso = db.scalar(select(Recurso).where(Recurso.codigo == "LIB-002"))
    if usuario is None or recurso is None:
        return 0
    existe = db.scalar(
        select(Reserva.id)
        .where(Reserva.usuario_id == usuario.id, Reserva.recurso_id == recurso.id)
        .limit(1)
    )
    if existe is not None:
        return 0

    fecha = datetime.now(ZoneInfo("America/Lima")).date() + timedelta(days=3)
    db.add(
        Reserva(
            usuario_id=usuario.id,
            recurso_id=recurso.id,
            fecha=fecha,
            franja="10:00-12:00",
            estado=EstadoReserva.PENDIENTE,
        )
    )
    return 1


def _reset(db: Session) -> None:
    """Borra usuarios y recursos (y lo que dependa de ellos: reservas y préstamos)."""
    db.query(Garantia).delete()
    db.query(Notificacion).delete()
    db.query(Solicitud).delete()
    db.query(Prestamo).delete()
    db.query(Reserva).delete()
    db.query(UsuarioRol).delete()
    db.query(Usuario).delete()
    db.query(Recurso).delete()
    db.commit()
    print(
        "reset: usuarios, recursos, reservas, préstamos, solicitudes y "
        "notificaciones borrados"
    )


def run(reset: bool = False) -> None:
    init_db()
    db = SessionLocal()
    try:
        if reset:
            _reset(db)

        usuarios = _sembrar_usuarios(db)
        recursos = _sembrar_recursos(db)
        db.commit()
        solicitudes = _sembrar_solicitudes(db)
        db.commit()
        prestamos = _sembrar_prestamos(db)
        # aceptar_solicitud confirma cada préstamo y deja coherentes tanto el
        # estado del recurso como el historial y la notificación.
        reservas = _sembrar_reserva(db)
        db.commit()

        total_u = db.scalar(select(func.count()).select_from(Usuario))
        total_r = db.scalar(select(func.count()).select_from(Recurso))
        total_p = db.scalar(select(func.count()).select_from(Prestamo))
        total_s = db.scalar(select(func.count()).select_from(Solicitud))
        total_res = db.scalar(select(func.count()).select_from(Reserva))

        print(f"seeds: +{usuarios} usuarios, +{recursos} recursos, "
              f"+{solicitudes} solicitudes, +{prestamos} préstamos, "
              f"+{reservas} reservas "
              f"(total: {total_u} usuarios, {total_r} recursos, "
              f"{total_s} solicitudes, {total_p} préstamos, {total_res} reservas)")
        if usuarios == 0 and recursos == 0 and solicitudes == 0 and prestamos == 0 and reservas == 0:
            print("       nada que insertar, los datos ya estaban cargados")
        else:
            print(f"       contraseña de todos los usuarios: {PASSWORD_DEMO}")
    finally:
        db.close()


if __name__ == "__main__":
    run(reset="--reset" in sys.argv)
