# Contrato de API — login y catálogo (entrega del 30%)

> **Para qué sirve:** es el acuerdo entre backend y frontend para los dos endpoints
> de la entrega del 30%. Quien hace el frontend puede maquetar y programar el `fetch`
> **sin esperar** a que el backend esté listo: basta con respetar estas formas.
>
> Alcance: `POST /api/auth/login` (RF7) y `GET /api/recursos` (RF1). El resto de
> endpoints está esbozado en [`01-sdd.md`](01-sdd.md) §4 y se detallará en su issue.
>
> Issues que dependen de este documento: #7 y #8 (backend), #10 y #11 (catálogo),
> #13 y #14 (login).

---

## 1. Convenciones generales

| Aspecto | Valor |
|---|---|
| Base URL (desarrollo) | `http://localhost:8000/api` |
| Formato | JSON en request y response (`Content-Type: application/json`) |
| Autenticación | `Authorization: Bearer <access_token>` en todo endpoint salvo `POST /auth/login` |
| Codificación | UTF-8 |

### Formato de error

**Todos** los errores usan la misma forma (es la de FastAPI):

```jsonc
{ "detail": "Credenciales inválidas" }
```

La única excepción es el **422** de validación, que FastAPI genera automáticamente
cuando el JSON enviado no cumple el esquema. Ahí `detail` es una lista:

```jsonc
{ "detail": [ { "loc": ["body", "email"], "msg": "field required", "type": "missing" } ] }
```

> **Para el frontend:** mostrá `detail` si es string; si es lista, mostrá un mensaje
> genérico del tipo "Revisá los datos del formulario". No asumas que siempre es string.

### Códigos de estado

| Código | Cuándo |
|---|---|
| `200` | Operación completada con respuesta |
| `201` | Recurso creado |
| `204` | Operación completada sin cuerpo de respuesta |
| `401` | Sin token, token vencido/inválido, o credenciales incorrectas en el login |
| `403` | Autenticado, pero sin permiso para la acción solicitada. |
| `404` | El recurso no existe |
| `409` | Conflicto con una regla de negocio o con el estado actual del registro |
| `422` | El JSON enviado o un parámetro de consulta no cumple el esquema |

---

## 2. `POST /api/auth/login` — RF7

Público (no lleva token). Devuelve el JWT con el que se firman las demás llamadas.

### Request

```jsonc
{
  "email": "diego@unsa.edu.pe",
  "password": "secreto123"
}
```

| Campo | Tipo | Obligatorio | Notas |
|---|---|---|---|
| `email` | string | sí | Se usa el email, **no** el código, como identificador de login |
| `password` | string | sí | En texto plano sobre HTTPS; el backend compara contra el hash bcrypt |

### Response `200`

```jsonc
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "codigo": "20200001",
    "nombres": "Diego Ramírez",
    "email": "diego@unsa.edu.pe",
    "roles": ["ESTUDIANTE", "DOCENTE"]
  }
}
```

| Campo | Tipo | Notas |
|---|---|---|
| `access_token` | string | JWT. Vence a las 8 h (`JWT_EXPIRE_MINUTES=480`) |
| `token_type` | string | Siempre `"bearer"` |
| `user.roles` | string[] | **Siempre un array**, aunque tenga un solo rol. Valores del enum `Rol` (§4) |

> `user` viene incluido en la respuesta del login a propósito: evita que el frontend
> tenga que llamar a `/auth/me` inmediatamente después para saber a qué pantalla redirigir.

### Errores

| Código | Cuerpo | Cuándo |
|---|---|---|
| `401` | `{ "detail": "Credenciales inválidas" }` | Email inexistente **o** contraseña incorrecta |
| `401` | `{ "detail": "Usuario inactivo" }` | Existe y la contraseña es correcta, pero `activo = false` |
| `422` | lista de validación | Falta `email` o `password`, o el email está malformado |

> **Seguridad:** email inexistente y contraseña incorrecta devuelven **el mismo**
> mensaje a propósito, para no revelar qué emails están registrados.

### `GET /api/auth/me`

Sirve para revalidar la sesión al recargar la página. Requiere token y devuelve
exactamente el mismo objeto que `user` del login (sin envolver):

