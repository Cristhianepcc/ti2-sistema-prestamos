// Notificaciones (prototipo de frontend, ver js/mock-solicitudes.js): avisos
// dentro de la plataforma cuando una Solicitud se acepta o rechaza
// (docs/00-contexto-alcance-propuesta.md §8, hallazgo #13).

if (!requireAuth()) throw new Error("sin sesión");

renderSidebar("notificaciones");

const usuario = currentUser();
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
    : `<button type="button" class="btn btn-ghost btn-sm btn-marcar-leida" data-id="${n.id}">Marcar como leída</button>`;
  return `<div class="loan${n.leida ? "" : " alert"}">
    <div><div class="t">${esc(n.mensaje)}</div><div class="s">${esc(formatearFechaHora(n.created_at))}</div></div>
    ${accion}
  </div>`;
}

function pintar() {
  const notificaciones = MockNotificaciones.listar(usuario.email);
  renderList(lista, notificaciones, filaNotificacion, "No tienes notificaciones todavía.");
}

lista.addEventListener("click", (evento) => {
  const btn = evento.target.closest(".btn-marcar-leida");
  if (!btn) return;
  MockNotificaciones.marcarLeida(Number(btn.dataset.id));
  pintar();
});

pintar();
