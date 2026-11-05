if (!requireAuth()) throw new Error("sin sesión");

renderSidebar("custodio");

const cajaActivos = document.getElementById("lista-prestamos-activos");
const buscarActivos = document.getElementById("buscar-activos");

let prestamosActivos = [];

async function init() {
    await cargarPrestamosActivos();
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
            <form class="fila-doble" style="align-items:flex-end;flex-wrap:wrap;">
                <label class="field" style="flex:1;">Comentario de devolución
                    <input type="text" name="condicion_devolucion" placeholder="Opcional">
                </label>
                <label class="field">Resultado
                    <select name="resultado">
                        <option value="OK">En buen estado</option>
                        <option value="DANADO">Dañado</option>
                        <option value="PERDIDO">Perdido</option>
                    </select>
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
            danado: datos.resultado === "DANADO",
            perdido: datos.resultado === "PERDIDO",
        });
        await cargarPrestamosActivos();
    } catch (e) {
        showFormError(errorDiv, e.message || "Error al registrar la devolución.");
        setBusy(btn, false);
    }
});

init();