```jsonc
{ "id": 1, "codigo": "20200001", "nombres": "Diego Ramírez",
  "email": "diego@unsa.edu.pe", "roles": ["ESTUDIANTE"] }
```

| Código | Cuerpo | Cuándo |
|---|---|---|
| `401` | `{ "detail": "No autenticado" }` | Falta el header `Authorization` |
| `401` | `{ "detail": "Token inválido o expirado" }` | Token malformado, firmado con otra clave, vencido, o el usuario ya no existe |
| `401` | `{ "detail": "Usuario inactivo" }` | La cuenta fue desactivada después de emitirse el token |

> Los roles se leen de la base de datos en cada request, no del token: si un administrador
> le quita un rol a alguien, el cambio aplica en la siguiente llamada sin esperar a que
> venza el JWT. Lo mismo con la desactivación de la cuenta.

---

## 3. `GET /api/recursos` — RF1

Lista el catálogo. Requiere estar autenticado (cualquier rol).

### Query params — todos opcionales

| Param | Tipo | Ejemplo | Efecto |
|---|---|---|---|
| `tipo` | enum `TipoRecurso` | `?tipo=LIBRO` | Filtra por tipo de recurso |
| `estado` | enum `EstadoRecurso` | `?estado=DISPONIBLE` | Filtra por estado exacto |
| `disponible` | boolean | `?disponible=true` | Atajo de `estado=DISPONIBLE`. Si se manda junto con `estado`, gana `estado` |
| `q` | string | `?q=clean` | Búsqueda parcial, **sin distinguir mayúsculas**, sobre `nombre` y `codigo` |

Se combinan con AND: `?tipo=LIBRO&disponible=true&q=clean`.

Un valor inválido en `tipo` o `estado` devuelve `422` (lo valida FastAPI con el enum).

### Response `200`

Un **array** (vacío `[]` si no hay coincidencias, nunca `null` ni un 404).

```jsonc
[
  {
    "id": 10,
    "codigo": "LIB-001",
    "nombre": "Clean Code",
    "descripcion": "Manual de estilo y buenas prácticas",
    "ubicacion": "Estante B-2",
    "estado": "DISPONIBLE",
    "gestor": "CENTRO_ESTUDIANTES",
    "tipo_recurso": "LIBRO",
    "disponible": true,
    "isbn": "9780132350884",
    "autor": "Robert C. Martin",
    "categoria": "Software"
  },
  {
    "id": 11,
    "codigo": "DEP-004",
    "nombre": "Balón de fútbol",
    "descripcion": null,
    "ubicacion": "Depósito CE",
    "estado": "PRESTADO",
    "gestor": "CENTRO_ESTUDIANTES",
    "tipo_recurso": "DEPORTIVO",
    "disponible": false,
    "tipo_deportivo": "Fútbol"
  },
  {
    "id": 12,
    "codigo": "ACA-002",
    "nombre": "Proyector Epson X05",
    "descripcion": null,
    "ubicacion": "Oficina de Infraestructura",
    "estado": "DISPONIBLE",
    "gestor": "INFRAESTRUCTURA",
    "tipo_recurso": "ACADEMICO",
    "disponible": true,
    "codigo_patrimonial": "PAT-9981",
    "requiere_aval": true
  }
]
```

### Campos

**Comunes a todo recurso** — siempre presentes:

| Campo | Tipo | Notas |
|---|---|---|
| `id` | int | |
| `codigo` | string | Único en todo el catálogo |
| `nombre` | string | |
| `descripcion` | string \| **null** | |
| `ubicacion` | string \| **null** | |
| `estado` | enum `EstadoRecurso` | |
| `gestor` | enum `Gestor` | |
| `tipo_recurso` | enum `TipoRecurso` | Discrimina qué campos extra trae el objeto |
| `disponible` | boolean | Derivado: `estado == "DISPONIBLE"`. Viene calculado para que el frontend no repita la regla |

**Según `tipo_recurso`** — presentes **solo** en su tipo:

