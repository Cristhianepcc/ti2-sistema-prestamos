// Reportes (RF6): dashboard administrativo de solo lectura — resumen general,
// usuarios, inventario, actividad de préstamos, demanda de recursos e
// incidencias. Solo ADMINISTRADOR_SISTEMA (el backend aplica la misma regla;
// ver docs/02-contrato-api.md, Anexo RF6). Los gráficos vienen de charts.js
// (SVG/HTML hechos a mano, sin librería externa).

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

// Inversa de parseFechaLocal: Date local -> "YYYY-MM-DD", sin pasar por UTC
// (toISOString() se corre de día cerca de medianoche en huso horario negativo).
function fechaISO(d) {
  const anio = d.getFullYear();
  const mes = String(d.getMonth() + 1).padStart(2, "0");
  const dia = String(d.getDate()).padStart(2, "0");
  return `${anio}-${mes}-${dia}`;
}

// --- Stats ---------------------------------------------------------------------

function statHTML(n, l, color) {
  const style = color ? ` style="color:var(--${color})"` : "";
  return `<div class="stat"><div class="n"${style}>${esc(n)}</div><div class="l">${esc(l)}</div></div>`;
}

// --- Resumen general -------------------------------------------------------------

const ICONO_ALERTA =
  '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>';

const kpiGrid = document.getElementById("kpi-grid");

function kpiCardHTML(icono, valor, etiqueta, alerta) {
  return `<div class="kpi-card">
    <div class="kpi-icono${alerta ? " danger" : ""}">${icono}</div>
    <div><div class="n">${esc(valor)}</div><div class="l">${esc(etiqueta)}</div></div>
  </div>`;
}

async function cargarResumenGeneral() {
  showLoading(kpiGrid);
  try {
    const r = await api.get("/reportes/resumen");
    kpiGrid.innerHTML = [
      kpiCardHTML(ICONOS.usuarios, r.total_usuarios, "Usuarios registrados"),
      kpiCardHTML(ICONOS.inventario, r.total_recursos, "Recursos totales"),
      kpiCardHTML(ICONOS.prestamos, r.total_prestamos, "Préstamos registrados"),
      kpiCardHTML(ICONO_ALERTA, r.prestamos_atrasados, "Préstamos atrasados", r.prestamos_atrasados > 0),
    ].join("");
  } catch (e) {
    showError(kpiGrid, e.message);
  }
}

// --- Usuarios --------------------------------------------------------------------

const usuariosStats = document.getElementById("usuarios-stats");
const usuariosTabla = document.getElementById("usuarios-tabla");

function filaRol(rol, cantidad) {
  return `<tr><td>${esc(ETIQUETA_ROL[rol] || rol)}</td><td>${esc(cantidad)}</td></tr>`;
}

async function cargarUsuarios() {
  showLoading(usuariosStats);
  showLoading(usuariosTabla, 5);
  try {
    const r = await api.get("/reportes/usuarios");
    usuariosStats.innerHTML = [
      statHTML(r.total_usuarios, "Usuarios registrados"),
      statHTML(r.administradores, "Cuentas administrador"),
    ].join("");

    usuariosTabla.innerHTML = Object.entries(r.por_rol)
      .map(([rol, cantidad]) => filaRol(rol, cantidad))
      .join("");
  } catch (e) {
    showError(usuariosStats, e.message);
    showError(usuariosTabla, e.message, 5);
  }
}

// --- Inventario ------------------------------------------------------------------

const inventarioStats = document.getElementById("inventario-stats");
const inventarioDonut = document.getElementById("inventario-donut");
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
  showLoading(inventarioDonut);
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

    // Mismos colores que los badges de estado (ETIQUETA_ESTADO en render.js),
    // para que la dona coincida visualmente con el resto del sistema.
    inventarioDonut.innerHTML = donutChartHTML([
      { label: "Disponible", valor: r.por_estado.DISPONIBLE || 0, color: "var(--ok)" },
      { label: "Reservado", valor: r.por_estado.RESERVADO || 0, color: "var(--warn)" },
      { label: "Prestado", valor: r.por_estado.PRESTADO || 0, color: "var(--neutral)" },
      { label: "Mantenimiento", valor: r.por_estado.MANTENIMIENTO || 0, color: "var(--danger)" },
    ]);

    inventarioTabla.innerHTML = Object.keys(ETIQUETA_TIPO)
      .map((tipo) => filaInventario(tipo, r.tipo_por_estado))
      .join("");
  } catch (e) {
    showError(inventarioStats, e.message);
    showError(inventarioDonut, e.message);
    showError(inventarioTabla, e.message, 5);
  }
}

