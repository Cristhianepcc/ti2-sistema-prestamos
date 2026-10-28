// Bandeja de Solicitudes del custodio (prototipo de frontend, ver
// js/mock-solicitudes.js). Reemplaza el registro directo de un préstamo
// SIMPLE: el custodio ya no registra en persona sin solicitud previa
// (docs/00-contexto-alcance-propuesta.md §8, hallazgo #13).

if (!requireAuth()) throw new Error("sin sesión");

renderSidebar("solicitudes");

const rolCustodio = hasRole("CUSTODIO_CE") ? "CUSTODIO_CE" : "CUSTODIO_INFRA";
const tabla = document.getElementById("solicitudes");

function filaSolicitud(s) {
  const detalleTipo =
    ETIQUETA_TIPO_SOLICITUD[s.tipo_solicitud] || s.tipo_solicitud;
  const motivo = s.motivo ? `<div class="sub">${esc(s.motivo)}</div>` : "";
  return `<tr>
    <td><b>${esc(s.recurso_nombre)}</b><div class="sub">${esc(s.recurso_codigo)} · ${esc(ETIQUETA_TIPO[s.tipo_recurso])}</div></td>
    <td>${esc(s.solicitante_nombre)}</td>
    <td>${esc(detalleTipo)}${motivo}</td>
    <td>${badgeSolicitud(s.estado)}</td>
    <td>
      <div class="acciones-tabla">
        <button type="button" class="btn btn-primary btn-sm btn-aceptar" data-id="${s.id}">Aceptar</button>
        <button type="button" class="btn btn-danger-ghost btn-sm btn-rechazar" data-id="${s.id}">Rechazar</button>
      </div>
    </td>
  </tr>`;
}

function pintar() {
  const pendientes = MockSolicitudes.pendientesParaCustodio(rolCustodio);
  renderList(tabla, pendientes, filaSolicitud, "No hay solicitudes pendientes.", 5);
}

tabla.addEventListener("click", (evento) => {
  const btnAceptar = evento.target.closest(".btn-aceptar");
  if (btnAceptar) {
    const id = Number(btnAceptar.dataset.id);
    if (!confirm("¿Aceptar esta solicitud y registrar la entrega?")) return;
    MockSolicitudes.aceptar(id);
    pintar();
    return;
  }

  const btnRechazar = evento.target.closest(".btn-rechazar");
  if (btnRechazar) {
    const id = Number(btnRechazar.dataset.id);
    if (!confirm("¿Rechazar esta solicitud?")) return;
    MockSolicitudes.rechazar(id);
    pintar();
  }
});

pintar();