| `tipo_recurso` | Campos extra |
|---|---|
| `LIBRO` | `isbn`, `autor`, `categoria` (string \| null) |
| `DEPORTIVO` | `tipo_deportivo` (string \| null) |
| `ACADEMICO` | `codigo_patrimonial` (string \| null), `requiere_aval` (boolean \| null) |

> ⚠️ **Lo más importante para el frontend:** las claves de un tipo **no aparecen** en los
> objetos de otro tipo — un `DEPORTIVO` no trae la clave `autor` ni siquiera en `null`.
> Accedé siempre con guarda (`recurso.autor ?? "—"`) o ramificá por `tipo_recurso`.
>
> Y ojo con la diferencia: `tipo_recurso` es el enum del sistema; `tipo_deportivo` es
> texto libre que describe el deporte. No son lo mismo.

### Errores

| Código | Cuerpo | Cuándo |
|---|---|---|
| `401` | `{ "detail": "No autenticado" }` | Falta el header `Authorization` o el token venció |
| `422` | lista de validación | `tipo` o `estado` con un valor fuera del enum |

---

## 4. Valores de los enums

El frontend debe tratarlos como **strings exactos, en mayúsculas**. Son los que viajan
por la API; el texto bonito para el usuario se arma en el frontend.

| Enum | Valores |
|---|---|
| `Rol` | `ESTUDIANTE` · `DOCENTE` · `CUSTODIO_CE` · `CUSTODIO_INFRA` · `DIRECCION_ESCUELA` · `ADMINISTRADOR_SISTEMA` |
| `TipoRecurso` | `LIBRO` · `DEPORTIVO` · `ACADEMICO` |
| `EstadoRecurso` | `DISPONIBLE` · `RESERVADO` · `PRESTADO` · `MANTENIMIENTO` |
| `Gestor` | `CENTRO_ESTUDIANTES` · `INFRAESTRUCTURA` |

Regla de coherencia que garantiza el backend: los `ACADEMICO` siempre tienen
`gestor = INFRAESTRUCTURA`, y los `LIBRO` / `DEPORTIVO` siempre `CENTRO_ESTUDIANTES`.

---

## 5. Cómo lo consume el frontend

Guardá el token al hacer login y mandalo en cada llamada posterior:

```js
// 1. Login
const res = await fetch("http://localhost:8000/api/auth/login", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email, password }),
});
if (!res.ok) {
  const err = await res.json();
  throw new Error(typeof err.detail === "string" ? err.detail : "Datos inválidos");
}
const { access_token, user } = await res.json();
localStorage.setItem("token", access_token);

// 2. Catálogo, ya con el token
const recursos = await fetch("http://localhost:8000/api/recursos?disponible=true", {
  headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
}).then((r) => r.json());
```

Si una llamada devuelve `401`, borrá el token y mandá al usuario al login: significa
que la sesión venció.

