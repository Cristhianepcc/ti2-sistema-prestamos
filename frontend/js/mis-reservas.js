// Mis Reservas (issue #28). Mismo patrón que catalogo.js (ver frontend/README.md).
//
// Depende de #26 (GET /api/reservas?mias=true y DELETE /api/reservas/{id}) y de
// #24 (objeto `recurso` anidado en cada reserva).
//
// ⚠️ MIENTRAS EL BACKEND NO ESTÉ LISTO: USAR_PRUEBA = true muestra datos de
// ejemplo y simula la cancelación. Al integrar con #26, cambiar SOLO esa línea
// a `false`.
const USAR_PRUEBA = false;

if (!requireAuth()) throw new Error("sin sesión"); // corta si no hay token

const caja = document.getElementById("reservas");
const cajaError = document.getElementById("reservas-error");

document
  .getElementById("btn-cerrar-sesion")
  .addEventListener("click", () => api.logout());

// --- Datos ------------------------------------------------------------------

// Forma esperada según el spec del #28 / #24. Cubre los 4 estados.
const RESERVAS_PRUEBA = [
  {
    id: 1,
    fecha: "2026-10-20",
    franja: "10:00 - 12:00",
    estado: "PENDIENTE",
    recurso: { id: 10, codigo: "LIB-001", nombre: "Clean Code" },
  },
  {
    id: 2,
    fecha: "2026-10-22",
    franja: "14:00 - 16:00",
    estado: "PENDIENTE",
    recurso: { id: 12, codigo: "ACA-002", nombre: "Proyector Epson X05" },
  },
  {
    id: 3,
    fecha: "2026-10-12",
    franja: "08:00 - 10:00",
    estado: "CONFIRMADA",
    recurso: { id: 14, codigo: "ACA-005", nombre: "Arduino Uno" },
  },
  {
    id: 4,
    fecha: "2026-10-05",
    franja: "16:00 - 18:00",
    estado: "VENCIDA",
    recurso: { id: 10, codigo: "LIB-001", nombre: "Clean Code" },
  },
  {
    id: 5,
    fecha: "2026-10-08",
    franja: "10:00 - 12:00",
    estado: "CANCELADA",
    recurso: { id: 15, codigo: "ACA-007", nombre: "Kit LEGO Mindstorms" },
  },
];

async function obtenerReservas() {
  if (USAR_PRUEBA) return structuredClone(RESERVAS_PRUEBA);
  return api.get("/reservas?mias=true");
}

async function cancelarReserva(id) {
  if (USAR_PRUEBA) return; // simula un 204
  return api.del(`/reservas/${id}`);
}

// --- Fechas -----------------------------------------------------------------

// "2026-10-20" → Date en hora LOCAL. new Date("2026-10-20") la interpretaría en
// UTC y en Perú (UTC-5) mostraría el día anterior.
function parseFechaLocal(texto) {
  const [anio, mes, dia] = String(texto).slice(0, 10).split("-").map(Number);
  return new Date(anio, mes - 1, dia);
}

function formatearFecha(texto) {
  return parseFechaLocal(texto).toLocaleDateString("es-PE", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

// --- Render -----------------------------------------------------------------

function tarjetaReserva(r) {
  const nombre = r.recurso ? r.recurso.nombre : "Recurso sin datos";
  const codigo = r.recurso ? r.recurso.codigo : "";

  // Solo una reserva PENDIENTE tiene sentido cancelarla: CONFIRMADA ya se
  // convirtió en préstamo; CANCELADA y VENCIDA ya terminaron.
  const botonCancelar =
    r.estado === "PENDIENTE"
      ? `<button type="button" class="btn btn-outline-danger btn-sm btn-cancelar"
                 data-id="${esc(r.id)}">Cancelar</button>`
      : "";

  return `
    <div class="card mb-2" data-reserva-id="${esc(r.id)}">
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-start">
          <h2 class="h6 mb-1">${esc(nombre)}</h2>
          ${badgeReserva(r.estado)}
        </div>
        <p class="text-muted small mb-1">${esc(codigo)}</p>
        <p class="small mb-2">${esc(formatearFecha(r.fecha))} · ${esc(r.franja)}</p>
        ${botonCancelar}
      </div>
    </div>`;
}

async function cargarReservas() {
  showFormError(cajaError, null);
  showLoading(caja);
  try {
    const reservas = await obtenerReservas();
    renderList(caja, reservas, tarjetaReserva, "No tienes reservas");
  } catch (e) {
    showError(caja, e.message);
  }
}

// --- Cancelar ---------------------------------------------------------------

// Un solo listener para todos los botones (las tarjetas se pintan con innerHTML).
caja.addEventListener("click", async (evento) => {
  const boton = evento.target.closest(".btn-cancelar");
  if (!boton) return;

  if (!confirm("¿Seguro que quieres cancelar esta reserva?")) return;

  showFormError(cajaError, null);
  setBusy(boton, true, "Cancelando…");

  try {
    await cancelarReserva(boton.dataset.id);
    // Saca la tarjeta sin recargar la lista.
    boton.closest(".card").remove();
    if (!caja.querySelector(".card")) showEmpty(caja, "No tienes reservas");
  } catch (e) {
    // 404/403/etc.: el mensaje viene del backend.
    showFormError(cajaError, e.message);
    setBusy(boton, false);
  }
});

cargarReservas();