// --- Actividad de préstamos + demanda de recursos + incidencias -----------------

const prestamosStats = document.getElementById("prestamos-stats");
const evolucionChart = document.getElementById("evolucion-chart");
const masPrestados = document.getElementById("mas-prestados");
const distribucionRolesEl = document.getElementById("distribucion-roles");
const garantiasEl = document.getElementById("garantias");
const atrasadosTabla = document.getElementById("atrasados-tabla");
const atrasadosNota = document.getElementById("atrasados-nota");
const filtroDesde = document.getElementById("filtro-desde");
const filtroHasta = document.getElementById("filtro-hasta");
const periodoImpreso = document.getElementById("periodo-impreso");

// El reporte de préstamos es retrospectivo (fecha_entrega nunca es futura),
// así que no tiene sentido dejar elegir un rango que no puede tener datos.
// El backend valida lo mismo (RangoInvalido -> 422) para quien llame la API
// directo, sin pasar por este selector.
const hoy = new Date();
const hoyISO = fechaISO(hoy);
filtroDesde.max = hoyISO;
filtroHasta.max = hoyISO;

const ETIQUETA_DISTRIBUCION_ROL = {
  ESTUDIANTE: "Estudiantes",
  DOCENTE: "Docentes",
  CUSTODIO: "Custodios",
  ADMINISTRADOR_SISTEMA: "Administradores",
};
const COLOR_DISTRIBUCION_ROL = {
  ESTUDIANTE: "var(--azul)",
  DOCENTE: "var(--verde)",
  CUSTODIO: "var(--warn)",
  ADMINISTRADOR_SISTEMA: "var(--neutral)",
};

function filaAtrasado(item) {
  return `<tr>
    <td>${esc(item.recurso.nombre)} <span class="hint">${esc(item.recurso.codigo)}</span></td>
    <td>${esc(item.prestatario.nombres)} <span class="hint">${esc(item.prestatario.codigo)}</span></td>
    <td>${esc(formatearFecha(item.fecha_limite))}</td>
    <td><span class="badge danger">${esc(item.dias_atraso)} días</span></td>
    <td class="no-imprimir"><a class="btn btn-ghost btn-sm" href="historial.html?usuario_id=${esc(item.prestatario.id)}">Ver historial</a></td>
  </tr>`;
}

