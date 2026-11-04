// Notificaciones de la cuenta autenticada, cargadas desde la API.

if (!requireAuth()) throw new Error("sin sesión");

renderSidebar("notificaciones");

const lista = document.getElementById("notificaciones");

function formatearFechaHora(iso) {
  return new Date(iso).toLocaleString("es-PE", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function filaNotificacion(n) {
  const accion = n.leida
    ? `<span class="badge neutral">Leída</span>`
    : `<button type="button" class="btn btn-ghost btn-sm btn-marcar-leida" data-id="${esc(n.id)}">Marcar como leída</button>`;
  return `<div class="loan${n.leida ? "" : " alert"}">
    <div><div class="t">${esc(n.mensaje)}</div><div class="s">${esc(formatearFechaHora(n.created_at))}</div></div>
    ${accion}
  </div>`;
}

async function pintar() {
  showLoading(lista);
  try {
    const notificaciones = await api.get("/notificaciones");
    renderList(lista, notificaciones, filaNotificacion, "No tienes notificaciones todavía.");
  } catch (e) {
    showError(lista, e.message);
  }
}

lista.addEventListener("click", async (evento) => {
  const boton = evento.target.closest(".btn-marcar-leida");
  if (!boton) return;
  boton.disabled = true;
  try {
    await api.patch(`/notificaciones/${Number(boton.dataset.id)}`, { leida: true });
    await pintar();
  } catch (e) {
    alert(e.message);
    boton.disabled = false;
  }
});

pintar();
