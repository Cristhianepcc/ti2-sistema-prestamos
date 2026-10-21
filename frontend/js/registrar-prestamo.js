if (!requireAuth()) throw new Error("sin sesión");

renderSidebar("custodio");

const selectRecursos = document.getElementById("select-recurso");
const formRegistrar = document.getElementById("form-registrar-prestamo");
const cajaActivos = document.getElementById("lista-prestamos-activos");
const buscarActivos = document.getElementById("buscar-activos");

let prestamosActivos = [];

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
    showLoading(cajaActivos, 6);
    try {
        prestamosActivos = await api.get("/prestamos?estado=ACTIVO");
        pintarActivos();
    } catch (e) {
        showError(cajaActivos, e.message, 6);
    }
}

function pintarActivos() {
    const texto = buscarActivos.value.toLowerCase();
    const filtrados = prestamosActivos.filter((p) => {
        const nombre = p.recurso ? p.recurso.nombre : "";
        const codigo = p.recurso ? p.recurso.codigo : "";
        return (
            nombre.toLowerCase().includes(texto) ||
            codigo.toLowerCase().includes(texto) ||
            String(p.prestatario_id).includes(texto)
        );
    });
    const filas = filtrados.map(filaPrestamoActivo).join("");
    cajaActivos.innerHTML = filas || `<tr><td colspan="6"><div class="estado-vacio">No hay préstamos activos en este momento.</div></td></tr>`;
}

function filaPrestamoActivo(p) {
    const nombre = p.recurso ? p.recurso.nombre : `Recurso #${p.recurso_id}`;
    const codigo = p.recurso ? p.recurso.codigo : "";
    const iniciales = String(p.prestatario_id).slice(0, 2);

    return `
    <tr id="prestamo-${esc(p.id)}">
        <td><b>${esc(nombre)}</b><div class="sub">${esc(codigo)}</div></td>
        <td><div class="who-cell"><span class="avatar">${esc(iniciales)}</span>ID ${esc(p.prestatario_id)}</div></td>
        <td>${esc(formatearFechaCorta(p.fecha_entrega))}</td>
        <td>${esc(formatearFechaCorta(p.fecha_limite))}</td>
        <td>${badgePrestamo(p.estado)}</td>
        <td><button type="button" class="btn btn-danger-ghost btn-sm btn-devolver" data-id="${esc(p.id)}">Registrar devolución</button></td>
    </tr>
    <tr class="fila-devolucion" data-id="${esc(p.id)}" hidden>
        <td colspan="6">
            <form class="fila-doble" style="align-items:flex-end;">
                <label class="field" style="flex:1;">Condición de devolución
                    <input type="text" name="condicion_devolucion" placeholder="Estado en que se devuelve" required>
                </label>
                <button type="button" class="btn btn-ghost btn-sm btn-cancelar-devolucion">Cancelar</button>
                <button type="submit" class="btn btn-primary btn-sm">Confirmar devolución</button>
            </form>
            <div class="alert-danger form-error-msg" hidden></div>
        </td>
    </tr>`;
}

function formatearFechaCorta(texto) {
    const [anio, mes, dia] = String(texto).slice(0, 10).split("-").map(Number);
    return new Date(anio, mes - 1, dia).toLocaleDateString("es-PE", { day: "numeric", month: "short" });
}

buscarActivos.addEventListener("input", pintarActivos);

cajaActivos.addEventListener("click", (evento) => {
    const btnDevolver = evento.target.closest(".btn-devolver");
    if (btnDevolver) {
        cajaActivos.querySelector(`.fila-devolucion[data-id="${btnDevolver.dataset.id}"]`).hidden = false;
        return;
    }
    const btnCancelar = evento.target.closest(".btn-cancelar-devolucion");
    if (btnCancelar) {
        btnCancelar.closest(".fila-devolucion").hidden = true;
    }
});

cajaActivos.addEventListener("submit", async (evento) => {
    const fila = evento.target.closest(".fila-devolucion");
    if (!fila) return;
    evento.preventDefault();

    const form = evento.target;
    const datos = formValues(form);
    const btn = form.querySelector('button[type="submit"]');
    const errorDiv = fila.querySelector(".form-error-msg");

    setBusy(btn, true, "Registrando...");
    showFormError(errorDiv, "");

    try {
        await api.post(`/prestamos/${fila.dataset.id}/devolucion`, {
            condicion_devolucion: datos.condicion_devolucion,
        });
        await cargarPrestamosActivos();
        await cargarRecursosDisponibles();
    } catch (e) {
        showFormError(errorDiv, e.message || "Error al registrar la devolución.");
        setBusy(btn, false);
    }
});

// --- Chips (tipo_prestamo / modalidad_uso) ----------------------------------

formRegistrar.querySelectorAll("[data-chip-grupo]").forEach((grupo) => {
    grupo.addEventListener("click", (evento) => {
        const chip = evento.target.closest(".chip-opt");
        if (!chip) return;
        grupo.querySelectorAll(".chip-opt").forEach((c) => c.classList.toggle("on", c === chip));
        grupo.nextElementSibling.value = chip.dataset.valor;
    });
});

formRegistrar.addEventListener("submit", async (e) => {
    e.preventDefault();
    const datos = formValues(formRegistrar);
    const btn = formRegistrar.querySelector('button[type="submit"]');
    const errorDiv = formRegistrar.querySelector(".form-error-msg");

    setBusy(btn, true, "Registrando entrega...");
    showFormError(errorDiv, "");

    const payload = {
        recurso_id: datos.recurso_id,
        prestatario_id: parseInt(datos.prestatario_id),
        tipo_prestamo: datos.tipo_prestamo,
        modalidad_uso: datos.modalidad_uso,
        condicion_entrega: datos.condicion_entrega,
    };

    if (datos.garantia_tipo) {
        payload.garantia = {
            tipo: datos.garantia_tipo,
            valor: parseFloat(datos.garantia_valor || 0),
        };
    }

    try {
        await api.post("/prestamos", payload);
        formRegistrar.reset();
        // reset() vuelve los <input hidden> a su valor por defecto en el HTML;
        // los chips visuales no son controles de formulario, hay que
        // resincronizarlos a mano con ese mismo valor.
        formRegistrar.querySelectorAll("[data-chip-grupo]").forEach((grupo) => {
            const valorPorDefecto = grupo.nextElementSibling.value;
            grupo.querySelectorAll(".chip-opt").forEach((c) => {
                c.classList.toggle("on", c.dataset.valor === valorPorDefecto);
            });
        });
        await init();
    } catch (err) {
        showFormError(errorDiv, err.message || "Error al registrar la entrega.");
    } finally {
        setBusy(btn, false);
    }
});

init();
