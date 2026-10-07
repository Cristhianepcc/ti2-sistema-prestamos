if (!requireAuth()) throw new Error("sin sesión");

const caja = document.getElementById("catalogo");
const inputBuscador = document.getElementById("input-buscador");

let recursos = [];

async function cargarCatalogo() {
    showLoading(caja);
    try {
        recursos = await api.get("/recursos?disponible=true");
        pintarCatalogo(recursos);
    } catch (e) {
        showError(caja, e.message);
    }
}

function pintarCatalogo(lista) {
    renderList(caja, lista, tarjetaRecurso, "No se encontraron recursos.");
}

function tarjetaRecurso(r) {
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
                <button class="btn btn-success btn-sm px-4 rounded-pill d-block mt-2">Solicitar</button>
            </div>
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

document.getElementById("btn-cerrar-sesion").addEventListener("click", () => api.logout());

cargarCatalogo();
