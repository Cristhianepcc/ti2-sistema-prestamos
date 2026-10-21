# Frontend — cómo usar los helpers

Guía de uso de `js/api.js` y `js/render.js` (issue #5). La idea es que las páginas
solo tengan HTML y unas pocas líneas de lógica: todo lo repetitivo (token, errores,
estados de carga) ya está resuelto acá.

- Formas exactas de request y response: [`../docs/02-contrato-api.md`](../docs/02-contrato-api.md)
- Antes de empezar: levantá la API (`docker compose up --build`) y cargá los datos
  de ejemplo (`docker compose exec api python -m app.seeds`).

---

## 1. Estructura de una página

Cargá siempre los dos scripts antes de tu lógica:

```html
<script src="js/api.js"></script>
<script src="js/render.js"></script>
<script src="js/catalogo.js"></script>   <!-- la lógica de tu página -->
```

---

## 2. Login (issue #13 / #14)

```html
<form id="form-login">
  <div id="login-error" class="alert-danger" hidden></div>

  <label class="field">Correo institucional
    <input id="email" name="email" type="email" required>
  </label>
  <label class="field">Contraseña
    <input id="password" name="password" type="password" required>
  </label>

  <button id="btn-entrar" class="btn btn-primary btn-block" type="submit">Entrar</button>
</form>
```

> No hay Bootstrap: las clases vienen de `css/styles.css` (ver `.field`, `.btn`,
> `.alert-danger`, etc.). Los estados que se ocultan/muestran usan el atributo
> `hidden`, no una clase `d-none`.

```js
const form = document.getElementById("form-login");
const cajaError = document.getElementById("login-error");
const boton = document.getElementById("btn-entrar");

form.addEventListener("submit", async (evento) => {
  evento.preventDefault();          // sin esto la página se recarga
  showFormError(cajaError, null);   // limpia el error anterior
  setBusy(boton, true, "Entrando…");

  const { email, password } = formValues(form);

  try {
    const usuario = await api.login(email, password);
    // Sesión guardada. Redirigí según el rol si hace falta:
    location.href = "catalogo.html";
  } catch (e) {
    // e.message trae el mensaje del backend: "Credenciales inválidas",
    // "Usuario inactivo", o "Revisá los datos del formulario." en un 422.
    showFormError(cajaError, e.message);
  } finally {
    setBusy(boton, false);
  }
});
```

> **Importante:** el login fallido devuelve `401`, pero `api.login()` **no** redirige
> ni borra la sesión — te deja mostrar el mensaje. La redirección automática al login
> solo ocurre en llamadas que van con token (o sea, sesión realmente vencida).

---

## 3. Catálogo (issue #10 / #11)

```html
<div class="app">
  <aside class="app-sidebar" id="app-sidebar"></aside>
  <div class="app-main">
    <div id="catalogo"></div>
  </div>
</div>
```

```js
if (!requireAuth()) throw new Error("sin sesión");  // corta si no hay token

renderSidebar("catalogo");  // pinta el sidebar y resalta el item activo (js/shell.js)

const caja = document.getElementById("catalogo");

async function cargarCatalogo(filtros = "") {
  showLoading(caja);
  try {
    const recursos = await api.get(`/recursos${filtros}`);
    renderList(caja, recursos, tarjetaRecurso, "No hay recursos que coincidan.");
  } catch (e) {
    showError(caja, e.message);
  }
}

function tarjetaRecurso(r) {
  return `
    <div class="tarjeta">
      <div class="cuerpo">
        <div class="nombre">${esc(r.nombre)}</div>
        ${badgeEstado(r.estado)}
        <p class="detalle">${esc(ETIQUETA_TIPO[r.tipo_recurso])} · ${esc(r.codigo)}</p>
        ${detalleSegunTipo(r)}
      </div>
    </div>`;
}

// ⚠️ Las claves de un subtipo NO existen en los otros: un DEPORTIVO no trae la
// clave `autor` ni siquiera en null. Ramificá por tipo_recurso.
function detalleSegunTipo(r) {
  if (r.tipo_recurso === "LIBRO") {
    return `<p class="small mb-0">${esc(r.autor)} · ISBN ${esc(r.isbn)}</p>`;
  }
  if (r.tipo_recurso === "DEPORTIVO") {
    return `<p class="small mb-0">${esc(r.tipo_deportivo)}</p>`;
  }
  return `<p class="small mb-0">Patrimonio ${esc(r.codigo_patrimonial)}
          ${r.requiere_aval ? "· requiere aval" : ""}</p>`;
}

cargarCatalogo("?disponible=true");
```

Filtros disponibles (se combinan): `?tipo=LIBRO`, `?estado=PRESTADO`,
`?disponible=true`, `?q=clean`.

---

## 4. Referencia rápida

### `api.js`

| Función | Qué hace |
|---|---|
| `api.login(email, password)` | Login + guarda la sesión. Devuelve el usuario |
| `api.logout()` | Borra la sesión y vuelve al login |
| `api.me()` | Revalida la sesión contra el backend |
| `api.get(ruta)` | GET con el token puesto |
| `api.post(ruta, cuerpo)` | POST con el token puesto |
| `api.put` · `api.patch` · `api.del` | Ídem para los otros métodos |
| `requireAuth()` | Al inicio de una página protegida: redirige al login si no hay token |
| `currentUser()` | El usuario guardado: `{ id, codigo, nombres, email, roles }` |
| `hasRole("CUSTODIO_CE", ...)` | `true` si tiene alguno de esos roles |

Todos los métodos lanzan `ApiError` con `.status` (el código HTTP) y `.message`
(el mensaje del backend). Para ramificar:

```js
try {
  await api.post("/recursos", nuevo);
} catch (e) {
  if (e.status === 403) showError(caja, "No tenés permiso para dar de alta recursos.");
  else showError(caja, e.message);
}
```

`e.status === 0` significa que no se pudo contactar a la API (caída o CORS).

### `render.js`

| Función | Qué hace |
|---|---|
| `esc(texto)` | Escapa texto de la API antes de meterlo en `innerHTML`. **Usalo siempre** |
| `showLoading(el, colspan?)` | Spinner de carga |
| `showError(el, msg, colspan?)` | Alerta roja |
| `showEmpty(el, msg, colspan?)` | Mensaje de "no hay datos" |
| `renderList(el, items, fn, vacío, colspan?)` | Pinta una lista; si está vacía muestra el mensaje |
| `formValues(form)` | Los campos del form como objeto |
| `setBusy(boton, true/false)` | Deshabilita el botón con spinner mientras se envía |
| `showFormError(el, msg)` | Muestra el error del form (usa `el.hidden`); con `null` lo oculta |
| `badgeEstado` · `badgeReserva` · `badgePrestamo` | Badge de color (`ok`/`warn`/`danger`/`neutral`) según el estado |
| `ETIQUETA_TIPO` · `ETIQUETA_ROL` · `ETIQUETA_ESTADO` · `ETIQUETA_RESERVA` · `ETIQUETA_PRESTAMO` | Enum → texto legible en español |

> El parámetro `colspan` es solo para cuando `el` es un `<tbody>` (una lista en
> forma de tabla, como "Mis Reservas" o el Panel Custodio): envuelve el mensaje
> en una fila con `colspan` para no romper la tabla. Omitilo en listas normales.

### `shell.js`

| Función | Qué hace |
|---|---|
| `renderSidebar(activa)` | Pinta el sidebar de navegación en `#app-sidebar` y resalta el item `activa` (`"catalogo"`, `"reservas"`, `"prestamos"` o `"custodio"`). Incluye el botón de cerrar sesión. Llamalo una vez al cargar cualquier página con sesión |

El Panel Custodio solo aparece en el sidebar para `CUSTODIO_CE`/`CUSTODIO_INFRA`
(usa `hasRole()` internamente) — no hace falta ocultarlo a mano.

---

## 5. Si algo no funciona

| Síntoma | Causa probable |
|---|---|
| `e.status === 0` o "No se pudo conectar" | La API no está corriendo, o tu puerto no está en `CORS_ORIGINS` |
| El catálogo llega vacío | Faltan los seeds: `docker compose exec api python -m app.seeds` |
| Te saca al login todo el tiempo | El token venció (dura 8 h). Volvé a entrar |
| La API arranca pero el login tira error 500 | Imagen vieja: `docker compose up --build` |
