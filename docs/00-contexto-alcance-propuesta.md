# Contexto, Alcance y Propuesta — Sistema de Préstamos (Grupo 8)

> Documento base del proyecto. Consolida el análisis de requisitos (Partes 1–3) y el
> modelo de dominio en un solo panorama, y fija el alcance y la ruta de construcción.
> **Curso:** Trabajo Interdisciplinario II (TI2) · EPCC · UNSA · 2026-B.

---

## 1. Contexto

**Sector:** educación superior — gestión de recursos académicos y de bienestar en la
Escuela Profesional de Ciencia de la Computación (EPCC) de la UNSA.

La Escuela presta a su comunidad **tres tipos de recurso**:

- **Libros** — gestionados por el **Centro de Estudiantes (CE)**.
- **Implementos deportivos** (balones, mesa de ping-pong) — gestionados por el **CE**.
- **Implementos académicos** (robot, procesador Nano, drones, workstation con GPU,
  Arduinos, podómetros, kits LEGO, escáner 3D, micrófonos inalámbricos, Oculus) —
  gestionados por **Infraestructura**.

Hoy la gestión es **manual y fragmentada**: cuadernos físicos, correos y acuerdos
verbales, repartida entre el CE e Infraestructura, **sin inventario centralizado, sin
historial, sin reservas y sin sanciones sistemáticas**.

---

## 2. El problema

### Enunciado (5W)

> Los estudiantes, el CE e Infraestructura de la EPCC necesitan **gestionar los préstamos**
> de libros, implementos deportivos y académicos *[necesidad]* para **acceder y controlar
> los recursos de forma confiable y trazable** *[objetivo]*, pero enfrentan un proceso
> **manual, disperso y sin trazabilidad ni control de disponibilidad** *[obstáculo]*.

### Estado actual → estado deseable

| Estado actual | Estado deseable |
|---|---|
| Cuadernos físicos, correos, acuerdos verbales | Plataforma web única y centralizada |
| Sin inventario centralizado | Inventario por tipo de recurso, con estado en tiempo real |
| Sin disponibilidad consultable | Consulta de disponibilidad y reservas con antelación |
| Sin historial ni trazabilidad | Registro de préstamos/devoluciones + historial + reportes |
| Sin sanciones sistemáticas | Sanciones por retraso/daño/pérdida + escalamiento a Dirección |

### Objetivo de diseño (SMART)

Diseñar un **sistema web de gestión de préstamos e inventario** para la EPCC que permita
**reservar, prestar y devolver** libros, implementos deportivos y académicos,
centralizando el inventario y reduciendo el tiempo de atención y la pérdida de ítems.

---

## 3. Stakeholders y roles

### Stakeholders

| Stakeholder | Tipo | Rol en el sistema |
|---|---|---|
| Estudiante | Directo | Solicita/reserva libros y deportivos; solicita y usa académicos. |
| Custodio del CE (estudiante) | Directo | Administra libros e implementos deportivos: entrega/recibe, garantía, registro. |
| Personal de Infraestructura | Directo | Administra implementos académicos; autoriza y controla su uso. |
| Docente | Directo | Avala/solicita el uso de académicos para cursos, tesis o investigación. |
| Dirección de la Escuela | Directo | Autoridad máxima; atiende pedidos excepcionales; autoriza administradores. |
| Centro de Estudiantes (organización) | Afectado | Responsable global de libros y deportivos; control y rendición de cuentas. |

### Roles del sistema (6 roles)

`ESTUDIANTE` · `DOCENTE` · `CUSTODIO_CE` · `CUSTODIO_INFRA` ·
`DIRECCION_ESCUELA` · `ADMINISTRADOR_SISTEMA`

