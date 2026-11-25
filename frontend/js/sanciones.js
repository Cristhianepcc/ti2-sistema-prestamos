if (!requireAuth()) throw new Error("sin sesión");

renderSidebar("sanciones");

const cajaMias = document.getElementById("mis-sanciones");
const seccionGestion = document.getElementById("seccion-gestion-sanciones");
const tituloGestion = document.getElementById("titulo-gestion-sanciones");
const ayudaGestion = document.getElementById("ayuda-gestion-sanciones");
const cajaGestion = document.getElementById("gestion-sanciones");
const puedeConsultarGestion = hasRole(
  "CUSTODIO_CE",
  "CUSTODIO_INFRA",
  "ADMINISTRADOR_SISTEMA"
);
const puedeResolver = hasRole("CUSTODIO_CE", "CUSTODIO_INFRA");
const ETIQUETA_EVENTO_SANCION = {
  REGISTRADA: "Sanción registrada",
  REPARACION_REGISTRADA: "Reparación registrada",
  REPOSICION_REGISTRADA: "Reposición registrada",
  VENCIDA: "Bloqueo vencido automáticamente",
};

if (puedeConsultarGestion) {
  seccionGestion.hidden = false;
  tituloGestion.textContent = hasRole("ADMINISTRADOR_SISTEMA")
    ? "Sanciones del sistema"
    : "Sanciones de los recursos que administras";
  ayudaGestion.textContent = puedeResolver
    ? "Registra la reparación o la reposición para cerrar la sanción y conservar su historial."
    : "Consulta sanciones de todos los usuarios.";
}

function fechaHoraLocal(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("es-PE", {
    timeZone: "America/Lima",
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function estadoSancion(s) {
  if (!s.activa) return `<span class="badge neutral">Resuelta</span>`;
  if (s.fin) return `<span class="badge warn">Activa hasta ${esc(fechaHoraLocal(s.fin))}</span>`;
  return `<span class="badge danger">Activa · requiere resolución</span>`;
}

function eventosHtml(eventos = []) {
  if (eventos.length === 0) return "";
  return `<details class="sancion-eventos">
    <summary>Historial (${eventos.length})</summary>
    <ol>${eventos.map((e) => `
      <li><b>${esc(ETIQUETA_EVENTO_SANCION[e.tipo] || e.tipo)}</b>
        <span>${esc(fechaHoraLocal(e.created_at))}</span>
        <p>${esc(e.detalle)}</p>
        ${e.actor ? `<small>Registrado por ${esc(e.actor.nombres)}</small>` : ""}
        ${e.recurso_reposicion_id ? `<small>Ejemplar de reposición #${esc(e.recurso_reposicion_id)}</small>` : ""}
      </li>`).join("")}</ol>
  </details>`;
}

function formularioResolucion(s) {
  if (!puedeResolver || !s.activa || s.motivo === "RETRASO") return "";
  const esPerdida = s.motivo === "PERDIDA";
  return `<form class="form-card sancion-resolucion" data-id="${esc(s.id)}">
    <label class="field">${esPerdida ? "Detalle de la reposición" : "Detalle de la reparación"}
      <textarea name="detalle" rows="2" required minlength="3" maxlength="1000" placeholder="Qué se hizo y cuándo"></textarea>
    </label>
    ${esPerdida ? `<label class="field">Código del nuevo ejemplar en inventario
      <input name="recurso_reposicion_id" type="number" min="1" required>
    </label>` : ""}
    <div class="alert-danger form-error-msg" hidden></div>
    <button type="submit" class="btn btn-primary btn-sm">Registrar ${esPerdida ? "reposición" : "reparación"}</button>
  </form>`;
}

function tarjetaSancion(s, gestionar = false) {
  const recurso = s.prestamo?.recurso || {};
  const nombreMotivo = ETIQUETA_MOTIVO_SANCION[s.motivo] || s.motivo;
  const nombreUsuario = s.usuario?.nombres || `Usuario #${s.usuario_id}`;
  const datosUsuario = gestionar
    ? `<div class="s">${esc(nombreUsuario)} · ${esc(s.usuario?.codigo || "")}</div>`
    : "";
  const resolucion = gestionar ? formularioResolucion(s) : "";

  return `<article class="loan sancion-card${s.activa ? " alert" : ""}">
    <div class="sancion-contenido">
      <div class="t">${esc(nombreMotivo)} · ${esc(recurso.nombre || `Recurso #${recurso.id || "?"}`)}</div>
      <div class="s">${esc(recurso.codigo || "")} · Préstamo #${esc(s.prestamo_id)}</div>
      ${datosUsuario}
      <div class="dates">Registrada: ${esc(fechaHoraLocal(s.inicio))} · ${estadoSancion(s)}</div>
      ${s.detalle ? `<p class="sancion-detalle">${esc(s.detalle)}</p>` : ""}
      ${eventosHtml(s.eventos)}
      ${resolucion}
    </div>
  </article>`;
}

async function cargar() {
  showLoading(cajaMias);
  if (puedeConsultarGestion) showLoading(cajaGestion);
  try {
    const mias = await api.get("/sanciones?mias=true");
    renderList(cajaMias, mias, (s) => tarjetaSancion(s), "No tienes sanciones registradas.");
    if (puedeConsultarGestion) {
      const todas = await api.get("/sanciones");
      renderList(cajaGestion, todas, (s) => tarjetaSancion(s, true), "No hay sanciones para mostrar.");
    }
  } catch (e) {
    showError(cajaMias, e.message);
    if (puedeConsultarGestion) showError(cajaGestion, e.message);
  }
}

cajaGestion.addEventListener("submit", async (evento) => {
  const form = evento.target.closest(".sancion-resolucion");
  if (!form) return;
  evento.preventDefault();
  const valores = formValues(form);
  const boton = form.querySelector('button[type="submit"]');
  const error = form.querySelector(".form-error-msg");
  const payload = { detalle: valores.detalle };
  if (valores.recurso_reposicion_id) {
    payload.recurso_reposicion_id = Number(valores.recurso_reposicion_id);
  }

  setBusy(boton, true, "Guardando...");
  showFormError(error, "");
  try {
    await api.patch(`/sanciones/${Number(form.dataset.id)}/levantar`, payload);
    await cargar();
  } catch (e) {
    showFormError(error, e.message || "No se pudo registrar la resolución.");
    setBusy(boton, false);
  }
});

cargar();
