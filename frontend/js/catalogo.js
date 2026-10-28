if (!requireAuth()) throw new Error("sin sesión");

renderSidebar("catalogo");

const caja = document.getElementById("catalogo");
const inputBuscador = document.getElementById("input-buscador");
const filtrosTipo = document.getElementById("filtros-tipo");

let recursos = [];
let tipoActivo = "";

async function cargarCatalogo() {
    showLoading(caja);
    try {
        // Sin filtro de disponibilidad: hay que poder VER (y reservar) los
        // recursos ocupados, no solo los libres.
        recursos = await api.get("/recursos");
        pintarCatalogo();
    } catch (e) {
        showError(caja, e.message);
    }
}

function pintarCatalogo() {
    const texto = inputBuscador.value.toLowerCase();
    const filtrados = recursos.filter((r) => {
        const coincideTipo = !tipoActivo || r.tipo_recurso === tipoActivo;
        const coincideTexto =
            r.nombre.toLowerCase().includes(texto) ||
            (r.descripcion || "").toLowerCase().includes(texto) ||
            r.tipo_recurso.toLowerCase().includes(texto);
        return coincideTipo && coincideTexto;
    });
    renderList(caja, filtrados, tarjetaRecurso, "No se encontraron recursos.");
}

// Reservar es para cuando el recurso está OCUPADO (booking para cuando se
// libere, RF2). Deportivo nunca admite esto: es préstamo directo del mismo
// día (docs/00-contexto-alcance-propuesta.md §5), nunca booking anticipado.
function puedeReservar(r) {
    return r.tipo_recurso !== "DEPORTIVO" && !r.disponible && r.estado !== "MANTENIMIENTO";
}

// Solicitar es para cuando el recurso está LIBRE ahora: ya no hay registro
// directo en persona (hallazgo #13, docs/00-contexto-alcance-propuesta.md
// §8) — toda entrega (SIMPLE incluido) nace de una Solicitud que acepta un
// custodio. Prototipo de frontend sin backend: ver js/mock-solicitudes.js.
function puedeSolicitar(r) {
    return r.disponible;
}

// Ícono genérico de "espacio para foto" — placeholder hasta que la API
// tenga un campo de imagen real (no hay fotos de los recursos todavía).
const ICONO_IMAGEN_PENDIENTE =
    '<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>';

function tarjetaRecurso(r) {
    const usuario = currentUser();
    const yaSolicitado = puedeSolicitar(r) && MockSolicitudes.tieneSolicitudActiva(r.id, usuario.email);

    let boton;
    if (yaSolicitado) {
        boton = `<button type="button" class="btn btn-sm tp-boton" disabled>Solicitud enviada</button>`;
    } else if (puedeSolicitar(r)) {
        boton = `<button type="button" class="btn btn-primary btn-sm tp-boton btn-solicitar" data-id="${esc(r.id)}">Solicitar</button>`;
    } else if (puedeReservar(r)) {
        boton = `<button type="button" class="btn btn-primary btn-sm tp-boton btn-reservar" data-id="${esc(r.id)}">Reservar</button>`;
    } else {
        boton = `<button type="button" class="btn btn-sm tp-boton" disabled>${esc(ETIQUETA_ESTADO[r.estado]?.texto || r.estado)}</button>`;
    }

    return `
    <div class="tarjeta">
        <div class="tp-etiqueta"><span>${esc(ETIQUETA_TIPO[r.tipo_recurso])}</span></div>
        <div class="tp-col">
            <div class="tp-main">
                <div class="tp-media">
                    ${ICONO_IMAGEN_PENDIENTE}
                    <span class="tp-badge">${badgeEstado(r.estado)}</span>
                </div>
                <div class="tp-nombre">${esc(r.nombre)}</div>
                <p class="tp-detalle">${esc(r.codigo)} · ${detalleSegunTipo(r)}</p>
                <p class="tp-gestor">A cargo de ${esc(ETIQUETA_GESTOR[r.gestor] || r.gestor)}</p>
                ${boton}
            </div>
        </div>
    </div>`;
}

