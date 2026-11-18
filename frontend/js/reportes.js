// Reportes (RF6, nivel 1): inventario y préstamos de solo lectura, más el
// historial por usuario. Solo ADMINISTRADOR_SISTEMA (el backend aplica la
// misma regla; ver docs/02-contrato-api.md, Anexo RF6).

if (!requireAuth()) throw new Error("sin sesión");

if (!hasRole("ADMINISTRADOR_SISTEMA")) {
  location.href = "inicio.html";
  throw new Error("solo administradores del sistema");
}

renderSidebar("reportes");

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

// --- Stats ---------------------------------------------------------------------

function statHTML(n, l, color) {
  const style = color ? ` style="color:var(--${color})"` : "";
  return `<div class="stat"><div class="n"${style}>${esc(n)}</div><div class="l">${esc(l)}</div></div>`;
}

// --- Inventario ------------------------------------------------------------------

const inventarioStats = document.getElementById("inventario-stats");
const inventarioTabla = document.getElementById("inventario-tabla");

function filaInventario(tipo, porTipoEstado) {
  const fila = porTipoEstado[tipo] || {};
  return `<tr>
    <td>${esc(ETIQUETA_TIPO[tipo] || tipo)}</td>
    <td>${esc(fila.DISPONIBLE || 0)}</td>
    <td>${esc(fila.RESERVADO || 0)}</td>
    <td>${esc(fila.PRESTADO || 0)}</td>
    <td>${esc(fila.MANTENIMIENTO || 0)}</td>
  </tr>`;
}

async function cargarInventario() {
  showLoading(inventarioStats);
  showLoading(inventarioTabla, 5);
  try {
    const r = await api.get("/reportes/inventario");
    inventarioStats.innerHTML = [
      statHTML(r.total_recursos, "Recursos en total"),
      statHTML(r.por_estado.DISPONIBLE || 0, "Disponibles"),
      statHTML(r.por_estado.PRESTADO || 0, "Prestados"),
      statHTML(
        r.por_estado.MANTENIMIENTO || 0,
        "En mantenimiento",
        r.por_estado.MANTENIMIENTO ? "danger" : undefined
      ),
    ].join("");

    inventarioTabla.innerHTML = Object.keys(ETIQUETA_TIPO)
      .map((tipo) => filaInventario(tipo, r.tipo_por_estado))
      .join("");
  } catch (e) {
    showError(inventarioStats, e.message);
    showError(inventarioTabla, e.message, 5);
  }
}

// --- Préstamos ---------------------------------------------------------------------

const prestamosStats = document.getElementById("prestamos-stats");
const masPrestados = document.getElementById("mas-prestados");
const garantiasEl = document.getElementById("garantias");
const atrasadosTabla = document.getElementById("atrasados-tabla");
const atrasadosNota = document.getElementById("atrasados-nota");
const filtroDesde = document.getElementById("filtro-desde");
const filtroHasta = document.getElementById("filtro-hasta");

function filaAtrasado(item) {
  return `<tr>
    <td>${esc(item.recurso.nombre)} <span class="hint">${esc(item.recurso.codigo)}</span></td>
    <td>${esc(item.prestatario.nombres)} <span class="hint">${esc(item.prestatario.codigo)}</span></td>
    <td>${esc(formatearFecha(item.fecha_limite))}</td>
    <td><span class="badge danger">${esc(item.dias_atraso)} días</span></td>
  </tr>`;
}