> El helper reutilizable que envuelve esto vive en `frontend/js/api.js` (issue #5).

### CORS

El backend solo acepta los orígenes listados en `CORS_ORIGINS`. Ya vienen habilitados:

- `http://localhost:5500` y `http://127.0.0.1:5500` — Live Server de VS Code
- `http://localhost:8080` — solo si levantás con Docker (está en `docker-compose.yml`)

Si servís el frontend en otro puerto, agregalo a `CORS_ORIGINS` (en `docker-compose.yml`
si usás Docker, o en `backend/.env` si corrés con venv) o la petición falla en el
navegador aunque el endpoint funcione bien desde Swagger.

---

## 6. Pendiente de definir

- Paginación de `GET /api/recursos`. Para el 30% el catálogo es chico y se devuelve
  completo; cuando crezca habrá que decidir entre `?page/?size` o `?limit/?offset`.
- Orden por defecto del listado (hoy: sin orden garantizado; conviene fijar `codigo ASC`).
- `POST /api/recursos` (alta, issue #8) — se documenta acá cuando se implemente.

---

## Anexo RF2 — Reservas

### POST `/api/reservas` — Crear reserva

Requiere autenticación mediante `Authorization: Bearer <access_token>`.

### Request

```json
{
  "recurso_id": 10,
  "fecha": "2026-09-25",
  "franja": "10:00-12:00",
  "tipo": "SIMPLE"
}
```

| Campo | Tipo | Obligatorio | Notas |
|---|---|---|---|
| `recurso_id` | int | Sí | ID del recurso que se quiere reservar |
| `fecha` | string (`YYYY-MM-DD`) | Sí | Fecha de la reserva |
| `franja` | string | Sí | Máximo 30 caracteres; por ejemplo, `10:00-12:00` |
| `tipo` | enum `TipoPrestamo` | No (default `SIMPLE`) | `SIMPLE`, `POR_CURSO` o `EXCEPCIONAL`. Determina la `prioridad` de la cola (`EXCEPCIONAL`=3, `POR_CURSO`=2, `SIMPLE`=1) y se valida contra el mismo invariante tipo↔recurso de `POST /api/prestamos` (Anexo RF3): `SIMPLE` solo en `LIBRO`/`DEPORTIVO`; `POR_CURSO`/`EXCEPCIONAL` solo en `ACADEMICO` |

El backend asigna `usuario_id`, `estado`, `prioridad` y `created_at`; no se envían en el request.
`tipo` no se persiste en la fila de la reserva (la tabla `reserva` no tiene esa columna, ver `01-sdd.md` §3.3) — solo se usa para calcular `prioridad` en el momento de crearla.

### Response `201`

Devuelve un objeto `ReservaPublica`:

```json
{
  "id": 1,
  "usuario_id": 1,
  "recurso_id": 10,
  "recurso": { "id": 10, "codigo": "LIB-001", "nombre": "Clean Code", "...": "resto de RecursoPublico" },
  "fecha": "2026-09-25",
  "franja": "10:00-12:00",
  "estado": "PENDIENTE",
  "prioridad": 1,
  "created_at": "2026-09-24T15:30:00-05:00"
}
```

`recurso` es el mismo objeto `RecursoPublico` que devuelve `GET /api/recursos` (docs/02-contrato-api.md Sección 3); se incluye anidado para que el frontend no tenga que pedir el catálogo completo solo para mostrar el nombre.

`EstadoReserva`: `PENDIENTE`, `CONFIRMADA`, `CANCELADA` o `VENCIDA`.

### Errores de `POST /api/reservas`

| Código | Cuándo |
|---|---|
| `401` | Falta el token o es inválido/expiró |
| `404` | El recurso indicado no existe |
| `409` | El recurso está disponible y no requiere reserva |
| `409` | `tipo=SIMPLE` sobre un recurso `ACADEMICO`, o `POR_CURSO`/`EXCEPCIONAL` sobre uno que no lo es |
| `409` | El usuario tiene una sanción activa, según la regla del SDD |
| `422` | `tipo` con un valor fuera del enum |

La comprobación de sanciones aún está pendiente de RF5: el servicio actual tiene ese punto como TODO y todavía no bloquea reservas por sanción activa.

### GET `/api/reservas?mias=true` — Mis reservas

Requiere autenticación. El parámetro `mias` es obligatorio y debe ser `true`. Devuelve un array de objetos `ReservaPublica`, con la misma estructura de reserva del `POST`; si no hay reservas, devuelve `[]`.

| Código | Cuándo |
|---|---|
| `200` | Devuelve las reservas del usuario autenticado |
| `401` | Falta el token o es inválido/expiró |
| `403` | Se solicita `mias=false` |
| `422` | Falta `mias` o su valor no es booleano |

### DELETE `/api/reservas/{id}` — Cancelar una reserva

Requiere autenticación. Solo el dueño puede cancelar su reserva. La reserva no se elimina de la base de datos: su estado cambia a `CANCELADA`. Solo se pueden cancelar reservas en estado `PENDIENTE`.

Devuelve `204` sin cuerpo cuando la cancelación se completa.

| Código | Cuándo |
|---|---|
| `401` | Falta el token o es inválido/expiró |
| `403` | La reserva pertenece a otro usuario |
| `404` | La reserva no existe |
| `409` | La reserva no está en estado `PENDIENTE` |

---

## Anexo RF3/RF4 — Solicitudes

> **Decisión (ver `00-contexto-alcance-propuesta.md` §8, hallazgo #13):** ya no hay registro
> directo de un préstamo sin solicitud previa. Todo préstamo —incluido SIMPLE— nace de una
> `Solicitud`. El flujo normal del custodio deja de ser llamar a `POST /api/prestamos`
> directamente: llama a `POST /api/solicitudes/{id}/aceptar`, que crea el préstamo
> internamente (mismas reglas y errores que el Anexo RF3 de abajo) y lo devuelve. El endpoint
> `POST /api/prestamos` se documenta igual por si el backend lo necesita como función interna,
> pero el frontend no debe llamarlo directo para un préstamo que empezó como solicitud.

### POST `/api/solicitudes` — Crear solicitud

Requiere autenticación. Cualquier rol, sin sanción activa.

#### Request

```json
{
  "recurso_id": 10,
  "tipo_solicitud": "SIMPLE",
  "motivo": null
}
```

| Campo | Tipo | Obligatorio | Notas |
|---|---|---|---|
| `recurso_id` | int | Sí | Recurso que se quiere pedir |
| `tipo_solicitud` | enum `TipoSolicitud` | Sí | `SIMPLE`, `POR_CURSO` o `EXCEPCIONAL` |
| `motivo` | string o `null` | Solo si `tipo_solicitud != SIMPLE` | Curso/tesis/proyecto que justifica el uso académico |

El backend asigna `solicitante_id`, `estado` (inicia en `SOLICITADA`) y `created_at`.

#### Response `201`

Devuelve un objeto `SolicitudPublica`:

```json
{
  "id": 1,
  "solicitante_id": 1,
  "recurso_id": 10,
  "recurso": { "id": 10, "codigo": "LIB-001", "nombre": "Clean Code", "...": "resto de RecursoPublico" },
  "tipo_solicitud": "SIMPLE",
  "motivo": null,
  "estado": "SOLICITADA",
  "avalado_por_id": null,
  "autorizado_por_id": null,
  "aceptado_por_id": null,
  "prestamo_id": null,
  "created_at": "2026-10-22T09:00:00-05:00"
}
```

`EstadoSolicitud`: `SOLICITADA` · `AVALADA` · `AUTORIZADA` · `ACEPTADA` · `RECHAZADA`. El
camino depende de `tipo_solicitud` (ver `00-contexto-alcance-propuesta.md` §4):
`SIMPLE` va `SOLICITADA → ACEPTADA`; `POR_CURSO` va `SOLICITADA → AVALADA → ACEPTADA`;
`EXCEPCIONAL` va `SOLICITADA → AVALADA → AUTORIZADA → ACEPTADA`. `RECHAZADA` es posible
desde cualquier paso previo a `ACEPTADA`.

#### Errores

| Código | Cuándo |
|---|---|
| `401` | Falta el token o es inválido/expiró |
| `404` | `recurso_id` no existe |
| `409` | El solicitante tiene una sanción activa |
| `409` | `tipo_solicitud=SIMPLE` sobre un recurso `ACADEMICO`, o `POR_CURSO`/`EXCEPCIONAL` sobre uno que no lo es (mismo invariante tipo↔recurso del Anexo RF3) |
| `422` | Falta `motivo` con `tipo_solicitud` distinto de `SIMPLE` |

---

### GET `/api/solicitudes` — Listar solicitudes

Requiere autenticación. Dos modos, combinables con `estado`:

| Param | Tipo | Efecto |
|---|---|---|
| `mias` | boolean | `true`: solo las solicitudes del usuario autenticado (como solicitante) |
| `pendientes` | boolean | `true`: la bandeja de lo que el usuario autenticado puede resolver ahora — `DOCENTE` ve `SOLICITADA` de `POR_CURSO`/`EXCEPCIONAL`; `DIRECCION_ESCUELA` ve `AVALADA` de `EXCEPCIONAL`; `CUSTODIO_CE`/`CUSTODIO_INFRA` ven lo que ya pueden aceptar, filtrado por el `gestor` de su recurso |
| `estado` | enum `EstadoSolicitud` | Filtra por estado exacto |

Sin `mias=true` ni `pendientes=true`, un usuario sin rol de aprobación recibe `403`.

#### Response `200`

Un array de `SolicitudPublica` (`[]` si no hay coincidencias).

| Código | Cuándo |
|---|---|
| `401` | Falta el token o es inválido/expiró |
| `403` | Pide la bandeja de pendientes sin tener ningún rol de aprobación |
| `422` | `estado` no es un valor válido del enum |

---

### POST `/api/solicitudes/{id}/avalar` — Aval del docente

Requiere rol `DOCENTE`. Solo aplica a `tipo_solicitud` `POR_CURSO` o `EXCEPCIONAL` en estado `SOLICITADA`. Pasa a `AVALADA` y guarda `avalado_por_id`.

| Código | Cuándo |
|---|---|
| `401` | Falta el token o es inválido/expiró |
| `403` | El usuario no es `DOCENTE` |
| `404` | La solicitud no existe |
| `409` | La solicitud no está en `SOLICITADA`, o `tipo_solicitud=SIMPLE` (no requiere aval) |

### POST `/api/solicitudes/{id}/autorizar` — Autorización de Dirección

Requiere rol `DIRECCION_ESCUELA`. Solo aplica a `tipo_solicitud=EXCEPCIONAL` en estado `AVALADA`. Pasa a `AUTORIZADA` y guarda `autorizado_por_id`.

| Código | Cuándo |
|---|---|
| `401` | Falta el token o es inválido/expiró |
| `403` | El usuario no es `DIRECCION_ESCUELA` |
| `404` | La solicitud no existe |
| `409` | La solicitud no está en `AVALADA`, o `tipo_solicitud != EXCEPCIONAL` |

### POST `/api/solicitudes/{id}/aceptar` — Aceptación del custodio

Requiere rol `CUSTODIO_CE` (si el recurso es `LIBRO`/`DEPORTIVO`) o `CUSTODIO_INFRA` (si es `ACADEMICO`). La solicitud debe estar en el último estado antes de `ACEPTADA` según su tipo (`SOLICITADA` para SIMPLE, `AVALADA` para POR_CURSO, `AUTORIZADA` para EXCEPCIONAL).

#### Request

```json
{
  "modalidad_uso": "RETIRO_TEMPORAL",
  "condicion_entrega": "Buen estado",
  "garantia": { "tipo": "CARNET", "valor": 0 }
}
```

Mismos campos que el `POST /api/prestamos` del Anexo RF3 (sin `recurso_id`, `prestatario_id` ni `tipo_prestamo`: se toman de la solicitud). Al aceptar: pasa a `ACEPTADA`, guarda `aceptado_por_id`, **crea el `Prestamo`** (con las mismas reglas/errores del Anexo RF3) y **genera una `Notificacion`** de tipo `SOLICITUD_ACEPTADA` para el solicitante (ver Anexo de Notificaciones).

#### Response `201`

El objeto `SolicitudPublica` con `estado: "ACEPTADA"` y `prestamo_id` apuntando al `PrestamoPublico` recién creado.

| Código | Cuándo |
|---|---|
| `401` | Falta el token o es inválido/expiró |
| `403` | El usuario no tiene el rol de custodio que corresponde al `gestor` del recurso |
| `404` | La solicitud no existe |
| `409` | La solicitud no está en el estado previo esperado para su tipo |
| `409` | El recurso ya no está `DISPONIBLE` |
| `409` | (los mismos 409 de validación de `POST /api/prestamos`, Anexo RF3) |

### POST `/api/solicitudes/{id}/rechazar` — Rechazo

Requiere el rol que corresponde al paso **pendiente** de la solicitud (docente si está en `SOLICITADA` de un académico, dirección si está en `AVALADA` de un `EXCEPCIONAL`, o el custodio correspondiente en cualquier paso). Pasa a `RECHAZADA` y genera una `Notificacion` de tipo `SOLICITUD_RECHAZADA` para el solicitante.

#### Request

```json
{ "motivo_rechazo": "El equipo ya está comprometido para otro curso" }
```

| Campo | Tipo | Obligatorio |
|---|---|---|
| `motivo_rechazo` | string o `null` | No |

| Código | Cuándo |
|---|---|
| `401` | Falta el token o es inválido/expiró |
| `403` | El usuario no tiene el rol que corresponde al paso pendiente |
| `404` | La solicitud no existe |
| `409` | La solicitud ya está en `ACEPTADA` o `RECHAZADA` |

---

## Anexo — Notificaciones

Avisos **dentro de la plataforma** (no hay email ni push) generados automáticamente al
aceptar o rechazar una `Solicitud`.

### GET `/api/notificaciones` — Listar mis notificaciones

Requiere autenticación. Devuelve solo las notificaciones del usuario autenticado (no existe
un modo "de todos").

| Param | Tipo | Efecto |
|---|---|---|
| `leidas` | boolean | `?leidas=false` muestra solo las no leídas. Sin el parámetro, muestra todas |

#### Response `200`

```json
[
  {
    "id": 1,
    "usuario_id": 1,
    "solicitud_id": 7,
    "tipo": "SOLICITUD_ACEPTADA",
    "mensaje": "Tu solicitud de \"Clean Code\" fue aceptada. Preséntate en el Centro de Estudiantes antes de las 18:00 de hoy para recogerlo.",
    "leida": false,
    "created_at": "2026-10-22T09:15:00-05:00"
  }
]
```

`TipoNotificacion`: `SOLICITUD_ACEPTADA` · `SOLICITUD_RECHAZADA`. El `mensaje` lo compone el
backend; si la solicitud generó una `Reserva` en vez de un préstamo inmediato, incluye la
`fecha`/`franja` reservada en vez de "antes de las 18:00 de hoy".

| Código | Cuándo |
|---|---|
| `401` | Falta el token o es inválido/expiró |
| `422` | `leidas` no es un booleano válido |

### PATCH `/api/notificaciones/{id}` — Marcar como leída

Requiere autenticación. Solo el dueño de la notificación puede marcarla.

#### Request

```json
{ "leida": true }
```

#### Response `200`

El mismo objeto, con `leida: true`.

| Código | Cuándo |
|---|---|
| `401` | Falta el token o es inválido/expiró |
| `403` | La notificación pertenece a otro usuario |
| `404` | La notificación no existe |

---

## Anexo RF3 — `POST /api/prestamos`

Requiere autenticación con `Authorization: Bearer <access_token>` y rol `CUSTODIO_CE` o `CUSTODIO_INFRA`.

### Request

~~~json
{
  "recurso_id": 10,
  "prestatario_id": 1,
  "reserva_id": null,
  "tipo_prestamo": "SIMPLE",
  "modalidad_uso": "RETIRO_TEMPORAL",
  "condicion_entrega": "Buen estado",
  "garantia": {
    "tipo": "CARNET",
    "valor": 0
  }
}
~~~

| Campo | Tipo | Obligatorio | Notas |
|---|---|---|---|
| `recurso_id` | int | Sí | ID del recurso |
| `prestatario_id` | int | Sí | ID del usuario que recibe el préstamo |
| `reserva_id` | int o `null` | No | Reserva asociada, si corresponde |
| `fecha_limite` | string (ISO 8601) o `null` | No | Si no se manda, `prestamo_service` la calcula: DEPORTIVO vence al final del día de la entrega (préstamo del mismo día, §5 del alcance); LIBRO suma 7 días; ACADEMICO POR_CURSO suma 1 día y EXCEPCIONAL suma 3 días. Son plazos provisionales hasta que el equipo defina duraciones oficiales |
| `tipo_prestamo` | enum `TipoPrestamo` | Sí | `SIMPLE`, `POR_CURSO` o `EXCEPCIONAL` |
| `modalidad_uso` | enum `ModalidadUso` | Sí | `EN_SITIO` o `RETIRO_TEMPORAL` |
| `condicion_entrega` | string o `null` | No | Condición del recurso al entregarlo |
| `garantia` | objeto o `null` | No | Garantía asociada al préstamo |

En `garantia`, `tipo` es obligatorio y admite hasta 60 caracteres. `valor` es decimal con hasta 10 dígitos y 2 decimales; si se omite, vale `0`.

El backend asigna `registrado_por_id`, `fecha_entrega` y `estado`; y `fecha_limite` si no vino en el request. Al crear el préstamo, `estado` inicia en `ACTIVO`; `fecha_devolucion` y `condicion_devolucion` empiezan en `null`.

### Response `201`

~~~json
{
  "id": 1,
  "recurso_id": 10,
  "recurso": { "id": 10, "codigo": "LIB-001", "nombre": "Clean Code", "...": "resto de RecursoPublico" },
  "prestatario_id": 1,
  "registrado_por_id": 3,
  "reserva_id": null,
  "fecha_entrega": "2026-10-07T05:00:00Z",
  "fecha_limite": "2026-10-10T12:00:00Z",
  "fecha_devolucion": null,
  "estado": "ACTIVO",
  "tipo_prestamo": "SIMPLE",
  "modalidad_uso": "RETIRO_TEMPORAL",
  "condicion_entrega": "Buen estado",
  "condicion_devolucion": null,
  "garantia": {
    "id": 1,
    "prestamo_id": 1,
    "tipo": "CARNET",
    "valor": "0.00",
    "devuelta": false
  }
}
~~~

`recurso` es el mismo objeto `RecursoPublico` de la Sección 3, anidado. `garantia` será `null` si el préstamo no tiene una asociada. `valor` se devuelve como cadena decimal para conservar su precisión.

### Errores de `POST /api/prestamos`

| Código | Cuándo |
|---|---|
| `401` | Falta el token o es inválido/expiró |
| `403` | El usuario no es `CUSTODIO_CE` ni `CUSTODIO_INFRA` |
| `404` | `recurso_id`, `prestatario_id` o el registrador no existen |
| `409` | `registrado_por_id == prestatario_id` ("El registrador no puede ser el prestatario") |
| `409` | El recurso no está `DISPONIBLE` |
| `409` | `tipo_prestamo=SIMPLE` sobre un recurso `ACADEMICO`, o `POR_CURSO`/`EXCEPCIONAL` sobre uno que no lo es |
| `409` | `tipo_prestamo=EXCEPCIONAL` con `modalidad_uso` distinta de `RETIRO_TEMPORAL` |

---

### POST `/api/prestamos/{id}/devolucion` — Registrar devolución

Requiere autenticación con rol `CUSTODIO_CE` o `CUSTODIO_INFRA`.

#### Request

~~~json
{ "condicion_devolucion": "Buen estado, sin daños", "danado": false }
~~~

| Campo | Tipo | Obligatorio | Notas |
|---|---|---|---|
| `condicion_devolucion` | string o `null` | No | |
| `danado` | boolean | No (default `false`) | Si es `true`, el recurso pasa a `MANTENIMIENTO` en vez de `DISPONIBLE` |

Solo se pueden devolver préstamos en estado `ACTIVO` o `ATRASADO`. Al devolver, `estado` pasa a `DEVUELTO`, se completa `fecha_devolucion`, y el recurso vuelve a `DISPONIBLE` (o `MANTENIMIENTO` si `danado=true`).

#### Response `200`

Mismo objeto `PrestamoPublico` de arriba, ya con `estado: "DEVUELTO"`.

| Código | Cuándo |
|---|---|
| `401` | Falta el token o es inválido/expiró |
| `403` | El usuario no es `CUSTODIO_CE` ni `CUSTODIO_INFRA` |
| `404` | El préstamo no existe |
| `409` | El préstamo no está `ACTIVO` ni `ATRASADO` |

---

### GET `/api/prestamos` — Listar préstamos

Requiere autenticación. Dos modos, combinables:

| Param | Tipo | Efecto |
|---|---|---|
| `mios` | boolean | `true`: solo los préstamos donde el usuario autenticado es el prestatario (cualquier rol) |
| `estado` | enum `EstadoPrestamo` | Filtra por estado. Sin `mios=true`, solo lo puede usar un custodio (ve los préstamos de todos) |

Sin `mios=true`, un usuario que no sea custodio recibe `403`. `mios=true` y `estado` se pueden combinar (ej. `?mios=true&estado=ACTIVO`).

#### Response `200`

Un array de `PrestamoPublico` (`[]` si no hay coincidencias).

| Código | Cuándo |
|---|---|
| `401` | Falta el token o es inválido/expiró |
| `403` | Pide préstamos de otros usuarios (sin `mios=true`) sin ser custodio |
| `422` | `estado` no es un valor válido del enum |