// ⚠️ Las claves de un subtipo NO existen en los otros: un DEPORTIVO no trae la
// clave `autor` ni siquiera en null. Hay que ramificar por tipo_recurso.
function detalleSegunTipo(r) {
    if (r.tipo_recurso === "LIBRO") return esc(r.autor);
    if (r.tipo_recurso === "DEPORTIVO") return esc(r.tipo_deportivo);
    return `Patrimonio ${esc(r.codigo_patrimonial)}`;
}

inputBuscador.addEventListener("input", pintarCatalogo);

filtrosTipo.addEventListener("click", (evento) => {
    const chip = evento.target.closest(".filter");
    if (!chip) return;
    tipoActivo = chip.dataset.tipo;
    filtrosTipo.querySelectorAll(".filter").forEach((f) => f.classList.toggle("on", f === chip));
    pintarCatalogo();
});

// --- Abrir el modal correspondiente al hacer click en la tarjeta ------------

// La prioridad de la reserva depende del tipo (EXCEPCIONAL>POR_CURSO>SIMPLE,
// backend/app/services/reserva_service.py). Libro/Deportivo son siempre
// SIMPLE (sin chip); solo Académico elige POR_CURSO/EXCEPCIONAL.
function formReservarTipoHTML(r) {
    if (r.tipo_recurso !== "ACADEMICO") return "";
    return `
        <label class="field">Tipo de solicitud
            <span class="chip-toggle" data-chip-grupo="tipo">
                <span class="chip-opt on" data-valor="POR_CURSO">Por curso</span>
                <span class="chip-opt" data-valor="EXCEPCIONAL">Excepcional (retiro)</span>
            </span>
            <input type="hidden" name="tipo" value="POR_CURSO">
        </label>`;
}

function formSolicitarTipoHTML(r) {
    if (r.tipo_recurso !== "ACADEMICO") {
        return `<p class="nota-futura">Se enviará como solicitud SIMPLE; el custodio la acepta o rechaza manualmente.</p>`;
    }
    return `
        <label class="field">Motivo (curso, tesis o proyecto)
            <textarea name="motivo" required placeholder="Ej: Curso de Redes, prof. Fernández"></textarea>
        </label>
        <label class="field">Tipo de solicitud
            <span class="chip-toggle" data-chip-grupo="tipo_solicitud">
                <span class="chip-opt on" data-valor="POR_CURSO">Por curso</span>
                <span class="chip-opt" data-valor="EXCEPCIONAL">Excepcional (retiro)</span>
            </span>
            <input type="hidden" name="tipo_solicitud" value="POR_CURSO">
        </label>`;
}

function abrirModalReservar(r) {
    openModal(
        `Reservar · ${r.nombre}`,
        `<form data-accion="reservar" data-id="${esc(r.id)}">
            <div class="fila">
                <label class="field">Fecha
                    <input type="date" name="fecha" required>
                </label>
                <label class="field">Franja
                    <input type="text" name="franja" placeholder="ej: 10:00-12:00" required>
                </label>
            </div>
            ${formReservarTipoHTML(r)}
            <div class="alert-danger form-error-msg" hidden></div>
            <div class="acciones">
                <button type="button" class="btn btn-ghost btn-sm" data-cerrar-modal>Cancelar</button>
                <button type="submit" class="btn btn-primary btn-sm">Confirmar reserva</button>
            </div>
        </form>`
    );
}

function abrirModalSolicitar(r) {
    openModal(
        `Solicitar · ${r.nombre}`,
        `<form data-accion="solicitar" data-id="${esc(r.id)}" data-tipo="${esc(r.tipo_recurso)}">
            ${formSolicitarTipoHTML(r)}
            <div class="alert-danger form-error-msg" hidden></div>
            <div class="acciones">
                <button type="button" class="btn btn-ghost btn-sm" data-cerrar-modal>Cancelar</button>
                <button type="submit" class="btn btn-primary btn-sm">Confirmar solicitud</button>
            </div>
        </form>`
    );
}