- **Quién puede SOLICITAR:** cualquier rol; único requisito **no tener sanción activa**.
- **Quién APRUEBA/GESTIONA:**
  - `CUSTODIO_CE` → **registra** préstamos SIMPLE de libros/deportivos (la aprobación es automática; ver §4).
  - `CUSTODIO_INFRA` → aprueba **POR_CURSO** y **EXCEPCIONAL** (custodio de Infraestructura, incluye a los laboratoristas).
  - `DOCENTE` → **avala** solicitudes POR_CURSO.
  - `DIRECCION_ESCUELA` → **autoriza** solicitudes EXCEPCIONAL.
  - `ADMINISTRADOR_SISTEMA` → rol **técnico**: gestiona cuentas y permisos; **no** aprueba préstamos (RF7).
- Un mismo usuario puede tener **varios roles** a la vez (p. ej. un laboratorista es `CUSTODIO_INFRA` y a la vez puede solicitar un préstamo para sí como cualquier otro).

> **Cambio vs. borrador del diagrama:** se eliminó el rol `PERSONAL_ADMINISTRATIVO` (sin
> stakeholder/persona/historia que lo respaldara) y se renombró `CUSTODIO_ADMINISTRATIVO`
> → `CUSTODIO_INFRA` para evitar la colisión de nombres. Ver §8 (auditoría).

### Personas (arquetipos de usuario)

**Persona 1 — Diego Ramírez (la principal).** Estudiante de CC, 5.º semestre, 20 años.
Juega fútbol en los recreos y pide libros/equipos para sus cursos; prefiere resolver todo
desde el celular. **Objetivo:** reservar un balón o libro y saber si está disponible sin ir
a preguntar; devolver a tiempo. **Frustración:** no sabe qué está disponible, depende de
encontrar al del CE, el cuaderno es lento. *"Solo quiero saber si está libre y reservarlo
sin dar tantas vueltas."*

**Persona 2 — Rosa Quispe (custodio del CE).** Estudiante de CC, 7.º semestre, 21 años,
miembro del CE. **Objetivo:** llevar control de qué se prestó y a quién, recuperar los
ítems, reducir pérdidas. **Frustración:** el cuaderno se desordena; no hay forma rápida de
ver qué está prestado ni quién no devolvió. *"Si no lo anoto bien, después no sé quién se
llevó qué."*

**Persona 3 — Carlos Mendoza (Infraestructura).** Personal de la universidad, 38 años.
Custodia y presta los implementos académicos; recibe solicitudes por correo. **Objetivo:**
controlar quién usa los equipos, cuándo y con qué autorización; proteger el patrimonio.
**Frustración:** solicitudes dispersas por correo, sin inventario en tiempo real, difícil
de auditar. *"Necesito saber qué equipo salió, con qué autorización y cuándo vuelve."*

---

## 4. Modelo de dominio (resumen)

Organización por subdominios (DDD):

| Subdominio | Tipo | Responsabilidad |
|---|---|---|
| **Préstamos** | **Núcleo** | Registro y ciclo de vida del préstamo (ACTIVO/DEVUELTO/ATRASADO). |
| Identidad y Roles | Genérico | Usuarios y roles del sistema. |
| Catálogo de Recursos | Soporte | Inventario y estado (DISPONIBLE/RESERVADO/PRESTADO/MANTENIMIENTO). |
| Reservas | Soporte | *"¿CUÁNDO lo puedo tener?"* — reserva con antelación (booking) para una fecha/franja; incluye reservar para cuando el recurso se libere. |
| Solicitudes Académicas | Soporte | *"¿TENGO PERMISO?"* — solo POR_CURSO y EXCEPCIONAL. |
| Sanciones | Soporte | Sanciones por RETRASO / DAÑO / PÉRDIDA. |
| Historial y Reportes | Genérico | Vista de solo lectura sobre eventos del sistema (no transaccional). |

### Entidades principales

- **Usuario** (`codigo`, `nombres`, `email`, `activo`) con uno o varios **Rol**.
- **Recurso** (abstracto) → `Libro`, `ImplementoDeportivo`, `ImplementoAcademico`.
  `gestor`: `CENTRO_ESTUDIANTES` (libros/deportivos) o `INFRAESTRUCTURA` (académicos).
