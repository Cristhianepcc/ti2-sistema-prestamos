// Helpers de render (issue #5) — para pintar estados, listas y formularios
// sin repetir código. Ejemplos de uso en frontend/README.md.

// Escapa texto que viene de la API antes de meterlo en innerHTML.
// Usalo SIEMPRE con datos del servidor: un nombre de recurso con < o & rompe
// el HTML, y en el peor caso permite inyectar etiquetas.
function esc(texto) {
  if (texto === null || texto === undefined) return "";
  return String(texto)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

// --- Estados de una zona de la página ---------------------------------------

function showLoading(el) {
  el.innerHTML = `<div class="text-center text-muted py-4">
    <div class="spinner-border" role="status"></div>
    <div class="mt-2">Cargando…</div></div>`;
}

function showError(el, msg) {
  el.innerHTML = `<div class="alert alert-danger" role="alert">${esc(msg)}</div>`;
}

function showEmpty(el, msg = "No hay datos.") {
  el.innerHTML = `<div class="text-center text-muted py-4">${esc(msg)}</div>`;
}

// Renderiza una lista usando una función que devuelve el HTML de cada item.
function renderList(el, items, itemHtml, emptyMsg) {
  if (!items || items.length === 0) return showEmpty(el, emptyMsg);
  el.innerHTML = items.map(itemHtml).join("");
}

// --- Formularios ------------------------------------------------------------

// Devuelve los valores de un <form> como objeto: { email: "...", password: "..." }
// Cada campo necesita su atributo name.
function formValues(form) {
  return Object.fromEntries(new FormData(form).entries());
}

// Deshabilita el botón y le pone un spinner mientras se envía el formulario,
// para que no se pueda hacer doble submit.
function setBusy(boton, busy, textoOcupado = "Enviando…") {
  if (busy) {
    boton.dataset.textoOriginal = boton.innerHTML;
    boton.disabled = true;
    boton.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>${esc(textoOcupado)}`;
  } else {
    boton.disabled = false;
    if (boton.dataset.textoOriginal) boton.innerHTML = boton.dataset.textoOriginal;
  }
}

// Muestra u oculta el mensaje de error de un formulario.
function showFormError(el, msg) {
  if (!msg) {
    el.classList.add("d-none");
    el.textContent = "";
    return;
  }
  el.className = "alert alert-danger";
  el.textContent = msg; // textContent ya escapa, no hace falta esc()
}

// --- Etiquetas del dominio --------------------------------------------------

// Los enums viajan en MAYÚSCULAS (ver docs/02-contrato-api.md §4); acá se
// traducen a algo legible y a un color de badge de Bootstrap.
const ETIQUETA_ESTADO = {
  DISPONIBLE: { texto: "Disponible", color: "success" },
  RESERVADO: { texto: "Reservado", color: "warning" },
  PRESTADO: { texto: "Prestado", color: "secondary" },
  MANTENIMIENTO: { texto: "En mantenimiento", color: "danger" },
};

// Estados de una RESERVA (no confundir con ETIQUETA_ESTADO, que es del recurso).
const ETIQUETA_RESERVA = {
  PENDIENTE: { texto: "Pendiente", color: "warning" },
  CONFIRMADA: { texto: "Confirmada", color: "success" },
  CANCELADA: { texto: "Cancelada", color: "secondary" },
  VENCIDA: { texto: "Vencida", color: "danger" },
};

function badgeReserva(estado) {
  const e = ETIQUETA_RESERVA[estado] || { texto: estado, color: "light" };
  return `<span class="badge text-bg-${e.color}">${esc(e.texto)}</span>`;
}

const ETIQUETA_TIPO = {
  LIBRO: "Libro",
  DEPORTIVO: "Implemento deportivo",
  ACADEMICO: "Implemento académico",
};

const ETIQUETA_ROL = {
  ESTUDIANTE: "Estudiante",
  DOCENTE: "Docente",
  CUSTODIO_CE: "Custodio del Centro de Estudiantes",
  CUSTODIO_INFRA: "Custodio de Infraestructura",
  DIRECCION_ESCUELA: "Dirección de Escuela",
  ADMINISTRADOR_SISTEMA: "Administrador del sistema",
};

// Estados de un PRÉSTAMO (no confundir con ETIQUETA_ESTADO, que es del recurso).
const ETIQUETA_PRESTAMO = {
  ACTIVO: { texto: "Activo", color: "info" },
  DEVUELTO: { texto: "Devuelto", color: "secondary" },
  ATRASADO: { texto: "Atrasado", color: "danger" },
};

function badgePrestamo(estado) {
  const e = ETIQUETA_PRESTAMO[estado] || { texto: estado, color: "light" };
  return `<span class="badge text-bg-${e.color}">${esc(e.texto)}</span>`;
}

function badgeEstado(estado) {
  const e = ETIQUETA_ESTADO[estado] || { texto: estado, color: "light" };
  return `<span class="badge text-bg-${e.color}">${esc(e.texto)}</span>`;
}
