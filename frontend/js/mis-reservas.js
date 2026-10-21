// Mis Reservas (issue #28). Mismo patrón que catalogo.js (ver frontend/README.md).

if (!requireAuth()) throw new Error("sin sesión"); // corta si no hay token

renderSidebar("reservas");

const caja = document.getElementById("reservas");
const cajaError = document.getElementById("reservas-error");

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
      <td>${esc(formatearFecha(r.fecha))} · ${esc(r.franja)}</td>
      <td>${badgeReserva(r.estado)}</td>
      <td>${botonCancelar}</td>
    </tr>`;
}

async function cargarReservas() {
  showFormError(cajaError, null);
  showLoading(caja, 4);
  try {
    const reservas = await api.get("/reservas?mias=true");
    renderList(caja, reservas, filaReserva, "No tienes reservas", 4);
  } catch (e) {
    showError(caja, e.message, 4);
  }
}

// --- Cancelar ---------------------------------------------------------------

// Un solo listener para todos los botones (las filas se pintan con innerHTML).
caja.addEventListener("click", async (evento) => {
  const boton = evento.target.closest(".btn-cancelar");
  if (!boton) return;

  if (!confirm("¿Seguro que quieres cancelar esta reserva?")) return;

  showFormError(cajaError, null);
  setBusy(boton, true, "Cancelando…");

  try {
    await api.del(`/reservas/${boton.dataset.id}`);
    // Saca la fila sin recargar la lista.
    boton.closest("tr").remove();
    if (!caja.querySelector("tr")) showEmpty(caja, "No tienes reservas", 4);
  } catch (e) {
    // 404/403/etc.: el mensaje viene del backend.
    showFormError(cajaError, e.message);
    setBusy(boton, false);
  }
});

cargarReservas();
