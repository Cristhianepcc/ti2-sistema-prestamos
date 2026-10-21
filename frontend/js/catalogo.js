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

// Deportivo es préstamo directo del mismo día (docs/00-contexto-alcance-propuesta.md
// §5): no admite reserva anticipada. Libro/Académico sí, pero solo si NO está
// disponible ahora mismo (si está libre, el backend rechaza la reserva con 409).
function puedeReservar(r) {
    return r.tipo_recurso !== "DEPORTIVO" && !r.disponible && r.estado !== "MANTENIMIENTO";
}

// Ícono genérico de "espacio para foto" — placeholder hasta que la API
// tenga un campo de imagen real (no hay fotos de los recursos todavía).
const ICONO_IMAGEN_PENDIENTE =
    '<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>';

function tarjetaRecurso(r) {
    let boton;
    if (puedeReservar(r)) {
        boton = `<button type="button" class="btn btn-primary btn-sm tp-boton btn-reservar" data-id="${esc(r.id)}">Reservar</button>`;
    } else if (r.tipo_recurso === "DEPORTIVO" && r.disponible) {
        boton = `<button type="button" class="btn btn-sm tp-boton" disabled>Préstamo directo</button>`;
    } else {
        boton = `<button type="button" class="btn btn-sm tp-boton" disabled>${esc(ETIQUETA_ESTADO[r.estado]?.texto || r.estado)}</button>`;
    }

    return `
    <div class="tarjeta">
        <div class="tp-main">
            <div class="tp-media">
                ${ICONO_IMAGEN_PENDIENTE}
                <span class="tp-badge">${badgeEstado(r.estado)}</span>
            </div>
            <div class="tp-nombre">${esc(r.nombre)}</div>
            <p class="tp-detalle">${esc(r.codigo)} · ${detalleSegunTipo(r)}</p>
            ${boton}
        </div>
        <div class="tp-etiqueta"><span>${esc(ETIQUETA_TIPO[r.tipo_recurso])}</span></div>
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

// --- Aviso de éxito (banner que se oculta solo) -------------------------------

const avisoExito = document.getElementById("aviso-exito");
let avisoTimeout = null;

function mostrarAvisoExito(mensaje) {
    avisoExito.textContent = mensaje;
    avisoExito.hidden = false;
    clearTimeout(avisoTimeout);
    avisoTimeout = setTimeout(() => {
        avisoExito.hidden = true;
    }, 5000);
}

// --- Modal de reserva ---------------------------------------------------------

const modal = document.getElementById("modal-reservar");
const formModal = document.getElementById("form-modal-reservar");
const inputFecha = formModal.querySelector('input[name="fecha"]');
const errorModal = formModal.querySelector(".form-error-msg");
let recursoReservando = null;

function hoyISO() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function abrirModal(recursoId) {
    recursoReservando = recursos.find((r) => String(r.id) === String(recursoId));
    if (!recursoReservando) return;

    document.getElementById("modal-recurso-nombre").textContent =
        `${recursoReservando.nombre} · ${recursoReservando.codigo}`;
    formModal.reset();
    inputFecha.min = hoyISO();
    showFormError(errorModal, "");
    modal.hidden = false;
}

function cerrarModal() {
    modal.hidden = true;
    recursoReservando = null;
}

caja.addEventListener("click", (evento) => {
    const btnReservar = evento.target.closest(".btn-reservar");
    if (btnReservar) abrirModal(btnReservar.dataset.id);
});

document.getElementById("btn-cerrar-modal").addEventListener("click", cerrarModal);

// Cerrar al hacer clic fuera del cuadro, o con Escape.
modal.addEventListener("click", (evento) => {
    if (evento.target === modal) cerrarModal();
});
document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape" && !modal.hidden) cerrarModal();
});

formModal.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    if (!recursoReservando) return;

    const datos = formValues(formModal);
    const boton = formModal.querySelector('button[type="submit"]');

    if (datos.hora_fin <= datos.hora_inicio) {
        showFormError(errorModal, "La hora de fin debe ser posterior a la de inicio.");
        return;
    }

    setBusy(boton, true, "Reservando…");
    showFormError(errorModal, "");

    const franja = `${datos.hora_inicio}-${datos.hora_fin}`;
    const nombreRecurso = recursoReservando.nombre;

    try {
        await api.post("/reservas", {
            recurso_id: recursoReservando.id,
            fecha: datos.fecha,
            franja,
        });
        cerrarModal();
        await cargarCatalogo();
        mostrarAvisoExito(`Reserva creada para ${nombreRecurso} — queda PENDIENTE hasta que un custodio la confirme.`);
    } catch (e) {
        showFormError(errorModal, e.message);
    } finally {
        setBusy(boton, false);
    }
});

cargarCatalogo();
