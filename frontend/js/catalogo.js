if (!requireAuth()) throw new Error("sin sesión");

if (hasRole("CUSTODIO_CE", "CUSTODIO_INFRA")) {
    document.getElementById("link-panel-custodio").hidden = false;
}

const caja = document.getElementById("catalogo");
const inputBuscador = document.getElementById("input-buscador");

let recursos = [];

async function cargarCatalogo() {
    showLoading(caja);
    try {
        // Sin filtro de disponibilidad: hay que poder VER (y reservar) los
        // recursos ocupados, no solo los libres.
        recursos = await api.get("/recursos");
        pintarCatalogo(recursos);
    } catch (e) {
        showError(caja, e.message);
    }
}

function pintarCatalogo(lista) {
    renderList(caja, lista, tarjetaRecurso, "No se encontraron recursos.");
}

// Deportivo es préstamo directo del mismo día (docs/00-contexto-alcance-propuesta.md
// §5): no admite reserva anticipada. Libro/Académico sí, pero solo si NO está
// disponible ahora mismo (si está libre, el backend rechaza la reserva con 409).
function puedeReservar(r) {
    return r.tipo_recurso !== "DEPORTIVO" && !r.disponible && r.estado !== "MANTENIMIENTO";
}

function tarjetaRecurso(r) {
    let accion = "";
    if (puedeReservar(r)) {
        accion = `<button type="button" class="btn btn-success btn-sm px-4 rounded-pill d-block mt-2 btn-reservar" data-id="${esc(r.id)}">Reservar</button>`;
    } else if (r.tipo_recurso === "DEPORTIVO" && r.disponible) {
        accion = `<p class="small text-muted mb-0 mt-2">Préstamo directo · mismo día</p>`;
    }

    return `
    <div class="card shadow-sm border-0 bg-light mb-3">
        <div class="card-body d-flex justify-content-between align-items-center">
            <div>
                <span class="badge bg-secondary mb-2">${esc(r.gestor)}</span>
                <span class="badge bg-info text-dark mb-2">${esc(ETIQUETA_TIPO[r.tipo_recurso])}</span>
                <h5 class="card-title mb-1">${esc(r.nombre)}</h5>
                <p class="card-text text-muted small mb-0">${esc(r.descripcion)} · Código: ${esc(r.codigo)}</p>
                ${detalleSegunTipo(r)}
            </div>
            <div class="text-end">
                ${badgeEstado(r.estado)}
                ${accion}
            </div>
        </div>
        <div class="form-reservar d-none border-top px-3 py-3" data-id="${esc(r.id)}">
            <form class="row g-2 align-items-end">
                <div class="col-6">
                    <label class="form-label small fw-bold mb-1">Fecha</label>
                    <input type="date" name="fecha" class="form-control form-control-sm" required>
                </div>
                <div class="col-6">
                    <label class="form-label small fw-bold mb-1">Franja</label>
                    <input type="text" name="franja" class="form-control form-control-sm" placeholder="ej: 10:00-12:00" required>
                </div>
                <div class="col-12 form-error-msg alert alert-danger d-none py-1 px-2 small mb-0"></div>
                <div class="col-12 d-flex justify-content-end gap-2 mt-2">
                    <button type="button" class="btn btn-outline-secondary btn-sm btn-cancelar-reserva">Cancelar</button>
                    <button type="submit" class="btn btn-primary btn-sm">Confirmar reserva</button>
                </div>
            </form>
        </div>
    </div>`;
}

// ⚠️ Las claves de un subtipo NO existen en los otros: un DEPORTIVO no trae la
// clave `autor` ni siquiera en null. Hay que ramificar por tipo_recurso.
function detalleSegunTipo(r) {
    if (r.tipo_recurso === "LIBRO") {
        return `<p class="small mb-0">${esc(r.autor)} · ISBN ${esc(r.isbn)}</p>`;
    }
    if (r.tipo_recurso === "DEPORTIVO") {
        return `<p class="small mb-0">${esc(r.tipo_deportivo)}</p>`;
    }
    return `<p class="small mb-0">Patrimonio ${esc(r.codigo_patrimonial)}
            ${r.requiere_aval ? "· requiere aval" : ""}</p>`;
}

inputBuscador.addEventListener("input", () => {
    const texto = inputBuscador.value.toLowerCase();
    const filtrados = recursos.filter((r) =>
        r.nombre.toLowerCase().includes(texto) ||
        (r.descripcion || "").toLowerCase().includes(texto) ||
        r.tipo_recurso.toLowerCase().includes(texto)
    );
    pintarCatalogo(filtrados);
});

// --- Reservar ---------------------------------------------------------------

caja.addEventListener("click", (evento) => {
    const btnReservar = evento.target.closest(".btn-reservar");
    if (btnReservar) {
        btnReservar.closest(".card").querySelector(".form-reservar").classList.remove("d-none");
        btnReservar.classList.add("d-none");
        return;
    }

    const btnCancelar = evento.target.closest(".btn-cancelar-reserva");
    if (btnCancelar) {
        const card = btnCancelar.closest(".card");
        card.querySelector(".form-reservar").classList.add("d-none");
        card.querySelector(".btn-reservar")?.classList.remove("d-none");
    }
});

caja.addEventListener("submit", async (evento) => {
    const contenedor = evento.target.closest(".form-reservar");
    if (!contenedor) return;
    evento.preventDefault();

    const form = evento.target;
    const datos = formValues(form);
    const boton = form.querySelector('button[type="submit"]');
    const errorDiv = form.querySelector(".form-error-msg");

    setBusy(boton, true, "Reservando…");
    showFormError(errorDiv, "");

    try {
        await api.post("/reservas", {
            recurso_id: Number(contenedor.dataset.id),
            fecha: datos.fecha,
            franja: datos.franja,
        });
        contenedor.innerHTML = `<p class="text-success small mb-0 py-1">Reserva creada — queda <b>PENDIENTE</b> hasta que un custodio la confirme.</p>`;
    } catch (e) {
        showFormError(errorDiv, e.message);
        setBusy(boton, false);
    }
});

document.getElementById("btn-cerrar-sesion").addEventListener("click", () => api.logout());

cargarCatalogo();
