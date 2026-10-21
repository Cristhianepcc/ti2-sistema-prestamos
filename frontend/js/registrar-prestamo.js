if (!requireAuth()) throw new Error("sin sesión");

const selectRecursos = document.getElementById("select-recurso");
const formRegistrar = document.getElementById("form-registrar-prestamo");
const cajaActivos = document.getElementById("lista-prestamos-activos");

async function init() {
    await cargarRecursosDisponibles();
    await cargarPrestamosActivos();
}

async function cargarRecursosDisponibles() {
    try {
        const recursos = await api.get("/recursos?disponible=true");
        selectRecursos.innerHTML = '<option value="">Seleccione un recurso...</option>' + 
            recursos.map(r => `<option value="${r.id}">${esc(r.nombre)} (${esc(r.codigo)}) - ${esc(r.tipo_recurso)}</option>`).join("");
    } catch (e) {
        console.error("Error al cargar recursos:", e);
    }
}

async function cargarPrestamosActivos() {
    showLoading(cajaActivos);
    try {
        const prestamos = await api.get("/prestamos?estado=ACTIVO");
        renderList(cajaActivos, prestamos, tarjetaPrestamoActivo, "No hay préstamos activos en este momento.");
    } catch (e) {
        showError(cajaActivos, e.message);
    }
}

function tarjetaPrestamoActivo(p) {
    return `
    <div class="card bg-white border-0 shadow-sm mb-3" id="prestamo-${p.id}">
        <div class="card-body">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <h6 class="fw-bold mb-1">Recurso ID: ${esc(p.recurso_id)}</h6>
                    <p class="small text-muted mb-1">Prestatario ID: ${esc(p.prestatario_id)} · Tipo: ${esc(p.tipo_prestamo)}</p>
                    <p class="small text-muted mb-2">Entrega: ${esc(p.condicion_entrega)}</p>
                    ${badgePrestamo(p.estado)}
                </div>
                <div>
                    <button class="btn btn-outline-danger btn-sm" onclick="toggleFormDevolucion('${p.id}')">Registrar Devolución</button>
                </div>
            </div>
            <!-- Formulario de devolución inline -->
            <div id="form-dev-${p.id}" class="mt-3 pt-2 border-top d-none">
                <form onsubmit="registrarDevolucion(event, '${p.id}')">
                    <div class="mb-2">
                        <label class="form-label small fw-bold">Condición de Devolución</label>
                        <input type="text" name="condicion_devolucion" class="form-control form-control-sm" placeholder="Estado en que se devuelve" required>
                    </div>
                    <div class="form-error-msg text-danger small mb-2 d-none"></div>
                    <div class="d-flex justify-content-end gap-2">
                        <button type="button" class="btn btn-secondary btn-sm" onclick="toggleFormDevolucion('${p.id}')">Cancelar</button>
                        <button type="submit" class="btn btn-primary btn-sm">Confirmar Devolución</button>
                    </div>
                </form>
            </div>
        </div>
    </div>`;
}

window.toggleFormDevolucion = function(id) {
    const el = document.getElementById(`form-dev-${id}`);
    if (el) el.classList.toggle("d-none");
};

window.registrarDevolucion = async function(event, prestamoId) {
    event.preventDefault();
    const form = event.target;
    const datos = formValues(form);
    const btn = form.querySelector('button[type="submit"]');
    const errorDiv = form.querySelector('.form-error-msg');

    setBusy(btn, true, "Registrando...");
    showFormError(errorDiv, "");

    try {
        await api.post(`/prestamos/${prestamoId}/devolucion`, {
            condicion_devolucion: datos.condicion_devolucion
        });
        await cargarPrestamosActivos();
        await cargarRecursosDisponibles(); 
    } catch (e) {
        showFormError(errorDiv, e.message || "Error al registrar la devolución.");
    } finally {
        setBusy(btn, false);
    }
};

formRegistrar.addEventListener("submit", async (e) => {
    e.preventDefault();
    const datos = formValues(formRegistrar);
    const btn = formRegistrar.querySelector('button[type="submit"]');
    const errorDiv = formRegistrar.querySelector('.form-error-msg');

    setBusy(btn, true, "Registrando entrega...");
    showFormError(errorDiv, "");

    const payload = {
        recurso_id: datos.recurso_id,
        prestatario_id: parseInt(datos.prestatario_id),
        tipo_prestamo: datos.tipo_prestamo,
        modalidad_uso: datos.modalidad_uso,
        condicion_entrega: datos.condicion_entrega
    };

    if (datos.garantia_tipo) {
        payload.garantia = {
            tipo: datos.garantia_tipo,
            valor: parseFloat(datos.garantia_valor || 0)
        };
    }

    try {
        await api.post("/prestamos", payload);
        formRegistrar.reset();
        await init();
    } catch (err) {
        showFormError(errorDiv, err.message || "Error al registrar la entrega.");
    } finally {
        setBusy(btn, false);
    }
});

document.getElementById("btn-cerrar-sesion").addEventListener("click", () => api.logout());

init();