caja.addEventListener("click", (evento) => {
    const btnReservar = evento.target.closest(".btn-reservar");
    if (btnReservar) {
        abrirModalReservar(recursos.find((r) => r.id === Number(btnReservar.dataset.id)));
        return;
    }

    const btnSolicitar = evento.target.closest(".btn-solicitar");
    if (btnSolicitar) {
        abrirModalSolicitar(recursos.find((r) => r.id === Number(btnSolicitar.dataset.id)));
    }
});

// --- Interacción dentro del modal (cerrar, chips, enviar) ------------------

document.addEventListener("click", (evento) => {
    if (evento.target.closest("[data-cerrar-modal]")) closeModal();

    const chip = evento.target.closest(".modal-body .chip-opt");
    if (chip) {
        const grupo = chip.closest("[data-chip-grupo]");
        grupo.querySelectorAll(".chip-opt").forEach((c) => c.classList.toggle("on", c === chip));
        grupo.nextElementSibling.value = chip.dataset.valor;
    }
});

document.addEventListener("submit", async (evento) => {
    const form = evento.target.closest(".modal-body form");
    if (!form) return;
    evento.preventDefault();

    if (form.dataset.accion === "reservar") return enviarReserva(form);
    if (form.dataset.accion === "solicitar") return enviarSolicitud(form);
});

// --- Reservar ----------------------------------------------------------------

async function enviarReserva(form) {
    const datos = formValues(form);
    const boton = form.querySelector('button[type="submit"]');
    const errorDiv = form.querySelector(".form-error-msg");

    setBusy(boton, true, "Reservando…");
    showFormError(errorDiv, "");

    try {
        await api.post("/reservas", {
            recurso_id: Number(form.dataset.id),
            fecha: datos.fecha,
            franja: datos.franja,
            tipo: datos.tipo || "SIMPLE",
        });
        modalBody().innerHTML = `
            <p class="alert-success">Reserva creada — queda <b>PENDIENTE</b> hasta que un custodio la confirme.</p>
            <div class="acciones"><button type="button" class="btn btn-primary btn-sm" data-cerrar-modal>Cerrar</button></div>`;
    } catch (e) {
        showFormError(errorDiv, e.message);
        setBusy(boton, false);
    }
}

// --- Solicitar (prototipo sin backend, ver js/mock-solicitudes.js) ---------

function enviarSolicitud(form) {
    const datos = formValues(form);
    const boton = form.querySelector('button[type="submit"]');
    const errorDiv = form.querySelector(".form-error-msg");
    const recurso = recursos.find((r) => r.id === Number(form.dataset.id));

    if (form.dataset.tipo === "ACADEMICO" && !datos.motivo) {
        return showFormError(errorDiv, "Contanos el motivo (curso, tesis o proyecto).");
    }

    setBusy(boton, true, "Enviando…");
    showFormError(errorDiv, "");

    const tipoSolicitud = form.dataset.tipo === "ACADEMICO" ? datos.tipo_solicitud : "SIMPLE";
    const siguientePaso =
        tipoSolicitud === "SIMPLE"
            ? `pendiente de aceptación de <b>${recurso.gestor === "CENTRO_ESTUDIANTES" ? "Custodio CE" : "Custodio Infra"}</b>`
            : "pendiente de aval del docente (próxima entrega: todavía no hay pantalla para avalar)";

    MockSolicitudes.crear({ recurso, tipoSolicitud, motivo: datos.motivo || null });
    pintarCatalogo();
    modalBody().innerHTML = `
        <p class="alert-success">Solicitud enviada — queda ${siguientePaso}.</p>
        <div class="acciones"><button type="button" class="btn btn-primary btn-sm" data-cerrar-modal>Cerrar</button></div>`;
}

cargarCatalogo();
