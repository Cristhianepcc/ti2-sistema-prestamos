// Mis Préstamos (issue #32). Mismo patrón que catalogo.js (ver frontend/README.md).
//
// Depende de #31 (GET /api/prestamos?mios=true) y de #29 (objeto `recurso`
// anidado en cada préstamo).
//
// Pantalla de SOLO LECTURA: no hay botón de devolver. La devolución la registra
// el custodio (#33).
//
// ⚠️ MIENTRAS EL BACKEND NO ESTÉ LISTO: USAR_PRUEBA = true muestra datos de
// ejemplo. Al integrar con #31, cambiar SOLO esa línea a `false`.
const USAR_PRUEBA = true;

if (!requireAuth()) throw new Error("sin sesión"); // corta si no hay token

const caja = document.getElementById("prestamos");

document
  .getElementById("btn-cerrar-sesion")
  .addEventListener("click", () => api.logout());

// Días de anticipación desde los que se resalta un préstamo ACTIVO.
const DIAS_ALERTA = 2;

// --- Fechas -----------------------------------------------------------------

// "2026-10-20" → Date en hora LOCAL. new Date("2026-10-20") la interpretaría en
// UTC y en Perú (UTC-5) caería en el día anterior, desfasando el aviso de vencimiento.
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

// --- Datos ------------------------------------------------------------------

// Fecha relativa a hoy ("YYYY-MM-DD"), para que el resaltado se pueda ver en la
// demo sin importar el día en que se abra.
function fechaRelativa(dias) {
  const d = new Date();
  d.setDate(d.getDate() + dias);
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${mm}-${dd}`;
}

// Forma esperada según el spec del #32 / #29. Cubre los 3 estados y los casos
// de resaltado (vence en 1 día, ya pasó pero el backend aún no lo marca).
const PRESTAMOS_PRUEBA = [
  {
    id: 1,
    estado: "ACTIVO",
    fecha_entrega: fechaRelativa(-6),
    fecha_limite: fechaRelativa(1),
    recurso: { id: 10, codigo: "LIB-001", nombre: "Clean Code" },
  },
  {
    id: 2,
    estado: "ACTIVO",
    fecha_entrega: fechaRelativa(-1),
    fecha_limite: fechaRelativa(6),
    recurso: { id: 12, codigo: "ACA-002", nombre: "Proyector Epson X05" },
  },
  {
    id: 3,
    estado: "ATRASADO",
    fecha_entrega: fechaRelativa(-12),
    fecha_limite: fechaRelativa(-3),
    recurso: { id: 11, codigo: "DEP-004", nombre: "Balón de fútbol" },
  },
  {
    id: 4,
    estado: "ACTIVO",
    fecha_entrega: fechaRelativa(-8),
    fecha_limite: fechaRelativa(-1),
    recurso: { id: 14, codigo: "ACA-005", nombre: "Arduino Uno" },
  },
  {
    id: 5,
    estado: "DEVUELTO",
    fecha_entrega: fechaRelativa(-30),
    fecha_limite: fechaRelativa(-23),
    recurso: { id: 10, codigo: "LIB-002", nombre: "Código Limpio (edición 2)" },
  },
];

async function obtenerPrestamos() {
  if (USAR_PRUEBA) return structuredClone(PRESTAMOS_PRUEBA);
  return api.get("/prestamos?mios=true");
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

  const limite = resaltar
    ? `<strong class="text-danger">⚠️ ${esc(formatearFecha(p.fecha_limite))}</strong>`
    : `<strong>${esc(formatearFecha(p.fecha_limite))}</strong>`;

  return `
    <div class="card mb-2${resaltar ? " border-danger" : ""}">
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-start">
          <h2 class="h6 mb-1">${esc(nombre)}</h2>
          ${badgePrestamo(p.estado)}
        </div>
        <p class="text-muted small mb-1">${esc(codigo)}</p>
        <p class="small mb-0">
          ${esc(formatearFecha(p.fecha_entrega))} → ${limite}
        </p>
        ${aviso ? `<p class="small text-danger fw-semibold mb-0 mt-1">${esc(aviso)}</p>` : ""}
      </div>
    </div>`;
}

async function cargarPrestamos() {
  showLoading(caja);
  try {
    const prestamos = await obtenerPrestamos();
    renderList(caja, prestamos, tarjetaPrestamo, "No tienes préstamos");
  } catch (e) {
    showError(caja, e.message);
  }
}

cargarPrestamos();
