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

// `colspan`: si `el` es un <tbody> (lista en forma de tabla), envuelve el
// contenido en una fila con una sola celda que abarca todas las columnas.
function envolverSiEsTabla(el, html, colspan) {
  return colspan ? `<tr><td colspan="${colspan}">${html}</td></tr>` : html;
}

function showLoading(el, colspan) {
  el.innerHTML = envolverSiEsTabla(
    el,
    `<div class="estado-carga"><div class="spinner" role="status"></div><p>Cargando…</p></div>`,
    colspan
  );
}

function showError(el, msg, colspan) {
  el.innerHTML = envolverSiEsTabla(el, `<div class="alert-danger" role="alert">${esc(msg)}</div>`, colspan);
}

function showEmpty(el, msg = "No hay datos.", colspan) {
  el.innerHTML = envolverSiEsTabla(el, `<div class="estado-vacio">${esc(msg)}</div>`, colspan);
}

// Renderiza una lista usando una función que devuelve el HTML de cada item.
function renderList(el, items, itemHtml, emptyMsg, colspan) {
  if (!items || items.length === 0) return showEmpty(el, emptyMsg, colspan);
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
    boton.innerHTML = `<span class="spinner" style="width:14px;height:14px;border-width:2px;margin:0;"></span>${esc(textoOcupado)}`;
  } else {
    boton.disabled = false;
    if (boton.dataset.textoOriginal) boton.innerHTML = boton.dataset.textoOriginal;
  }
}

// Muestra u oculta el mensaje de error de un formulario.
function showFormError(el, msg) {
  if (!msg) {
    el.hidden = true;
    el.textContent = "";
    return;
  }
  el.hidden = false;
  el.className = "alert-danger";
  el.textContent = msg; // textContent ya escapa, no hace falta esc()
}

// --- Etiquetas del dominio --------------------------------------------------

// Los enums viajan en MAYÚSCULAS (ver docs/02-contrato-api.md §4); acá se
// traducen a algo legible y a un tono de badge del design system (ok/warn/danger/neutral).
const ETIQUETA_ESTADO = {
  DISPONIBLE: { texto: "Disponible", color: "ok" },
  RESERVADO: { texto: "Reservado", color: "warn" },
  PRESTADO: { texto: "Prestado", color: "neutral" },
  MANTENIMIENTO: { texto: "En mantenimiento", color: "danger" },
};

// Estados de una RESERVA (no confundir con ETIQUETA_ESTADO, que es del recurso).
const ETIQUETA_RESERVA = {
  PENDIENTE: { texto: "Pendiente", color: "warn" },
  CONFIRMADA: { texto: "Confirmada", color: "ok" },
  CANCELADA: { texto: "Cancelada", color: "neutral" },
  VENCIDA: { texto: "Vencida", color: "danger" },
};

function badgeReserva(estado) {
  const e = ETIQUETA_RESERVA[estado] || { texto: estado, color: "neutral" };
  return `<span class="badge ${e.color}">${esc(e.texto)}</span>`;
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
  ACTIVO: { texto: "Activo", color: "ok" },
  DEVUELTO: { texto: "Devuelto", color: "neutral" },
  ATRASADO: { texto: "Atrasado", color: "danger" },
};

function badgePrestamo(estado) {
  const e = ETIQUETA_PRESTAMO[estado] || { texto: estado, color: "neutral" };
  return `<span class="badge ${e.color}">${esc(e.texto)}</span>`;
}

function badgeEstado(estado) {
  const e = ETIQUETA_ESTADO[estado] || { texto: estado, color: "neutral" };
  return `<span class="badge ${e.color}">${esc(e.texto)}</span>`;
}
