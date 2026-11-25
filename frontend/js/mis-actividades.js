// Mis Actividades: fusiona Mis Solicitudes, Mis Reservas, Mis Préstamos e
// Historial en una sola página con pestañas (antes eran 4 items de sidebar
// separados — demasiado ruido para algo que un mismo usuario revisa junto).
// Cada pestaña mantiene su propia lógica tal cual estaba en sus páginas
// originales; solo se agrega el swich de pestañas y la carga perezosa (cada
// bloque recién pide datos la primera vez que se abre su pestaña).

if (!requireAuth()) throw new Error("sin sesión");

renderSidebar("actividades");

// --- Fechas compartidas -------------------------------------------------------

// "2026-10-20" → Date en hora LOCAL. new Date("2026-10-20") la interpretaría en
// UTC y en Perú (UTC-5) mostraría el día anterior.
function parseFechaLocal(texto) {
  const [anio, mes, dia] = String(texto).slice(0, 10).split("-").map(Number);
  return new Date(anio, mes - 1, dia);
}

function formatearFecha(texto) {
  return parseFechaLocal(texto).toLocaleDateString("es-PE", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function formatearFechaConDia(texto) {
  return parseFechaLocal(texto).toLocaleDateString("es-PE", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

// --- Solicitudes (GET /solicitudes?mias=true) --------------------------------

const tablaSolicitudes = document.getElementById("mis-solicitudes");

function filaSolicitud(s) {
  const recurso = s.recurso || {};
  const tipo = ETIQUETA_TIPO_SOLICITUD[s.tipo_solicitud] || s.tipo_solicitud;
  return `<tr>
    <td><b>${esc(recurso.nombre || `Recurso #${s.recurso_id}`)}</b><div class="sub">${esc(recurso.codigo || "")}</div></td>
    <td>${esc(tipo)}</td>
    <td>${s.motivo ? esc(s.motivo) : "—"}</td>
    <td>${badgeSolicitud(s.estado)}</td>
    <td>${esc(formatearFecha(s.created_at))}</td>
  </tr>`;
}

async function cargarSolicitudes() {
  showLoading(tablaSolicitudes, 5);
  try {
    const solicitudes = await api.get("/solicitudes?mias=true");
    renderList(tablaSolicitudes, solicitudes, filaSolicitud, "Todavía no has enviado solicitudes.", 5);
  } catch (error) {
    showError(tablaSolicitudes, error.message, 5);
  }
}

// --- Reservas (GET /reservas?mias=true) ---------------------------------------

const cajaReservas = document.getElementById("reservas");
const cajaReservasError = document.getElementById("reservas-error");

function filaReserva(r) {
  const nombre = r.recurso ? r.recurso.nombre : "Recurso sin datos";
  const codigo = r.recurso ? r.recurso.codigo : "";

  // Solo una reserva PENDIENTE tiene sentido cancelarla: CONFIRMADA ya se
  // convirtió en préstamo; CANCELADA y VENCIDA ya terminaron.
  const botonCancelar =
    r.estado === "PENDIENTE"
      ? `<button type="button" class="btn btn-danger-ghost btn-sm btn-cancelar" data-id="${esc(r.id)}">Cancelar</button>`
      : "—";

  return `
    <tr data-reserva-id="${esc(r.id)}">
      <td><b>${esc(nombre)}</b><div class="sub">${esc(codigo)}</div></td>
      <td>${esc(formatearFechaConDia(r.fecha))} · ${esc(r.franja)}</td>
      <td>${badgeReserva(r.estado)}</td>
      <td>${botonCancelar}</td>
    </tr>`;
}

async function cargarReservas() {
  showFormError(cajaReservasError, null);
  showLoading(cajaReservas, 4);
  try {
    const reservas = await api.get("/reservas?mias=true");
    renderList(cajaReservas, reservas, filaReserva, "No tienes reservas", 4);
  } catch (e) {
    showError(cajaReservas, e.message, 4);
  }
}

// Un solo listener para todos los botones (las filas se pintan con innerHTML).
cajaReservas.addEventListener("click", async (evento) => {
  const boton = evento.target.closest(".btn-cancelar");
  if (!boton) return;

  if (!confirm("¿Seguro que quieres cancelar esta reserva?")) return;

  showFormError(cajaReservasError, null);
  setBusy(boton, true, "Cancelando…");

  try {
    await api.del(`/reservas/${boton.dataset.id}`);
    boton.closest("tr").remove();
    if (!cajaReservas.querySelector("tr")) showEmpty(cajaReservas, "No tienes reservas", 4);
  } catch (e) {
    showFormError(cajaReservasError, e.message);
    setBusy(boton, false);
  }
});

// --- Préstamos (GET /prestamos?mios=true) -------------------------------------
//
// Pantalla de SOLO LECTURA: no hay botón de devolver. La devolución la registra
// el custodio.

const cajaPrestamos = document.getElementById("prestamos");
const cajaComprobante = document.getElementById("comprobante");

// Días de anticipación desde los que se resalta un préstamo ACTIVO.
const DIAS_ALERTA = 2;

// Días que faltan para la fecha límite (negativo = ya pasó). Compara días
// calendario locales, sin horas.
function diasHasta(texto) {
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);
  return Math.round((parseFechaLocal(texto) - hoy) / 86400000);
}

// Devuelve el texto de aviso si el préstamo hay que resaltarlo, o null si no.
function avisoVencimiento(p) {
  if (p.estado === "DEVUELTO") return null;

  const dias = diasHasta(p.fecha_limite);

  // ATRASADO: siempre se resalta. ACTIVO: solo si le quedan menos de 2 días
  // (incluye los ya vencidos que el backend todavía no marcó como ATRASADO).
  if (p.estado !== "ATRASADO" && dias >= DIAS_ALERTA) return null;

  if (dias < -1) return `Venció hace ${-dias} días`;
  if (dias === -1) return "Venció ayer";
  if (dias === 0) return "Vence hoy";
  if (dias === 1) return "Vence mañana";
  return null; // ATRASADO con fecha aún futura: solo se resalta, sin texto extra
}

function tarjetaPrestamo(p) {
  const nombre = p.recurso ? p.recurso.nombre : "Recurso sin datos";
  const codigo = p.recurso ? p.recurso.codigo : "";

  const aviso = avisoVencimiento(p);
  const resaltar = aviso !== null || p.estado === "ATRASADO";

  return `
    <div class="loan${resaltar ? " alert" : ""}" data-id="${esc(p.id)}">
      <div>
        <div class="t">${esc(nombre)}</div>
        <div class="s">${esc(codigo)}</div>
        <div class="dates">${esc(formatearFecha(p.fecha_entrega))} → <b>${esc(formatearFecha(p.fecha_limite))}</b></div>
        ${aviso ? `<div class="warn-text">${esc(aviso)}</div>` : ""}
      </div>
      ${badgePrestamo(p.estado)}
    </div>`;
}

const ETIQUETA_MODALIDAD = {
  EN_SITIO: "En sitio",
  RETIRO_TEMPORAL: "Retiro temporal",
};

function comprobante(p) {
  const nombre = p.recurso ? p.recurso.nombre : "Recurso sin datos";
  const garantia = p.garantia ? `${esc(p.garantia.tipo)} (S/ ${esc(p.garantia.valor)})` : "—";

  return `
    <div class="ticket">
      <div class="fila"><span>Préstamo</span><b>#${esc(p.id)} · ${esc(nombre)}</b></div>
      <div class="fila"><span>Registrado por</span><b>Usuario #${esc(p.registrado_por_id)}</b></div>
      <div class="fila"><span>Garantía</span><b>${garantia}</b></div>
      <div class="fila"><span>Modalidad</span><b>${esc(ETIQUETA_MODALIDAD[p.modalidad_uso] || p.modalidad_uso)}</b></div>
      <div class="perf"></div>
      <div class="fila"><span>Entregado</span><b>${esc(formatearFecha(p.fecha_entrega))}</b></div>
      <div class="fila"><span>Vence</span><b style="color:var(--warn)">${esc(formatearFecha(p.fecha_limite))}</b></div>
      ${p.fecha_devolucion ? `<div class="fila"><span>Devuelto</span><b>${esc(formatearFecha(p.fecha_devolucion))}</b></div>` : ""}
    </div>`;
}

let prestamos = [];

function mostrarComprobante(id) {
  const p = prestamos.find((x) => String(x.id) === String(id));
  cajaComprobante.innerHTML = p ? comprobante(p) : "";
  cajaPrestamos.querySelectorAll(".loan").forEach((el) => {
    el.classList.toggle("seleccionado", el.dataset.id === String(id));
  });
}

async function cargarPrestamos() {
  showLoading(cajaPrestamos);
  try {
    prestamos = await api.get("/prestamos?mios=true");
    renderList(cajaPrestamos, prestamos, tarjetaPrestamo, "No tienes préstamos");
    if (prestamos.length > 0) mostrarComprobante(prestamos[0].id);
  } catch (e) {
    showError(cajaPrestamos, e.message);
  }
}

cajaPrestamos.addEventListener("click", (evento) => {
  const tarjeta = evento.target.closest(".loan");
  if (tarjeta) mostrarComprobante(tarjeta.dataset.id);
});

// --- Historial (GET /historial) -----------------------------------------------
//
// Siempre el propio: ver el historial de otro usuario es una consulta
// administrativa (Reportes > Incidencias > "Ver historial", en un modal),
// no "mi actividad" — no tiene cabida acá. Contrato: docs/02-contrato-api.md,
// Anexo RF6.

document.getElementById("historial-subtitulo").textContent =
  "Lo que pediste, cuándo, y si lo devolviste a tiempo.";

const LIMITE_HISTORIAL = 10;
let offsetHistorial = 0;

const campoEstado = document.getElementById("historial-estado");
const mensajeHistorial = document.getElementById("mensaje-historial");
const tablaHistorial = document.getElementById("historial-tabla");
const paginacionHistorial = document.getElementById("historial-paginacion");
const btnHistorialAnterior = document.getElementById("btn-historial-anterior");
const btnHistorialSiguiente = document.getElementById("btn-historial-siguiente");

function mostrarMensajeHistorial(texto) {
  mensajeHistorial.className = "alert-danger";
  mensajeHistorial.textContent = texto;
  mensajeHistorial.hidden = !texto;
}

function filaHistorial(item) {
  return `<tr>
    <td>${esc(item.recurso.nombre)} <span class="hint">${esc(item.recurso.codigo)}</span></td>
    <td>${esc(ETIQUETA_TIPO_SOLICITUD[item.tipo_prestamo] || item.tipo_prestamo)}</td>
    <td>${esc(formatearFecha(item.fecha_entrega))}</td>
    <td>${esc(formatearFecha(item.fecha_limite))}</td>
    <td>${badgePrestamo(item.estado)}</td>
    <td>${item.dias_atraso > 0 ? `<span class="badge danger">${esc(item.dias_atraso)} días</span>` : "—"}</td>
  </tr>`;
}

async function cargarHistorial() {
  mostrarMensajeHistorial("");
  showLoading(tablaHistorial, 6);

  const params = new URLSearchParams({ limite: LIMITE_HISTORIAL, offset: offsetHistorial });
  if (campoEstado.value) params.set("estado", campoEstado.value);

  try {
    const r = await api.get(`/historial?${params}`);
    renderList(tablaHistorial, r.items, filaHistorial, "No hay préstamos para mostrar.", 6);
    const desde = r.total === 0 ? 0 : r.offset + 1;
    const hasta = Math.min(r.offset + r.limite, r.total);
    paginacionHistorial.textContent = `${desde}–${hasta} de ${r.total}`;
    btnHistorialAnterior.disabled = r.offset <= 0;
    btnHistorialSiguiente.disabled = r.offset + r.limite >= r.total;
  } catch (e) {
    showError(tablaHistorial, e.message, 6);
    mostrarMensajeHistorial(e.message);
    paginacionHistorial.textContent = "";
  }
}

document.getElementById("btn-buscar-historial").addEventListener("click", () => {
  offsetHistorial = 0;
  cargarHistorial();
});
campoEstado.addEventListener("change", () => {
  offsetHistorial = 0;
  cargarHistorial();
});
btnHistorialAnterior.addEventListener("click", () => {
  offsetHistorial = Math.max(offsetHistorial - LIMITE_HISTORIAL, 0);
  cargarHistorial();
});
btnHistorialSiguiente.addEventListener("click", () => {
  offsetHistorial += LIMITE_HISTORIAL;
  cargarHistorial();
});

// --- Pestañas ------------------------------------------------------------------

const TABS = ["solicitudes", "reservas", "prestamos", "historial"];
const CARGAR_TAB = {
  solicitudes: cargarSolicitudes,
  reservas: cargarReservas,
  prestamos: cargarPrestamos,
  historial: cargarHistorial,
};
const tabsCargadas = new Set();

function mostrarTab(tab) {
  TABS.forEach((t) => {
    document.getElementById(`panel-${t}`).hidden = t !== tab;
  });
  document.querySelectorAll("#tabs .tab").forEach((boton) => {
    boton.classList.toggle("active", boton.dataset.tab === tab);
  });

  // Carga perezosa: cada bloque recién pide datos la primera vez que se abre.
  if (!tabsCargadas.has(tab)) {
    tabsCargadas.add(tab);
    CARGAR_TAB[tab]();
  }

  // Refleja la pestaña activa en la URL sin recargar, para que
  // volver/compartir el link funcione bien.
  const params = new URLSearchParams(location.search);
  params.set("tab", tab);
  history.replaceState(null, "", `${location.pathname}?${params}`);
}

document.getElementById("tabs").addEventListener("click", (evento) => {
  const boton = evento.target.closest(".tab");
  if (boton) mostrarTab(boton.dataset.tab);
});

const tabParam = new URLSearchParams(location.search).get("tab");
const tabInicial = TABS.includes(tabParam) ? tabParam : "solicitudes";
mostrarTab(tabInicial);