- **Reserva** — **reserva con antelación (booking)**: reservar un recurso para una
  `fecha`/`franja` futura. Cubre también el caso "no disponible ahora" (se reserva para
  cuando se libere). `prioridad` resuelve choques de franja. Al llegar la franja, un
  **custodio confirma la entrega** y la reserva *deriva en* préstamo (respetando
  `registradoPorId ≠ prestatarioId`). **Aplica a libros y académicos** (los deportivos son
  préstamo directo del mismo día, ver §5).
- **SolicitudAcademica** — solo para préstamos POR_CURSO y EXCEPCIONAL (implementos académicos).
- **Prestamo** — núcleo; con `tipoPrestamo`, `modalidadUso`, `condicionEntrega/Devolucion`.
- **Garantia**, **Sancion** (`RETRASO`/`DANIO`/`PERDIDA`), **Reporte**.

`modalidadUso` (`EN_SITIO` / `RETIRO_TEMPORAL`) indica si el ítem **sale del recinto** —
dato independiente del tipo (un libro SIMPLE es RETIRO; un deportivo SIMPLE es EN_SITIO).

### Tipos de préstamo

| Tipo | Aprobación | Registro / condición |
|---|---|---|
| **SIMPLE** | **Automática** (sin sanción + recurso disponible) | Lo **registra** un `CUSTODIO_CE`. Solo libros/deportivos. |
| **POR_CURSO** | `CUSTODIO_INFRA` aprueba + `DOCENTE` avala | Uso académico para un curso (normalmente EN_SITIO). |
| **EXCEPCIONAL** | `CUSTODIO_INFRA` aprueba + `DIRECCION_ESCUELA` autoriza | RETIRO_TEMPORAL fuera de la Escuela. |

**Prioridad en reservas (híbrida):** primero por tipo `EXCEPCIONAL > POR_CURSO > SIMPLE`
y, dentro del mismo tipo, **FIFO** (orden de solicitud).

### Invariantes / reglas

- **Aprobar ≠ registrar:** la *aprobación* de un SIMPLE es automática (decisión del
  sistema); la *entrega* la **registra** un custodio. Son dos actos distintos.
- **Tipo ↔ recurso (estricto):** libros/deportivos ⇒ **SIMPLE** siempre; POR_CURSO y
  EXCEPCIONAL ⇒ **solo** implementos académicos.
- `registradoPorId ≠ prestatarioId` — un custodio **no** puede autoregistrarse un préstamo
  (la *solicitud* es autoservicio, pero el *préstamo* siempre lo registra otra persona).
- Solo se puede solicitar si el usuario **no** tiene sanción activa.
- Historial y Reportes es una **vista de solo lectura**; no participa en transacciones.

### Diccionario de datos del dominio (modelo corregido)

**Entidades**

| Entidad | Atributos |
|---|---|
| **Usuario** | `codigo:String`, `nombres:String`, `email:String`, `activo:boolean`, `roles: Set<Rol>` |
| **Recurso** *(abstracto)* | `codigo:String`, `nombre:String`, `descripcion:String`, `ubicacion:String`, `estado:EstadoRecurso`, `gestor:Gestor` |
| ↳ **Libro** | `isbn:String`, `autor:String`, `categoria:String` |
| ↳ **ImplementoDeportivo** | `tipo:String` |
| ↳ **ImplementoAcademico** | `codigoPatrimonial:String`, `requiereAval:boolean` |
| **Reserva** | `fecha:Date`, `franja:String`, `estado:EstadoReserva`, `prioridad:int` |
| **SolicitudAcademica** | `motivo:String`, `fecha:Date`, `tipo:TipoSolicitud`, `estado:EstadoSolicitud` |
| **Prestamo** | `fechaEntrega:Date`, `fechaLimite:Date`, `fechaDevolucion:Date`, `estado:EstadoPrestamo`, `tipoPrestamo:TipoPrestamo`, `modalidadUso:ModalidadUso`, `condicionEntrega:String`, `condicionDevolucion:String`, `registradoPorId`, `prestatarioId` |
| **Garantia** | `tipo:String`, `valor:BigDecimal`, `devuelta:boolean` |
| **Sancion** | `motivo:MotivoSancion`, `inicio:Date`, `fin:Date`, `monto:BigDecimal`, `activa:boolean` |
| **Reporte** | `tipo:String`, `generadoEn:Date` |