async function cargarPrestamos() {
  showLoading(prestamosStats);
  showLoading(masPrestados);
  showLoading(garantiasEl);
  showLoading(atrasadosTabla, 4);
  atrasadosNota.textContent = "";

  const params = new URLSearchParams();
  if (filtroDesde.value) params.set("desde", filtroDesde.value);
  if (filtroHasta.value) params.set("hasta", filtroHasta.value);
  const query = params.toString() ? `?${params}` : "";

  try {
    const r = await api.get(`/reportes/prestamos${query}`);
    prestamosStats.innerHTML = [
      statHTML(r.total_prestamos, "Préstamos en el periodo"),
      statHTML(r.por_estado.ACTIVO || 0, "Activos"),
      statHTML(
        r.por_estado.ATRASADO || 0,
        "Atrasados",
        r.por_estado.ATRASADO ? "danger" : undefined
      ),
      statHTML(r.por_estado.DEVUELTO || 0, "Devueltos"),
    ].join("");

    renderList(
      masPrestados,
      r.mas_prestados,
      (item) =>
        `<div class="mini-row"><div><div class="t">${esc(item.nombre)}</div><div class="s">${esc(item.codigo)}</div></div><b>${esc(item.total)}</b></div>`,
      "Sin préstamos en este periodo."
    );

    garantiasEl.innerHTML = `
      <div class="mini-row"><div><div class="t">Garantías retenidas</div></div><b>${esc(r.garantias.retenidas)}</b></div>
      <div class="mini-row"><div><div class="t">Valor retenido</div></div><b>S/ ${esc(r.garantias.valor_retenido)}</b></div>`;

    renderList(atrasadosTabla, r.atrasados.items, filaAtrasado, "No hay préstamos atrasados.", 4);
    atrasadosNota.textContent =
      r.atrasados.total > r.atrasados.items.length
        ? `Mostrando los ${r.atrasados.items.length} más urgentes de ${r.atrasados.total} atrasados en total.`
        : "";
  } catch (e) {
    showError(prestamosStats, e.message);
    showError(masPrestados, e.message);
    showError(garantiasEl, e.message);
    showError(atrasadosTabla, e.message, 4);
  }
}

document.getElementById("btn-aplicar-filtro").addEventListener("click", cargarPrestamos);
document.getElementById("btn-limpiar-filtro").addEventListener("click", () => {
  filtroDesde.value = "";
  filtroHasta.value = "";
  cargarPrestamos();
});

// --- Historial por usuario -------------------------------------------------------------

const LIMITE_HISTORIAL = 10;
let historialOffset = 0;

const historialUsuarioId = document.getElementById("historial-usuario-id");
const historialEstado = document.getElementById("historial-estado");
const mensajeHistorial = document.getElementById("mensaje-historial");
const historialTabla = document.getElementById("historial-tabla");
const historialPaginacion = document.getElementById("historial-paginacion");
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
  const usuarioId = historialUsuarioId.value.trim();
  if (!usuarioId) {
    mostrarMensajeHistorial("");
    showEmpty(historialTabla, "Ingresa un ID de usuario para ver su historial.", 6);
    historialPaginacion.textContent = "";
    return;
  }

  mostrarMensajeHistorial("");
  showLoading(historialTabla, 6);

  const params = new URLSearchParams({
    usuario_id: usuarioId,
    limite: LIMITE_HISTORIAL,
    offset: historialOffset,
  });
  if (historialEstado.value) params.set("estado", historialEstado.value);

  try {
    const r = await api.get(`/historial?${params}`);
    renderList(historialTabla, r.items, filaHistorial, "Este usuario no tiene préstamos.", 6);
    const desde = r.total === 0 ? 0 : r.offset + 1;
    const hasta = Math.min(r.offset + r.limite, r.total);
    historialPaginacion.textContent = `${desde}–${hasta} de ${r.total}`;
    btnHistorialAnterior.disabled = r.offset <= 0;
    btnHistorialSiguiente.disabled = r.offset + r.limite >= r.total;
  } catch (e) {
    showError(historialTabla, e.message, 6);
    mostrarMensajeHistorial(e.message);
    historialPaginacion.textContent = "";
  }
}

document.getElementById("btn-buscar-historial").addEventListener("click", () => {
  historialOffset = 0;
  cargarHistorial();
});
historialEstado.addEventListener("change", () => {
  historialOffset = 0;
  cargarHistorial();
});
btnHistorialAnterior.addEventListener("click", () => {
  historialOffset = Math.max(historialOffset - LIMITE_HISTORIAL, 0);
  cargarHistorial();
});
btnHistorialSiguiente.addEventListener("click", () => {
  historialOffset += LIMITE_HISTORIAL;
  cargarHistorial();
});

// --- Carga inicial -------------------------------------------------------------------

cargarInventario();
cargarPrestamos();
showEmpty(historialTabla, "Ingresa un ID de usuario para ver su historial.", 6);
