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
  "franja": "10:00-12:00"
}
```

| Campo | Tipo | Obligatorio | Notas |
|---|---|---|---|
| `recurso_id` | int | Sí | ID del recurso que se quiere reservar |
| `fecha` | string (`YYYY-MM-DD`) | Sí | Fecha de la reserva |
| `franja` | string | Sí | Máximo 30 caracteres; por ejemplo, `10:00-12:00` |

El backend asigna `usuario_id`, `estado`, `prioridad` y `created_at`; no se envían en el request.

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
| `409` | El usuario tiene una sanción activa, según la regla del SDD |

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
| `fecha_limite` | string (ISO 8601) o `null` | No | Si no se manda, `prestamo_service` (#30) la calcula según `tipo_recurso`/`tipo_prestamo`. El form del custodio (#33) no la pide |
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
