// Bandeja persistida en el backend. La tabla conserva el diseño existente.

if (!requireAuth()) throw new Error("sin sesión");

renderSidebar("solicitudes");

const tabla = document.getElementById("solicitudes");
let solicitudes = [];

function accionDisponible(s) {
  if (
    s.estado === "SOLICITADA" &&
    s.tipo_solicitud !== "SIMPLE" &&
    hasRole("DOCENTE")
  ) {
    return ["avalar", "Avalar"];
  }
  if (
    s.estado === "AVALADA" &&
    s.tipo_solicitud === "EXCEPCIONAL" &&
    hasRole("DIRECCION_ESCUELA")
  ) {
    return ["autorizar", "Autorizar"];
  }
  const rolCustodio =
    s.recurso?.gestor === "CENTRO_ESTUDIANTES"
      ? "CUSTODIO_CE"
      : "CUSTODIO_INFRA";
  const listaParaCustodio =
    (s.tipo_solicitud === "SIMPLE" && s.estado === "SOLICITADA") ||
    (s.tipo_solicitud === "POR_CURSO" && s.estado === "AVALADA") ||
    (s.tipo_solicitud === "EXCEPCIONAL" && s.estado === "AUTORIZADA");
  return listaParaCustodio && hasRole(rolCustodio)
    ? ["aceptar", "Aceptar"]
    : null;
}

function filaSolicitud(s) {
  const recurso = s.recurso || {};
  const solicitante = s.solicitante || {};
  const detalleTipo = ETIQUETA_TIPO_SOLICITUD[s.tipo_solicitud] || s.tipo_solicitud;
  const motivo = s.motivo ? `<div class="sub">${esc(s.motivo)}</div>` : "";
  const accion = accionDisponible(s);
  const botonAccion = accion
    ? `<button type="button" class="btn btn-primary btn-sm btn-resolver" data-id="${esc(s.id)}" data-accion="${accion[0]}">${accion[1]}</button>`
    : "";

  return `<tr>
    <td><b>${esc(recurso.nombre)}</b><div class="sub">${esc(recurso.codigo)} · ${esc(ETIQUETA_TIPO[recurso.tipo_recurso])}</div></td>
    <td>${esc(solicitante.nombres || `Usuario #${s.solicitante_id}`)}</td>
    <td>${esc(detalleTipo)}${motivo}</td>
    <td>${badgeSolicitud(s.estado)}</td>
    <td><div class="acciones-tabla">
      ${botonAccion}
      <button type="button" class="btn btn-danger-ghost btn-sm btn-rechazar" data-id="${esc(s.id)}">Rechazar</button>
    </div></td>
  </tr>`;
}

async function pintar() {
  showLoading(tabla, 5);
  try {
    solicitudes = await api.get("/solicitudes?pendientes=true");
    renderList(tabla, solicitudes, filaSolicitud, "No hay solicitudes pendientes.", 5);
  } catch (e) {
    showError(tabla, e.message, 5);
  }
}

async function resolver(solicitud, accion) {
  const ruta = `/solicitudes/${solicitud.id}/${accion}`;
  if (accion === "aceptar") {
    const modalidad =
      solicitud.tipo_solicitud === "EXCEPCIONAL" ||
      solicitud.recurso.tipo_recurso === "LIBRO"
        ? "RETIRO_TEMPORAL"
        : "EN_SITIO";
    return api.post(ruta, { modalidad_uso: modalidad });
  }
  if (accion === "rechazar") {
    return api.post(ruta, { motivo_rechazo: null });
  }
  return api.post(ruta, {});
}

tabla.addEventListener("click", async (evento) => {
  const boton = evento.target.closest(".btn-resolver, .btn-rechazar");
  if (!boton) return;

  const solicitud = solicitudes.find((s) => s.id === Number(boton.dataset.id));
  if (!solicitud) return;
  const accion = boton.classList.contains("btn-rechazar")
    ? "rechazar"
    : boton.dataset.accion;
  const confirmacion =
    accion === "aceptar"
      ? "¿Aceptar esta solicitud y registrar el préstamo?"
      : accion === "rechazar"
        ? "¿Rechazar esta solicitud?"
        : `¿${accion === "avalar" ? "Avalar" : "Autorizar"} esta solicitud?`;
  if (!confirm(confirmacion)) return;

  boton.disabled = true;
  try {
    await resolver(solicitud, accion);
    await pintar();
  } catch (e) {
    alert(e.message);
    boton.disabled = false;
  }
});

pintar();