async function cargarPrestamos() {
  showLoading(prestamosStats);
  showLoading(evolucionChart);
  showLoading(masPrestados);
  showLoading(distribucionRolesEl);
  showLoading(garantiasEl);
  showLoading(atrasadosTabla, 5);
  atrasadosNota.textContent = "";

  const params = new URLSearchParams();
  if (filtroDesde.value) params.set("desde", filtroDesde.value);
  if (filtroHasta.value) params.set("hasta", filtroHasta.value);
  const query = params.toString() ? `?${params}` : "";

  try {
    const [r, evolucion] = await Promise.all([
      api.get(`/reportes/prestamos${query}`),
      api.get(`/reportes/prestamos/evolucion${query}`).catch(() => null),
    ]);

    // Texto que solo se ve al imprimir/exportar (ver .solo-imprimir en
    // styles.css): dentro del PDF, el filtro desde/hasta ya no está visible
    // como input, así que el periodo exacto queda escrito en el documento.
    periodoImpreso.textContent = evolucion
      ? `Periodo mostrado: ${formatearFecha(evolucion.periodo.desde)} – ${formatearFecha(evolucion.periodo.hasta)}`
      : "";

    prestamosStats.innerHTML = [
      statHTML(r.total_prestamos, "Préstamos registrados"),
      statHTML(r.por_estado.ACTIVO || 0, "Activos"),
      statHTML(
        r.por_estado.ATRASADO || 0,
        "Atrasados",
        r.por_estado.ATRASADO ? "danger" : undefined
      ),
      statHTML(r.por_estado.DEVUELTO || 0, "Devueltos"),
    ].join("");

    evolucionChart.innerHTML = evolucion
      ? lineChartHTML(evolucion.puntos)
      : `<p class="alert-danger">No se pudo cargar la evolución de préstamos.</p>`;

    masPrestados.innerHTML = barChartHTML(
      r.mas_prestados.map((item) => ({ label: item.nombre, sub: item.codigo, valor: item.total }))
    );

    distribucionRolesEl.innerHTML = barChartHTML(
      Object.entries(r.distribucion_roles).map(([rol, valor]) => ({
        label: ETIQUETA_DISTRIBUCION_ROL[rol] || rol,
        valor,
        color: COLOR_DISTRIBUCION_ROL[rol],
      }))
    );

    garantiasEl.innerHTML = `
      <div class="mini-row"><div><div class="t">Garantías retenidas</div></div><b>${esc(r.garantias.retenidas)}</b></div>
      <div class="mini-row"><div><div class="t">Valor retenido</div></div><b>S/ ${esc(r.garantias.valor_retenido)}</b></div>`;

    renderList(atrasadosTabla, r.atrasados.items, filaAtrasado, "No hay préstamos atrasados.", 5);
    atrasadosNota.textContent =
      r.atrasados.total > r.atrasados.items.length
        ? `Mostrando los ${r.atrasados.items.length} más urgentes de ${r.atrasados.total} atrasados en total.`
        : "";
  } catch (e) {
    showError(prestamosStats, e.message);
    showError(evolucionChart, e.message);
    showError(masPrestados, e.message);
    showError(distribucionRolesEl, e.message);
    showError(garantiasEl, e.message);
    showError(atrasadosTabla, e.message, 5);
  }
}

// --- Períodos rápidos --------------------------------------------------------------

function aplicarPeriodoRapido(tipo) {
  let desde;
  if (tipo === "7d") {
    desde = new Date(hoy);
    desde.setDate(desde.getDate() - 6);
  } else if (tipo === "30d") {
    desde = new Date(hoy);
    desde.setDate(desde.getDate() - 29);
  } else if (tipo === "semestre") {
    // Semestre calendario simple (ene-jun / jul-dic): el sistema no modela
    // un calendario académico, así que se usa esta aproximación de 6 meses.
    desde = new Date(hoy.getFullYear(), hoy.getMonth() < 6 ? 0 : 6, 1);
  } else if (tipo === "anio") {
    desde = new Date(hoy.getFullYear(), 0, 1);
  } else {
    return;
  }
  filtroDesde.value = fechaISO(desde);
  filtroHasta.value = hoyISO;
  cargarPrestamos();
}

document.getElementById("periodos-rapidos").addEventListener("click", (evento) => {
  const boton = evento.target.closest("[data-periodo]");
  if (boton) aplicarPeriodoRapido(boton.dataset.periodo);
});

// --- Exportar PDF --------------------------------------------------------------

// Sin librería nueva: se apoya en "Imprimir > Guardar como PDF" del
// navegador, con la hoja de estilos @media print (.no-imprimir/.solo-imprimir
// en styles.css) que oculta sidebar/filtros/botones y muestra en su lugar el
// periodo y la fecha de generación como texto fijo.
document.getElementById("fecha-exportacion").textContent =
  `Reporte generado el ${new Date().toLocaleString("es-PE", { dateStyle: "long", timeStyle: "short" })}`;
document.getElementById("btn-exportar-pdf").addEventListener("click", () => window.print());

document.getElementById("btn-aplicar-filtro").addEventListener("click", cargarPrestamos);
document.getElementById("btn-limpiar-filtro").addEventListener("click", () => {
  filtroDesde.value = "";
  filtroHasta.value = "";
  cargarPrestamos();
});

// --- Carga inicial -------------------------------------------------------------------

// "Actividad de préstamos" arranca en los últimos 30 días (igual que el
// default del backend en /reportes/prestamos/evolucion) en vez de sin
// filtro, para que el gráfico de evolución tenga un rango con el que partir.
aplicarPeriodoRapido("30d");
cargarResumenGeneral();
cargarUsuarios();
cargarInventario();
