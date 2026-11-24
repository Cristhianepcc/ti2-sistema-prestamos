// Historial de préstamos (RF6): cualquier usuario ve el suyo; el
// ADMINISTRADOR_SISTEMA además puede consultar el de otro por su código.
// Contrato: docs/02-contrato-api.md, Anexo RF6 — GET /api/historial.

if (!requireAuth()) throw new Error("sin sesión");

renderSidebar("historial");

const esAdmin = hasRole("ADMINISTRADOR_SISTEMA");

document.getElementById("historial-subtitulo").textContent = esAdmin
  ? "Tu historial de préstamos. Como administrador, también puedes consultar el de otro usuario por su código."
  : "Lo que pediste, cuándo, y si lo devolviste a tiempo.";
if (esAdmin) document.getElementById("campo-usuario-codigo").hidden = false;

// Deep link desde Reportes > Incidencias ("Ver historial" de un atrasado):
// ?codigo=X precarga la búsqueda en vez de mostrar el historial propio.
const codigoPrecargado = esAdmin ? new URLSearchParams(location.search).get("codigo") : null;

// --- Fechas -------------------------------------------------------------------

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

// --- Elementos -----------------------------------------------------------------

const LIMITE = 10;
let offset = 0;

const campoUsuarioCodigo = document.getElementById("historial-usuario-codigo");
const campoEstado = document.getElementById("historial-estado");
const mensaje = document.getElementById("mensaje-historial");
const tabla = document.getElementById("historial-tabla");
const paginacion = document.getElementById("historial-paginacion");
const btnAnterior = document.getElementById("btn-historial-anterior");
const btnSiguiente = document.getElementById("btn-historial-siguiente");

if (codigoPrecargado) campoUsuarioCodigo.value = codigoPrecargado;

function mostrarMensaje(texto) {
  mensaje.className = "alert-danger";
  mensaje.textContent = texto;
  mensaje.hidden = !texto;
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
  mostrarMensaje("");
  showLoading(tabla, 6);

  const params = new URLSearchParams({ limite: LIMITE, offset });
  if (campoEstado.value) params.set("estado", campoEstado.value);
  if (esAdmin && campoUsuarioCodigo.value.trim()) params.set("codigo", campoUsuarioCodigo.value.trim());

  try {
    const r = await api.get(`/historial?${params}`);
    renderList(tabla, r.items, filaHistorial, "No hay préstamos para mostrar.", 6);
    const desde = r.total === 0 ? 0 : r.offset + 1;
    const hasta = Math.min(r.offset + r.limite, r.total);
    paginacion.textContent = `${desde}–${hasta} de ${r.total}`;
    btnAnterior.disabled = r.offset <= 0;
    btnSiguiente.disabled = r.offset + r.limite >= r.total;
  } catch (e) {
    showError(tabla, e.message, 6);
    mostrarMensaje(e.message);
    paginacion.textContent = "";
  }
}

document.getElementById("btn-buscar-historial").addEventListener("click", () => {
  offset = 0;
  cargarHistorial();
});
campoEstado.addEventListener("change", () => {
  offset = 0;
  cargarHistorial();
});
btnAnterior.addEventListener("click", () => {
  offset = Math.max(offset - LIMITE, 0);
  cargarHistorial();
});
btnSiguiente.addEventListener("click", () => {
  offset += LIMITE;
  cargarHistorial();
});

cargarHistorial();
