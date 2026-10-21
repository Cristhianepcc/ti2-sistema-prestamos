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

function tarjetaRecurso(r) {
    let accion = "";
    if (puedeReservar(r)) {
        accion = `<button type="button" class="btn btn-success btn-sm btn-reservar" data-id="${esc(r.id)}">Reservar</button>`;
    } else if (r.tipo_recurso === "DEPORTIVO" && r.disponible) {
        accion = `<p class="nota-directa">Préstamo directo · mismo día</p>`;
    }

    return `
    <div class="tarjeta">
        <div class="cuerpo">
            <div class="etiquetas">
                <span class="chip-tipo">${esc(r.gestor)}</span>
                <span class="chip-tipo">${esc(ETIQUETA_TIPO[r.tipo_recurso])}</span>
            </div>
            <div class="nombre">${esc(r.nombre)}</div>
            <p class="detalle">${esc(r.descripcion)} · Código: ${esc(r.codigo)}</p>
            ${detalleSegunTipo(r)}
            <div class="fila-final">
                ${badgeEstado(r.estado)}
                ${accion}
            </div>
        </div>
        <div class="form-reservar" data-id="${esc(r.id)}" hidden>
            <form>
                <div class="fila">
                    <label class="field">Fecha
                        <input type="date" name="fecha" required>
                    </label>
                    <label class="field">Franja
                        <input type="text" name="franja" placeholder="ej: 10:00-12:00" required>
                    </label>
                </div>
                <div class="alert-danger form-error-msg" hidden></div>
                <div class="acciones">
                    <button type="button" class="btn btn-ghost btn-sm btn-cancelar-reserva">Cancelar</button>
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
        return `<p class="detalle">${esc(r.autor)} · ISBN ${esc(r.isbn)}</p>`;
    }
    if (r.tipo_recurso === "DEPORTIVO") {
        return `<p class="detalle">${esc(r.tipo_deportivo)}</p>`;
    }
    return `<p class="detalle">Patrimonio ${esc(r.codigo_patrimonial)}
            ${r.requiere_aval ? "· requiere aval" : ""}</p>`;
}

inputBuscador.addEventListener("input", pintarCatalogo);

filtrosTipo.addEventListener("click", (evento) => {
    const chip = evento.target.closest(".filter");
    if (!chip) return;
    tipoActivo = chip.dataset.tipo;
    filtrosTipo.querySelectorAll(".filter").forEach((f) => f.classList.toggle("on", f === chip));
    pintarCatalogo();
});

// --- Reservar ---------------------------------------------------------------

caja.addEventListener("click", (evento) => {
    const btnReservar = evento.target.closest(".btn-reservar");
    if (btnReservar) {
        btnReservar.closest(".tarjeta").querySelector(".form-reservar").hidden = false;
        btnReservar.hidden = true;
        return;
    }

    const btnCancelar = evento.target.closest(".btn-cancelar-reserva");
    if (btnCancelar) {
        const tarjeta = btnCancelar.closest(".tarjeta");
        tarjeta.querySelector(".form-reservar").hidden = true;
        const boton = tarjeta.querySelector(".btn-reservar");
        if (boton) boton.hidden = false;
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
        contenedor.innerHTML = `<p class="alert-success">Reserva creada — queda <b>PENDIENTE</b> hasta que un custodio la confirme.</p>`;
    } catch (e) {
        showFormError(errorDiv, e.message);
        setBusy(boton, false);
    }
});

cargarCatalogo();
