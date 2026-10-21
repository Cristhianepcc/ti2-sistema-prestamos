// Mis Préstamos (issue #32). Mismo patrón que catalogo.js (ver frontend/README.md).
//
// Pantalla de SOLO LECTURA: no hay botón de devolver. La devolución la registra
// el custodio (#33).

if (!requireAuth()) throw new Error("sin sesión"); // corta si no hay token

renderSidebar("prestamos");

const caja = document.getElementById("prestamos");
const cajaComprobante = document.getElementById("comprobante");

// Días de anticipación desde los que se resalta un préstamo ACTIVO.
const DIAS_ALERTA = 2;

// --- Fechas -----------------------------------------------------------------

// Admite tanto "2026-10-20" como un datetime ISO completo del backend — usa
// los primeros 10 caracteres en hora LOCAL, nunca UTC (en Perú corriría el día).
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

// Días que faltan para la fecha límite (negativo = ya pasó). Compara días
// calendario locales, sin horas.
function diasHasta(texto) {
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);
  return Math.round((parseFechaLocal(texto) - hoy) / 86400000);
}

// --- Render -----------------------------------------------------------------

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

const ETIQUETA_MODALIDAD = {
  EN_SITIO: "En sitio",
  RETIRO_TEMPORAL: "Retiro temporal",
};

let prestamos = [];

function mostrarComprobante(id) {
  const p = prestamos.find((x) => String(x.id) === String(id));
  cajaComprobante.innerHTML = p ? comprobante(p) : "";
  caja.querySelectorAll(".loan").forEach((el) => {
    el.classList.toggle("seleccionado", el.dataset.id === String(id));
  });
}

async function cargarPrestamos() {
  showLoading(caja);
  try {
    prestamos = await api.get("/prestamos?mios=true");
    renderList(caja, prestamos, tarjetaPrestamo, "No tienes préstamos");
    if (prestamos.length > 0) mostrarComprobante(prestamos[0].id);
  } catch (e) {
    showError(caja, e.message);
  }
}

caja.addEventListener("click", (evento) => {
  const tarjeta = evento.target.closest(".loan");
  if (tarjeta) mostrarComprobante(tarjeta.dataset.id);
});

cargarPrestamos();