> Nota: se eliminó `Prestamo.categoriaPrestatario` (se deriva del rol) y el enum
> `CategoriaPrestatario`. Ver §8 (auditoría, #6).

**Enumeraciones**

| Enum | Valores |
|---|---|
| **Rol** | ESTUDIANTE · DOCENTE · CUSTODIO_CE · CUSTODIO_INFRA · DIRECCION_ESCUELA · ADMINISTRADOR_SISTEMA |
| **Gestor** | CENTRO_ESTUDIANTES · INFRAESTRUCTURA |
| **EstadoRecurso** | DISPONIBLE · RESERVADO · PRESTADO · MANTENIMIENTO |
| **EstadoReserva** | PENDIENTE · CONFIRMADA · CANCELADA · VENCIDA |
| **TipoSolicitud** | POR_CURSO · EXCEPCIONAL |
| **EstadoSolicitud** | SOLICITADA · AVALADA · AUTORIZADA · RECHAZADA |
| **EstadoPrestamo** | ACTIVO · DEVUELTO · ATRASADO |
| **TipoPrestamo** | SIMPLE · POR_CURSO · EXCEPCIONAL |
| **ModalidadUso** | EN_SITIO · RETIRO_TEMPORAL |
| **MotivoSancion** | RETRASO · DANIO · PERDIDA |

### Relaciones del dominio

| Origen | Card. | Destino | Rol / semántica |
|---|---|---|---|
| Usuario | 0..* — 0..* | Rol | tiene |
| Usuario | 1 — 0..* | Reserva | realiza |
| Reserva | 0..* — 1 | Recurso | sobre |
| Reserva | 1 — 0..1 | Prestamo | deriva en (al llegar la franja) |
| Usuario | 1 — 0..* | Prestamo | prestatario |
| Usuario | 1 — 0..* | Prestamo | registra (custodio; `registradoPorId ≠ prestatarioId`) |
| Prestamo | 0..* — 1 | Recurso | entrega |
| Prestamo | 1 — 0..1 | Garantia | respalda *(composición)* |
| Prestamo | 1 — 0..1 | Sancion | puede generar |
| Usuario | 1 — 0..* | SolicitudAcademica | solicita (cualquier rol sin sanción; típ. estudiante/docente) |
| Usuario | 1 — 0..* | SolicitudAcademica | avala (docente) |
| Usuario | 1 — 0..* | SolicitudAcademica | autoriza (dirección) |
| SolicitudAcademica | 0..* — 1 | ImplementoAcademico | requiere |
| SolicitudAcademica | 1 — 0..1 | Prestamo | habilita (si disponible) |
| SolicitudAcademica | 1 — 0..1 | Reserva | genera (si no disponible ahora) |
| Sancion | 0..* — 1 | Usuario | afecta |
| Usuario | 1 — 0..* | Reporte | genera (dirección) |

> **Este documento es la fuente de verdad del modelo.** El diagrama
> `modelo-dominio-grupo8.pdf` y el `.puml` de `../Tarea-1/` reflejan una versión previa
> (7 roles, `categoriaPrestatario`, `CUSTODIO_ADMINISTRATIVO`) y deben regenerarse a partir
> de este diccionario.

---

## 5. Alcance

> Esta sección define el **alcance del sistema** (el producto completo que se especifica).
> El **alcance de la entrega** (qué se construye en cada release) es un subconjunto y se
> detalla en §7 — p. ej. el MVP (R1) no incluye aún el módulo completo de sanciones.

### Dentro del alcance ✅

- Los **tres tipos de recurso** (libros, implementos deportivos, implementos académicos).
- Los **6 roles** y sus flujos de solicitud/aprobación.
- Los **3 tipos de préstamo** (SIMPLE / POR_CURSO / EXCEPCIONAL).
- **Reservas con antelación (booking)** para libros y académicos, con prioridad híbrida.
- **Deportivos**: préstamo **directo del mismo día** (se pide y se devuelve el mismo día,
  sin reserva anticipada; el plazo vence al final del día).
- **Préstamos y devoluciones** con garantía, estado del ítem y plazos.
- **Sanciones** (multa / bloqueo temporal / reposición) por retraso, daño o pérdida.
- **Historial y reportes** de inventario y préstamos.
- **Autenticación** (login propio, ver Supuestos) y control de acceso por rol.

### Fuera del alcance ❌

- Reserva/gestión de **salones y laboratorios** (solo se prestan recursos, no espacios).
- Pagos electrónicos de multas (la multa se **registra**; el cobro es fuera del sistema).
- Integración con sistemas externos de la universidad (SIGA, biblioteca central, etc.).
- App móvil nativa (el requisito es **web responsive**, no app de tienda).
- **Lista de espera (waitlist) como concepto separado**: queda absorbida por el booking
  (reservar para cuando el recurso se libere).
- **SSO institucional real de UNSA**: el prototipo usa login propio (ver supuestos).

### Supuestos

- **Autenticación:** login propio con **correo institucional + contraseña** y roles en BD
  (mock institucional). El SSO real de UNSA queda como trabajo futuro de producción.
- El equipo del CE e Infraestructura opera el sistema como administradores con permiso de
  Dirección.
- Los datos personales sensibles (DNI/CUI) se protegen (RNF1).

---

## 6. Requisitos (resumen de la Parte 3)

### Features funcionales (RF)

| Feature | Descripción |
|---|---|
| **RF1** | Catálogo / Inventario (alta/baja/estado, consulta de disponibilidad) |
| **RF2** | Reservas (crear, cancelar/modificar, resolución de prioridad) |
| **RF3** | Préstamos / Devoluciones (garantía, estado, plazos, marcado de vencidos) |
| **RF4** | Autorización de académicos (solicitud → aval docente → autorización Infra/Dirección) |
| **RF5** | Sanciones (bloqueo temporal, multa/reposición, consulta de sanciones activas) |
| **RF6** | Historial y Reportes (historial por usuario, reportes de inventario/préstamos) |
| **RF7** | Usuarios / Roles (login institucional, gestión de roles y permisos) |

### Requisitos no funcionales (RNF)

| RNF | Descripción |
|---|---|
| **RNF1** | Seguridad — autenticación institucional, roles/permisos, protección de DNI/CUI, auditoría |
| **RNF2** | Usabilidad — responsive (uso desde móvil) |
| **RNF3** | Rendimiento — consulta de disponibilidad en < 2 s |
| **RNF4** | Disponibilidad — servicio activo en horario académico |

### Plan de releases (de la Parte 3)

| Release | Contenido |
|---|---|
| **R1 (MVP)** | RF1 + RF2 + RF3 + RF7 + RNF1 + RNF2 |
| **R2** | RF4 + RF5 + RNF3 |
| **R3** | RF6 + RNF4 + mejoras |

### Necesidades de usuario (Parte 2 — diagrama de afinidad)

14 historias observadas (formato POV: *el [usuario] necesita [necesidad] porque [insight]*),
agrupadas por afinidad:

- **G1 · Disponibilidad y reserva** — el estudiante necesita **saber qué hay disponible
  antes de ir**, **reservar con antelación** y **solicitar un implemento académico** para su
  curso/tesis.
- **G2 · Registro y control de préstamos** — el custodio del CE necesita **registrar rápido
  a quién entrega**, **saber qué está prestado y quién no devolvió**, y **registrar garantía
  y estado** del ítem.
- **G3 · Autorización y control de equipos** — Infraestructura necesita **recibir/autorizar
  solicitudes** y **verificar estado/disponibilidad**; el docente **avala** el uso; la
  dirección **autoriza pedidos excepcionales**.
- **G4 · Devolución, sanciones y estado** — el estudiante necesita **conocer plazo y
  condiciones**; custodio/Infra necesita **aplicar sanciones** por retraso/daño/pérdida.
- **G5 · Historial y reportes** — el estudiante necesita **consultar su historial**; la
  dirección necesita **ver reportes** de inventario y préstamos.

### Backlog completo de historias de usuario (Parte 3)

Prioridad (MoSCoW): ALTA/DEBE · MEDIA/DEBERÍA · BAJA/PODRÍA. Puntos (Planning Poker): 1,2,3,5,8,13.
*(Estimación inicial del equipo, sujeta a ajuste.)*

| ID | Perfil | Historia (Como… quiero…) | Feature | Prior. | Pts |
|---|---|---|---|---|---|
| HF.1.1.1 | Estudiante | consultar el catálogo y la disponibilidad de los recursos | RF1 | ALTA | 5 |
| HF.1.2.1 | Custodio/Infra | registrar y actualizar ítems del inventario (alta/baja/estado) | RF1 | ALTA | 5 |
| HF.1.3.1 | Custodio/Infra | ver el estado de cada ítem (disponible/prestado/reservado/mant.) | RF1 | ALTA | 3 |
| HF.2.1.1 | Estudiante | reservar un recurso con antelación | RF2 | ALTA | 5 |
| HF.2.2.1 | Estudiante | cancelar o modificar mi reserva | RF2 | MEDIA | 3 |
| HF.2.3.1 | Sistema | resolver la prioridad (híbrida: tipo + FIFO) ante conflicto | RF2 | MEDIA | 5 |
| HF.3.1.1 | Custodio CE | registrar la entrega con garantía (carnet/DNI) y estado del ítem | RF3 | ALTA | 5 |
| HF.3.2.1 | Custodio CE | registrar la devolución y verificar el estado | RF3 | ALTA | 3 |
| HF.3.3.1 | Estudiante | ver el plazo de devolución de mi préstamo | RF3 | ALTA | 2 |
| HF.3.4.1 | Sistema | marcar como vencido el préstamo que pasó su plazo | RF3 | ALTA | 3 |
| HF.4.1.1 | Estudiante | solicitar un implemento académico (curso/tesis + equipo) | RF4 | ALTA | 5 |
| HF.4.2.1 | Docente | avalar la solicitud de mis alumnos | RF4 | ALTA | 3 |
| HF.4.3.1 | Infraestructura | autorizar o rechazar solicitudes de equipos | RF4 | ALTA | 5 |
| HF.4.4.1 | Dirección | autorizar pedidos excepcionales (sacar un equipo de la Escuela) | RF4 | MEDIA | 3 |
| HF.5.1.1 | Sistema | aplicar bloqueo temporal a quien devuelve tarde | RF5 | MEDIA | 5 |
| HF.5.2.1 | Custodio/Infra | registrar daño o pérdida y generar la sanción (multa/reposición) | RF5 | MEDIA | 5 |
| HF.5.3.1 | Estudiante | ver mis sanciones activas y su vencimiento | RF5 | MEDIA | 2 |
| HF.6.1.1 | Estudiante | consultar mi historial de préstamos | RF6 | BAJA | 2 |
| HF.6.2.1 | Dirección | ver reportes de inventario y préstamos | RF6 | MEDIA | 5 |
| HF.7.1.1 | Usuario | iniciar sesión con correo institucional | RF7 | ALTA | 5 |
| HF.7.2.1 | Administrador | gestionar roles y permisos | RF7 | ALTA | 3 |
| HNF.1.1.1 | Sistema | autenticar por login institucional y proteger datos (DNI/CUI) | RNF1 | ALTA | 5 |
| HNF.2.1.1 | Estudiante | usar el sistema desde el móvil (responsive) | RNF2 | ALTA | 3 |
| HNF.3.1.1 | Sistema | responder la consulta de disponibilidad en < 2 s | RNF3 | MEDIA | 3 |
| HNF.4.1.1 | Sistema | estar disponible en horario académico | RNF4 | MEDIA | 3 |

---

## 7. Propuesta de ruta para terminar el proyecto

Estado: **análisis (Partes 1–3) y modelo de dominio → cerrados.** Lo que falta es
**construir el prototipo** siguiendo el plan de releases ya definido.

**Stack decidido:**
- **Backend:** **FastAPI + SQLAlchemy + PostgreSQL** (API REST).
- **Frontend (aparte):** **HTML/CSS/JavaScript (vanilla) + Bootstrap 5**, que consume la API
  vía `fetch`; responsive (RNF2).
- **Auth:** login propio (mock institucional) con JWT.

> **Nota de equipo:** se eligió frontend separado **sin framework** para que los integrantes
> junior (solo HTML/CSS/JS) puedan aportar. La parte más exigente para ellos es el
> `fetch`/render en JS; el líder técnico provee un **patrón reutilizable** (helper de
> `fetch` + funciones de render) para que se concentren en HTML/CSS/Bootstrap. Ver §9.

Las Fases A y B (diseño técnico y diseño de producto) pueden avanzar **en paralelo**;
ambas alimentan la implementación (Fase C).

### Fase A — Diseño técnico (puente dominio → código)

1. **Modelo relacional (BD)** derivado del dominio + enumeraciones (con la restricción
   tipo ↔ recurso e invariante `registradoPor ≠ prestatario`).
2. **Diagramas de secuencia** de los flujos críticos:
   - Reserva (booking) → derivar en préstamo al llegar la franja; desempate por prioridad.
   - Préstamo SIMPLE (auto-aprobación + registro por custodio, recurso disponible, sin sanción).
   - Solicitud académica POR_CURSO / EXCEPCIONAL con aval docente / autorización dirección.
3. **Contrato de API** (endpoints REST por feature, alineados a los RF).

### Fase B — Diseño de producto (UX/UI · front mockups)

1. **Mapa de flujos por rol** (estudiante, custodio CE, custodio infra, dirección) — qué
   pantallas ve y qué acciones puede hacer cada uno.
2. **Wireframes low-fidelity** de las pantallas clave (catálogo/disponibilidad, reserva,
   registro de préstamo/devolución, solicitud académica, sanciones, historial).
3. **Mockups de alta fidelidad (front)** — el diseño visual real: layout, componentes,
   estados (vacío/carga/error), responsive (móvil primero, RNF2).
4. **Prototipo navegable** (p. ej. Figma) para validar el flujo con usuarios antes de codear.

### Fase C — Implementación R1 (MVP)

Login + roles (RF7, RNF1) · Catálogo/inventario (RF1) · Reservas con prioridad (RF2) ·
Préstamos/devoluciones con garantía y estado (RF3) · responsive (RNF2).
Incluye **bloqueo básico por sanción** (dependencia de RF3: marcar vencidos y bloquear).

### Fase D — Releases 2 y 3

Sanciones completas (RF5) · Autorización de académicos (RF4) · Historial y reportes (RF6).

### Fase E — Cierre

Pruebas, README de despliegue y evidencia del curso (tablero Trello / User Story Mapping).

### Decisiones pendientes

- **Alcance a entregar.** Trabajamos sobre el supuesto de **MVP (R1)**; si el equipo/curso
  exige el prototipo completo, se extiende a la Fase D. — **por confirmar con el equipo**.

---

## 8. Auditoría del alcance — hallazgos y resolución

Auditoría de coherencia entre el modelo de dominio (diagrama actualizado) y las Partes 1–3
del análisis. Cada hallazgo quedó resuelto así:

| # | Hallazgo (fallo de lógica) | Resolución |
|---|---|---|
| 1 | "Reserva" tenía dos significados: booking (Partes 2–3) vs cola de no-disponible (dominio). | **Reserva = booking anticipado**; absorbe el caso "no disponible" (se reserva para cuando se libere). |
| 2 | Prioridad contradictoria: FIFO (Parte 3) vs por tipo (dominio). | **Híbrida:** por tipo `EXCEPCIONAL>POR_CURSO>SIMPLE` y FIFO dentro del mismo tipo. |
| 3 | SIMPLE decía "auto-aprobado" y a la vez "lo aprueba CUSTODIO_CE". | **Aprobar ≠ registrar:** aprobación automática; el custodio **registra** la entrega. |
| 4 | Nada impedía un libro POR_CURSO o un académico SIMPLE. | **Invariante estricto tipo ↔ recurso** (libros/deportivos = SIMPLE; académicos = POR_CURSO/EXCEPCIONAL). |
| 5 | `PERSONAL_ADMINISTRATIVO` sin stakeholder/persona/historia. | **Eliminado** (→ 6 roles). El caso "staff que pide para sí" lo cubre `CUSTODIO_INFRA`. |
| 6 | `categoriaPrestatario` y `modalidadUso` parecían redundantes. | **`categoriaPrestatario` eliminado** (se deriva del rol). **`modalidadUso` se conserva** (indica si el ítem sale del recinto; no es derivable del tipo). |
| 7 | RF3 (R1) "dispara sanciones" pero RF5 está en R2. | R1 incluye **bloqueo básico por sanción**; el módulo completo de sanciones queda en R2. |
| 8 | Tres significados de "administrativo". | **`CUSTODIO_ADMINISTRATIVO` → `CUSTODIO_INFRA`**. |
| 9 | Dos modelos de dominio vivos (puml viejo de 5 roles vs actualizado). | Fuente de verdad = **este documento** (§4). El `.puml` de `Tarea-1/` (5 roles) y el PDF `modelo-dominio-grupo8.pdf` son versiones previas a regenerar. |
| 10 | "Reposición" no se modela limpio en `Sancion`. | Pendiente menor: se refinará en Fase A (BD) al detallar `Sancion`. |
| 11 | RNF1 pide login institucional real, inviable para prototipo. | **Login propio (mock institucional)**; SSO UNSA = trabajo futuro. |
| 12 | Invariante `registradoPor ≠ prestatario` chocaba con autoservicio. | Aclarado: la **solicitud** es autoservicio; el **préstamo** siempre lo registra otra persona. |

> **Sincronización pendiente:** el diagrama PDF (`modelo-dominio-grupo8.pdf`) y el `README.md`
> aún reflejan el modelo previo (7 roles, `categoriaPrestatario`, `CUSTODIO_ADMINISTRATIVO`).
> Deben regenerarse para alinearse con este documento antes de la siguiente entrega.

## 9. Equipo y distribución del trabajo

| Integrante | Perfil | Responsabilidad |
|---|---|---|
| **Mariana Valery Luis Jimenez** | Backend Python (semi-junior) | Modelos SQLAlchemy · endpoints FastAPI · CRUD de catálogo y préstamos/devoluciones |
| **Aldair Daniel Condori Ataucuri** | HTML/CSS/JS (junior, sin frameworks) | Frontend (HTML/CSS/Bootstrap + `fetch`): catálogo/disponibilidad · reservas · historial |
| **Fernando Enrique Llosa Manchego** | HTML/CSS/JS (junior, sin frameworks) | Frontend (HTML/CSS/Bootstrap + `fetch`): préstamos/devoluciones · sanciones · login |
| **Cristhian Luis Taipe Huanca** | Senior (hackathones/trabajo), desarrolla con IA | Arquitectura · esquema BD · auth/roles (JWT) · lógica compleja (prioridad de reservas, invariantes, flujos de aprobación) · **capa JS de integración (helper `fetch`/render)** · code review · apoyo al equipo |

**Consideraciones de reparto**

- **Frontend por pantallas** (propuesta de trabajo): cada junior es dueño de su conjunto de
  vistas; el líder técnico entrega el patrón `fetch`/render y los componentes base (Bootstrap)
  para que ellos rellenen HTML/CSS.
- **Backend con apoyo:** Mariana lidera el CRUD estándar; el líder técnico toma la lógica de
  dominio no trivial (cola de prioridad, invariante tipo↔recurso, `registradoPor ≠ prestatario`,
  aprobaciones POR_CURSO/EXCEPCIONAL).
- **Riesgo principal:** el JS de consumo de API supera el nivel junior → mitigado con el helper
  reutilizable y pair-programming puntual con el líder técnico.

**Profesora:** Yessenia Deysi Yari Ramos
