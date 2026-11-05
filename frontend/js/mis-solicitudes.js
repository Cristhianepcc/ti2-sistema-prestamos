// Seguimiento de solicitudes propias mediante GET /solicitudes?mias=true.

if (!requireAuth()) throw new Error("sin sesión");

renderSidebar("misSolicitudes");

const tabla = document.getElementById("mis-solicitudes");

function fechaSolicitud(iso) {
  return new Date(iso).toLocaleDateString("es-PE", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function filaSolicitud(s) {
  const recurso = s.recurso || {};
  const tipo = ETIQUETA_TIPO_SOLICITUD[s.tipo_solicitud] || s.tipo_solicitud;
  return `<tr>
    <td><b>${esc(recurso.nombre || `Recurso #${s.recurso_id}`)}</b><div class="sub">${esc(recurso.codigo || "")}</div></td>
    <td>${esc(tipo)}</td>
    <td>${s.motivo ? esc(s.motivo) : "—"}</td>
    <td>${badgeSolicitud(s.estado)}</td>
    <td>${esc(fechaSolicitud(s.created_at))}</td>
  </tr>`;
}

async function cargar() {
  showLoading(tabla, 5);
  try {
    const solicitudes = await api.get("/solicitudes?mias=true");
    renderList(tabla, solicitudes, filaSolicitud, "Todavía no has enviado solicitudes.", 5);
  } catch (error) {
    showError(tabla, error.message, 5);
  }
}

cargar();
