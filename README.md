# Sistema de Préstamos — Trabajo Interdisciplinario II (Grupo 8)

Proyecto semestral del curso **Trabajo Interdisciplinario II** — Escuela Profesional de
Ciencia de la Computación, Facultad de Ingeniería de Producción y Servicios,
**Universidad Nacional de San Agustín (UNSA)**, Arequipa – Perú, 2026.

## Descripción

Sistema para gestionar el **préstamo de recursos** de la Escuela: libros e implementos
deportivos (gestionados por el Centro de Estudiantes) e implementos académicos
(gestionados por Infraestructura). El sistema controla solicitudes, reservas, aprobaciones
según el tipo de préstamo, sanciones e historial/reportes.

## Equipo

- Mariana Valery Luis Jimenez
- Fernando Enrique Llosa Manchego
- Aldair Daniel Condori Ataucuri
- Cristhian Luis Taipe Huanca

**Profesora:** Yessenia Deysi Yari Ramos

## Modelo de dominio

Diagrama completo en [`docs/modelo-dominio-grupo8.pdf`](docs/modelo-dominio-grupo8.pdf).

El dominio se organiza en subdominios:

| Subdominio | Tipo | Responsabilidad |
|---|---|---|
| Identidad y Roles | Genérico | Usuarios y roles del sistema |
| Catálogo de Recursos | Soporte | Inventario de libros, implementos deportivos y académicos |
| Reservas | Soporte | Responde *"¿CUÁNDO lo puedo tener?"* cuando el recurso no está disponible |
| Solicitudes Académicas | Soporte | Responde *"¿TENGO PERMISO para tenerlo?"* (solo POR_CURSO y EXCEPCIONAL) |
| **Préstamos** | **Núcleo** | Registro y ciclo de vida del préstamo |
| Sanciones | Soporte | Sanciones por retraso, daño o pérdida |
| Historial y Reportes | Genérico | Vista de solo lectura sobre eventos del sistema |

### Entidades principales

- **Usuario** (`codigo`, `nombres`, `email`, `activo`) con uno o varios **Rol**.
- **Recurso** (abstracto) → `Libro`, `ImplementoDeportivo`, `ImplementoAcademico`.
  Atributo `gestor`: `CENTRO_ESTUDIANTES` (libros/deportivos) o `INFRAESTRUCTURA` (académicos).
- **Reserva** — se crea cuando el recurso no está disponible; `prioridad` ordena la cola
  (`EXCEPCIONAL > POR_CURSO > SIMPLE`).
- **SolicitudAcademica** — solo para préstamos `POR_CURSO` y `EXCEPCIONAL`.
- **Prestamo** — entidad núcleo, con `tipoPrestamo` y `modalidadUso`
  (la categoría del prestatario se deriva del rol; ver auditoría §8 del doc base).
- **Garantia**, **Sancion** (`RETRASO`, `DANIO`, `PERDIDA`), **Reporte**.

### Roles

`ESTUDIANTE`, `DOCENTE`, `CUSTODIO_CE`, `CUSTODIO_INFRA`,
`DIRECCION_ESCUELA`, `ADMINISTRADOR_SISTEMA`.

- **Solicitar:** cualquier rol, único requisito no tener sanción activa.
- **Aprobar/gestionar:**
  - `CUSTODIO_CE` → préstamos **SIMPLE** de libros/deportivos.
  - `CUSTODIO_INFRA` → aprueba **POR_CURSO** y **EXCEPCIONAL**.
  - `DOCENTE` → avala solicitudes **POR_CURSO**.
  - `DIRECCION_ESCUELA` → autoriza **EXCEPCIONAL**.
  - `ADMINISTRADOR_SISTEMA` → rol técnico; gestiona cuentas y permisos, **no** aprueba préstamos (RF7).
- Un mismo usuario puede tener varios roles a la vez.

### Tipos de préstamo

- **SIMPLE:** cualquier persona, aprobación automática (sin sanción + recurso disponible).
- **POR_CURSO:** aprueba `CUSTODIO_INFRA` + verifica `DOCENTE`.
- **EXCEPCIONAL:** aprueba `CUSTODIO_INFRA` + verifica `DIRECCION_ESCUELA`
  (retiro temporal fuera de la Escuela).

**Invariante:** `registradoPorId ≠ prestatarioId` — un custodio no puede autoregistrarse un préstamo.

> **Fuente de verdad:** el contexto/alcance/dominio está en
> [`docs/00-contexto-alcance-propuesta.md`](docs/00-contexto-alcance-propuesta.md), el diseño
> técnico en [`docs/01-sdd.md`](docs/01-sdd.md) y el contrato de los endpoints del 30% en
> [`docs/02-contrato-api.md`](docs/02-contrato-api.md). Este README es un resumen.

## Stack

- **Backend:** FastAPI + SQLAlchemy + PostgreSQL (API REST)
- **Frontend:** HTML/CSS/JavaScript + Bootstrap 5 (consume la API vía `fetch`)
- **Auth:** JWT (login propio)

## Estructura del repositorio

```
backend/     API FastAPI (app/: main, models, schemas, routers, services, security)
frontend/    Cliente web estático (HTML/CSS/JS + Bootstrap)
docs/        Documentación (contexto, SDD, modelo de dominio)
docker-compose.yml
```

## Cómo ejecutar (desarrollo)

### Opción A — Docker (recomendada, un solo comando)

```bash
docker compose up --build
```

- API:        http://localhost:8000  · Swagger: http://localhost:8000/docs · Health: http://localhost:8000/api/health
- PostgreSQL: localhost:**5433** (usuario/clave/db: `prestamos`)
- Frontend:   servir la carpeta `frontend/` (p. ej. la extensión **Live Server** de VS Code,
  o `python -m http.server 5500` dentro de `frontend/`) y abrir `index.html`.

### Opción B — venv local (sin Docker)

Requiere Python 3.12+ y un PostgreSQL corriendo.

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # ajustar DATABASE_URL a tu Postgres local
uvicorn app.main:app --reload
```

### Datos de ejemplo (seeds)

Con la API corriendo, cargá el catálogo y los usuarios de prueba:

```bash
docker compose exec api python -m app.seeds     # Docker
python -m app.seeds                             # venv, dentro de backend/
```

Se puede correr las veces que haga falta: solo inserta lo que falta. Con `--reset`
borra usuarios y recursos antes de volver a insertarlos.

Crea **7 usuarios** (uno por cada rol, más uno con dos roles) y **10 recursos**
en distintos estados. La contraseña de todos es `prestamos123`.

| Email | Rol |
|---|---|
| `diego@unsa.edu.pe` | ESTUDIANTE |
| `lucia@unsa.edu.pe` | DOCENTE |
| `pedro@unsa.edu.pe` | CUSTODIO_CE |
| `rosa@unsa.edu.pe` | CUSTODIO_INFRA |
| `elena@unsa.edu.pe` | DIRECCION_ESCUELA |
| `ivan@unsa.edu.pe` | ADMINISTRADOR_SISTEMA |
| `marta@unsa.edu.pe` | DOCENTE + CUSTODIO_CE |

> Son credenciales de desarrollo, solo para la demo. No usar en nada real.

> **Nota sobre el esquema:** todavía no hay migraciones (Alembic). Las tablas se crean
> al arrancar la API a partir de los modelos, y `create_all` **no** modifica tablas ya
> existentes: si cambian las columnas de un modelo, hay que recrear la base con
> `docker compose down -v`.

> Repositorio del semestre; se irá completando conforme avancen las entregas del curso.
