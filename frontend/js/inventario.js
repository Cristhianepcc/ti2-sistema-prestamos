// Inventario (RF1): lista los recursos del propio gestor de un custodio, o
// el catálogo completo si es el administrador del sistema, y da de alta
// nuevos. El endpoint POST /api/recursos ya existía en el backend
// (routers/recurso.py) pero no tenía ninguna pantalla que lo usara.

if (!requireAuth()) throw new Error("sin sesión");

// El sidebar no ofrece esta página a otros roles, pero se puede llegar por URL
// y el POST/PUT del backend igual responde 403. Se corta acá para no mostrar
// una pantalla que no va a servir de nada.
if (!hasRole("CUSTODIO_CE", "CUSTODIO_INFRA", "ADMINISTRADOR_SISTEMA")) {
    location.href = "inicio.html";
    throw new Error("solo custodios o administradores");
}

renderSidebar("inventario");

const esAdmin = hasRole("ADMINISTRADOR_SISTEMA");

// Cada custodio administra solo lo suyo: el CE los libros y deportivos,
// Infraestructura los académicos (routers/recurso.py:77, y la constraint
// chk_gestor_tipo de la base). Se refleja la misma regla acá para no ofrecer
// opciones que el backend va a rechazar con 403. Un usuario con los dos roles
// de custodio ve la unión. El administrador del sistema no está atado a un
// gestor (recurso.py:_exigir_gestor_propio hace la misma excepción): ve y
// administra los tres tipos.
const TIPOS_DEL_CE = ["LIBRO", "DEPORTIVO"];
const TIPOS_DE_INFRA = ["ACADEMICO"];

const tiposPermitidos = esAdmin
    ? [...TIPOS_DEL_CE, ...TIPOS_DE_INFRA]
    : [
          ...(hasRole("CUSTODIO_CE") ? TIPOS_DEL_CE : []),
          ...(hasRole("CUSTODIO_INFRA") ? TIPOS_DE_INFRA : []),
      ];

const gestoresPropios = esAdmin
    ? ["CENTRO_ESTUDIANTES", "INFRAESTRUCTURA"]
    : [
          ...(hasRole("CUSTODIO_CE") ? ["CENTRO_ESTUDIANTES"] : []),
          ...(hasRole("CUSTODIO_INFRA") ? ["INFRAESTRUCTURA"] : []),
      ];

// Campos propios de cada subtipo (ver schemas/recurso.py). Los comunes
// (codigo, nombre, descripcion, ubicacion) van en el formulario base.
const CAMPOS_POR_TIPO = {
    LIBRO: [
        { name: "isbn", label: "ISBN" },
        { name: "autor", label: "Autor" },
        { name: "categoria", label: "Categoría", placeholder: "Ej. Software, Redes" },
    ],
    DEPORTIVO: [
        { name: "tipo_deportivo", label: "Tipo deportivo", placeholder: "Ej. Fútbol, Vóley" },
    ],
    ACADEMICO: [
        { name: "codigo_patrimonial", label: "Código patrimonial" },
        { name: "requiere_aval", label: "Requiere aval del docente", tipo: "checkbox" },
    ],
};

const tabla = document.getElementById("inventario");
const inputBuscador = document.getElementById("buscar");
const resumen = document.getElementById("resumen");

let recursos = [];

// --- Listado ----------------------------------------------------------------

// El dato que distingue al recurso dentro de su tipo, para la segunda línea
// de la celda del nombre.
function detalleSubtipo(r) {
    if (r.tipo_recurso === "LIBRO") return r.autor || r.isbn || "";
    if (r.tipo_recurso === "DEPORTIVO") return r.tipo_deportivo || "";
    return r.codigo_patrimonial || "";
}

// "Dar de baja" no tiene sentido si ya está de baja, ni mientras está
// prestado (se actualiza solo al devolverlo, ver routers/recurso.py).
// `opciones.soloEnSuGrupo`: este recurso no tiene más copias (ver
// pintarInventario), así que "+ Copia" va en su propia fila en vez de en un
// encabezado de grupo (que no existe para un grupo de 1).
// `opciones.enGrupo`: lo contrario — sí tiene copias y cuelga de un
// `filaGrupo` arriba. Marca la fila con `fila-miembro` (ver styles.css) para
// que quede claro que pertenece a ese grupo y no es un ítem suelto más; sin
// esto, una fila de grupo (LIB-002) y una suelta (LIB-004) se veían idénticas.
function filaRecurso(r, opciones = {}) {
    const detalle = detalleSubtipo(r);
    const sub = detalle ? `<div class="sub">${esc(detalle)}</div>` : "";
    const btnBaja =
        r.estado !== "BAJA" && r.estado !== "PRESTADO"
            ? `<button type="button" class="btn btn-danger-ghost btn-sm btn-dar-baja" data-id="${esc(r.id)}">Dar de baja</button>`
            : "";
    const btnCopia = opciones.soloEnSuGrupo
        ? `<button type="button" class="btn btn-ghost btn-sm btn-agregar-copia" data-id="${esc(r.id)}">+ Copia</button>`
        : "";
    // El backend ahora permite a cada custodio ver el historial de su propio
    // gestor (y al admin, de cualquiera) — justo lo que esta tabla ya muestra
    // por fila, así que el botón no necesita condición de rol.
    const btnHistorial = `<button type="button" class="btn btn-ghost btn-sm btn-ver-historial" data-codigo="${esc(r.codigo)}">Ver historial</button>`;
    const clase = opciones.enGrupo ? ` class="fila-miembro"` : "";
    const conector = opciones.enGrupo ? `<span class="conector">↳</span>` : "";
    return `<tr${clase}>
        <td>${conector}<b>${esc(r.codigo)}</b></td>
        <td>${esc(r.nombre)}${sub}</td>
        <td>${esc(ETIQUETA_TIPO[r.tipo_recurso] || r.tipo_recurso)}</td>
        <td>${esc(r.ubicacion || "—")}</td>
        <td>${badgeEstado(r.estado)}</td>
        <td><div class="acciones-tabla">
            <button type="button" class="btn btn-ghost btn-sm btn-editar" data-id="${esc(r.id)}">Editar</button>
            ${btnBaja}
            ${btnCopia}
            ${btnHistorial}
        </div></td>
    </tr>`;
}

function pintarResumen(propios) {
    const c = contarPorEstado(propios);
    resumen.textContent =
        `${propios.length} recursos · ${c.DISPONIBLE} disponibles · ` +
        `${c.PRESTADO} prestados · ${c.MANTENIMIENTO} en mantenimiento · ` +
        `${c.BAJA} de baja`;
}

// Varias copias del mismo recurso (mismo nombre, mismo tipo) se agrupan bajo
// una sola fila de resumen; un recurso sin más copias no lleva encabezado,
// para no duplicar una fila "1 unidad" por cada ítem único del catálogo.
function filaGrupo(grupo) {
    const primero = grupo.unidades[0];
    const c = contarPorEstado(grupo.unidades);
    return `<tr class="fila-grupo">
        <td colspan="6">
            <b>${esc(primero.nombre)}</b> · ${esc(ETIQUETA_TIPO[primero.tipo_recurso] || primero.tipo_recurso)}
            · ${grupo.unidades.length} unidades · ${c.DISPONIBLE} disponibles ·
            ${c.PRESTADO} prestadas · ${c.MANTENIMIENTO} en mantenimiento · ${c.BAJA} de baja
            <button type="button" class="btn btn-ghost btn-sm btn-agregar-copia" data-id="${esc(primero.id)}">+ Agregar copia</button>
        </td>
    </tr>`;
}

function pintarInventario() {
    const propios = recursos.filter((r) => gestoresPropios.includes(r.gestor));
    pintarResumen(propios);

    const texto = inputBuscador.value.toLowerCase();
    const filtrados = propios.filter(
        (r) =>
            r.nombre.toLowerCase().includes(texto) ||
            r.codigo.toLowerCase().includes(texto)
    );

    if (filtrados.length === 0) {
        return showEmpty(tabla, "No hay recursos que coincidan.", 6);
    }

    tabla.innerHTML = agruparPorNombre(filtrados)
        .map((grupo) =>
            grupo.unidades.length > 1
                ? filaGrupo(grupo) +
                  grupo.unidades.map((r) => filaRecurso(r, { enGrupo: true })).join("")
                : filaRecurso(grupo.unidades[0], { soloEnSuGrupo: true })
        )
        .join("");
}

// --- Historial de un recurso (modal) -----------------------------------------

function parseFechaLocal(texto) {
    const [anio, mes, dia] = String(texto).slice(0, 10).split("-").map(Number);
    return new Date(anio, mes - 1, dia);
}

function formatearFecha(texto) {
    return parseFechaLocal(texto).toLocaleDateString("es-PE", {
        day: "numeric",
        month: "short",
        year: "numeric",
    });
}

// El motivo (`condicion_devolucion`, texto libre que escribe el custodio al
// devolver) va pegado al badge: separarlos en columnas distintas no deja
// claro que uno es la explicación del otro.
function celdaIncidencia(item) {
    const motivo = item.condicion_devolucion
        ? ` — ${esc(item.condicion_devolucion)}`
        : "";
    if (item.perdido) return `<span class="badge danger">Perdido</span>${motivo}`;
    if (item.danado) return `<span class="badge warn">Dañado</span>${motivo}`;
    return item.condicion_devolucion ? esc(item.condicion_devolucion) : "—";
}

function filaHistorialRecurso(item) {
    return `<tr>
        <td>${esc(item.prestatario.nombres)} <span class="hint">${esc(item.prestatario.codigo)}</span></td>
        <td>${esc(formatearFecha(item.fecha_entrega))}</td>
        <td>${esc(formatearFecha(item.fecha_limite))}</td>
        <td>${item.fecha_devolucion ? esc(formatearFecha(item.fecha_devolucion)) : "—"}</td>
        <td>${celdaIncidencia(item)}</td>
    </tr>`;
}

// Quiénes se prestaron este implemento, cuándo, y si alguna devolución quedó
// marcada como dañada o perdida. `limite=50`: suficiente para el vistazo
// rápido de un modal; si el recurso tiene más historial que eso, se avisa en
// vez de paginar (no tiene sentido una paginación completa acá dentro).
async function abrirModalHistorial(codigo) {
    openModal(`Historial · ${codigo}`, `<p class="hint">Cargando…</p>`, { ancho: true });
    try {
        const r = await api.get(`/reportes/recursos/${encodeURIComponent(codigo)}/historial?limite=50`);
        const encabezado = `<p class="hint"><b>${esc(r.recurso.nombre)}</b> · ${esc(r.recurso.codigo)} · ${badgeEstado(r.recurso.estado)}</p>`;
        const cuerpo = r.items.length
            ? `<div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Prestatario</th>
                            <th>Entregado</th>
                            <th>Vence</th>
                            <th>Devuelto</th>
                            <th>Incidencia</th>
                        </tr>
                    </thead>
                    <tbody>${r.items.map(filaHistorialRecurso).join("")}</tbody>
                </table>
            </div>
            ${r.total > r.items.length ? `<p class="hint">Mostrando los ${r.items.length} préstamos más recientes de ${r.total}.</p>` : ""}`
            : `<p class="hint">Este recurso no tiene préstamos registrados.</p>`;
        modalBody().innerHTML = encabezado + cuerpo;
    } catch (e) {
        modalBody().innerHTML = `<p class="alert-danger">${esc(e.message)}</p>`;
    }
}

async function cargarInventario() {
    showLoading(tabla, 6);
    try {
        // Se pide el catálogo completo y se filtra por gestor en el cliente: la
        // API no tiene filtro por gestor todavía (routers/recurso.py acepta
        // tipo/estado/disponible/q).
        recursos = await api.get("/recursos");
        pintarInventario();
    } catch (e) {
        showError(tabla, e.message, 6);
    }
}

inputBuscador.addEventListener("input", pintarInventario);

// --- Alta de un recurso -----------------------------------------------------

// `valores`: para precargar el formulario de edición con los datos actuales
// del recurso (vacío al dar de alta, donde no hay nada que precargar).
function camposTipoHTML(tipo, valores = {}) {
    return CAMPOS_POR_TIPO[tipo]
        .map((c) => {
            if (c.tipo === "checkbox") {
                const marcado = valores[c.name] ? "checked" : "";
                return `<label class="field field-check">
                    <input type="checkbox" name="${c.name}" value="true" ${marcado}>
                    <span>${esc(c.label)}</span>
                </label>`;
            }
            return `<label class="field">${esc(c.label)}
                <input type="text" name="${c.name}" placeholder="${esc(c.placeholder || "")}" value="${esc(valores[c.name] ?? "")}">
            </label>`;
        })
        .join("");
}

// Nombres ya en uso del tipo elegido, para sugerir con un <datalist> en vez
// de que el custodio tenga que escribir igual a mano (un typo crea un grupo
// fantasma en vez de sumarse al que ya existe, ver render.js claveGrupo).
function nombresExistentes(tipo) {
    const vistos = new Set();
    const nombres = [];
    for (const r of recursos) {
        if (r.tipo_recurso !== tipo) continue;
        const clave = r.nombre.trim().toLowerCase();
        if (vistos.has(clave)) continue;
        vistos.add(clave);
        nombres.push(r.nombre);
    }
    return nombres;
}

function datalistNombresHTML(tipo) {
    return `<datalist id="nombres-existentes">
        ${nombresExistentes(tipo).map((n) => `<option value="${esc(n)}"></option>`).join("")}
    </datalist>`;
}

// Los chips solo tienen sentido si el custodio puede dar de alta más de un
// tipo; con uno solo, el tipo va en un hidden y no se muestra nada.
function chipsTipoHTML() {
    if (tiposPermitidos.length === 1) {
        return `<input type="hidden" name="tipo_recurso" value="${esc(tiposPermitidos[0])}">`;
    }
    const opciones = tiposPermitidos
        .map(
            (t, i) =>
                `<span class="chip-opt${i === 0 ? " on" : ""}" data-valor="${esc(t)}">${esc(
                    ETIQUETA_TIPO[t] || t
                )}</span>`
        )
        .join("");
    return `<label class="field">Tipo de recurso
        <span class="chip-toggle" data-chip-grupo="tipo_recurso">${opciones}</span>
        <input type="hidden" name="tipo_recurso" value="${esc(tiposPermitidos[0])}">
    </label>`;
}

function abrirModalNuevo() {
    openModal(
        "Nuevo recurso",
        `<form data-accion="crear">
            ${chipsTipoHTML()}
            <div class="fila">
                <label class="field">Código
                    <input type="text" name="codigo" maxlength="30" placeholder="Ej. LIB-011" required>
                </label>
                <label class="field">Ubicación
                    <input type="text" name="ubicacion" maxlength="120" placeholder="Ej. Estante B2">
                </label>
            </div>
            <label class="field">Nombre
                <input type="text" name="nombre" maxlength="120" list="nombres-existentes" required>
            </label>
            ${datalistNombresHTML(tiposPermitidos[0])}
            <label class="field">Descripción
                <textarea name="descripcion" rows="2"></textarea>
            </label>
            <div id="campos-tipo">${camposTipoHTML(tiposPermitidos[0])}</div>
            <span class="hint">Se da de alta como <b>Disponible</b>. El estado cambia solo al prestarlo o devolverlo.
            Si el nombre coincide con uno existente, esta copia se agrupa con las demás en la lista.</span>
            <div class="alert-danger form-error-msg" hidden></div>
            <div class="acciones">
                <button type="button" class="btn btn-ghost btn-sm" data-cerrar-modal>Cancelar</button>
                <button type="submit" class="btn btn-primary btn-sm">Crear recurso</button>
            </div>
        </form>`
    );
}

document.getElementById("btn-nuevo").addEventListener("click", abrirModalNuevo);

// --- Edición y baja de un recurso --------------------------------------------

// Transiciones manuales válidas (routers/recurso.py, schemas/recurso.py
// RecursoUpdate): PRESTADO/RESERVADO los asigna el sistema solo, nunca este
// formulario.
const ESTADOS_EDITABLES = ["DISPONIBLE", "MANTENIMIENTO", "BAJA"];

function estadoSelectHTML(r) {
    if (r.estado === "PRESTADO") {
        // Sin campo `estado` en el form: si se mandara igual, el backend lo
        // rechaza con 409 porque el recurso está prestado.
        return `<p class="hint">Está prestado: el estado se actualiza solo al registrar la devolución.</p>`;
    }
    const opciones = ESTADOS_EDITABLES.map(
        (e) =>
            `<option value="${e}" ${e === r.estado ? "selected" : ""}>${esc(
                ETIQUETA_ESTADO[e]?.texto || e
            )}</option>`
    ).join("");
    return `<label class="field">Estado
        <select name="estado">${opciones}</select>
    </label>`;
}

function abrirModalEditar(r) {
    openModal(
        `Editar · ${r.nombre}`,
        `<form data-accion="editar" data-id="${esc(r.id)}">
            <div class="fila">
                <label class="field">Código
                    <input type="text" name="codigo" maxlength="30" value="${esc(r.codigo)}" required>
                </label>
                <label class="field">Ubicación
                    <input type="text" name="ubicacion" maxlength="120" value="${esc(r.ubicacion || "")}">
                </label>
            </div>
            <label class="field">Nombre
                <input type="text" name="nombre" maxlength="120" value="${esc(r.nombre)}" required>
            </label>
            <label class="field">Descripción
                <textarea name="descripcion" rows="2">${esc(r.descripcion || "")}</textarea>
            </label>
            <div id="campos-tipo">${camposTipoHTML(r.tipo_recurso, r)}</div>
            ${estadoSelectHTML(r)}
            <div class="alert-danger form-error-msg" hidden></div>
            <div class="acciones">
                <button type="button" class="btn btn-ghost btn-sm" data-cerrar-modal>Cancelar</button>
                <button type="submit" class="btn btn-primary btn-sm">Guardar cambios</button>
            </div>
        </form>`
    );
}

// Sugerencia de código para una copia nueva: no hay ningún formato validado
// en el backend (routers/recurso.py, schemas/recurso.py), es solo un valor
// de partida que el custodio puede editar antes de guardar.
function sugerirCodigo(unidades) {
    return `${unidades[0].codigo}-${unidades.length + 1}`;
}

function abrirModalAgregarCopia(unidades) {
    const base = unidades[0];
    openModal(
        `Agregar copia · ${base.nombre}`,
        `<form data-accion="crear">
            <input type="hidden" name="tipo_recurso" value="${esc(base.tipo_recurso)}">
            <div class="fila">
                <label class="field">Código
                    <input type="text" name="codigo" maxlength="30" value="${esc(sugerirCodigo(unidades))}" required>
                </label>
                <label class="field">Ubicación
                    <input type="text" name="ubicacion" maxlength="120" value="${esc(base.ubicacion || "")}">
                </label>
            </div>
            <label class="field">Nombre
                <input type="text" name="nombre" maxlength="120" value="${esc(base.nombre)}" required>
            </label>
            <label class="field">Descripción
                <textarea name="descripcion" rows="2">${esc(base.descripcion || "")}</textarea>
            </label>
            <div id="campos-tipo">${camposTipoHTML(base.tipo_recurso, base)}</div>
            <span class="hint">Se da de alta como <b>Disponible</b>, con los mismos datos que las
            demás copias de "${esc(base.nombre)}". Revisá el código antes de guardar.</span>
            <div class="alert-danger form-error-msg" hidden></div>
            <div class="acciones">
                <button type="button" class="btn btn-ghost btn-sm" data-cerrar-modal>Cancelar</button>
                <button type="submit" class="btn btn-primary btn-sm">Crear copia</button>
            </div>
        </form>`
    );
}

tabla.addEventListener("click", (evento) => {
    const btnEditar = evento.target.closest(".btn-editar");
    if (btnEditar) {
        const recurso = recursos.find((r) => r.id === Number(btnEditar.dataset.id));
        if (recurso) abrirModalEditar(recurso);
        return;
    }

    const btnBaja = evento.target.closest(".btn-dar-baja");
    if (btnBaja) {
        darDeBaja(btnBaja);
        return;
    }

    const btnCopia = evento.target.closest(".btn-agregar-copia");
    if (btnCopia) {
        const base = recursos.find((r) => r.id === Number(btnCopia.dataset.id));
        if (!base) return;
        const clave = claveGrupo(base);
        abrirModalAgregarCopia(recursos.filter((r) => claveGrupo(r) === clave));
        return;
    }

    const btnHistorial = evento.target.closest(".btn-ver-historial");
    if (btnHistorial) {
        abrirModalHistorial(btnHistorial.dataset.codigo);
    }
});

async function darDeBaja(boton) {
    if (!confirm("¿Dar de baja este recurso? Deja de estar disponible para prestarse.")) return;

    setBusy(boton, true, "Dando de baja…");
    try {
        await api.put(`/recursos/${boton.dataset.id}`, { estado: "BAJA" });
        await cargarInventario();
    } catch (e) {
        alert(e.message);
        setBusy(boton, false);
    }
}

// --- Interacción dentro del modal -------------------------------------------

document.addEventListener("click", (evento) => {
    if (evento.target.closest("[data-cerrar-modal]")) closeModal();

    const chip = evento.target.closest(".modal-body .chip-opt");
    if (!chip) return;

    const grupo = chip.closest("[data-chip-grupo]");
    grupo.querySelectorAll(".chip-opt").forEach((c) => c.classList.toggle("on", c === chip));
    grupo.parentElement.querySelector("input[type=hidden]").value = chip.dataset.valor;

    // Cambiar el tipo cambia los campos del subtipo (un libro pide autor, un
    // deportivo pide disciplina), así que se vuelven a pintar.
    document.getElementById("campos-tipo").innerHTML = camposTipoHTML(chip.dataset.valor);

    // Las sugerencias de nombre también dependen del tipo (los nombres de
    // libros no tienen sentido como sugerencia al dar de alta un deportivo).
    const datalistNombre = document.getElementById("nombres-existentes");
    if (datalistNombre) datalistNombre.outerHTML = datalistNombresHTML(chip.dataset.valor);
});

document.addEventListener("submit", (evento) => {
    const form = evento.target.closest(".modal-body form");
    if (!form) return;
    evento.preventDefault();
    if (form.dataset.accion === "crear") crearRecurso(form);
    if (form.dataset.accion === "editar") editarRecurso(form);
});

function payloadDesdeForm(datos, tipo) {
    const payload = {
        codigo: datos.codigo.trim(),
        nombre: datos.nombre.trim(),
        tipo_recurso: tipo,
    };

    // `gestor` no se envía a propósito: el router lo deriva del tipo para que
    // sea imposible violar la constraint chk_gestor_tipo (routers/recurso.py:75).
    if (datos.descripcion && datos.descripcion.trim()) payload.descripcion = datos.descripcion.trim();
    if (datos.ubicacion && datos.ubicacion.trim()) payload.ubicacion = datos.ubicacion.trim();

    CAMPOS_POR_TIPO[tipo].forEach((c) => {
        if (c.tipo === "checkbox") {
            payload[c.name] = datos[c.name] === "true";
        } else if (datos[c.name] && datos[c.name].trim()) {
            payload[c.name] = datos[c.name].trim();
        }
    });

    return payload;
}

async function crearRecurso(form) {
    const datos = formValues(form);
    const boton = form.querySelector('button[type="submit"]');
    const errorDiv = form.querySelector(".form-error-msg");
    const tipo = datos.tipo_recurso;
    const codigo = datos.codigo.trim();

    // `codigo` es UNIQUE en la base; el backend ya devuelve 409 si se manda un
    // duplicado, pero se avisa antes de enviar para no gastar el round-trip
    // (comparando contra el catálogo completo, no solo el propio: el código es
    // único entre todos los recursos).
    if (recursos.some((r) => r.codigo.toLowerCase() === codigo.toLowerCase())) {
        return showFormError(errorDiv, `Ya existe un recurso con el código ${codigo}.`);
    }

    setBusy(boton, true, "Creando…");
    showFormError(errorDiv, "");

    try {
        await api.post("/recursos", payloadDesdeForm(datos, tipo));
        closeModal();
        await cargarInventario();
    } catch (e) {
        showFormError(errorDiv, e.message);
        setBusy(boton, false);
    }
}

// --- Edición: envío del formulario -------------------------------------------

// A diferencia de `payloadDesdeForm` (alta), acá un campo vacío es
// intencional: se manda `null` para poder borrar un dato que ya estaba.
function payloadEdicionDesdeForm(datos, tipo) {
    const payload = {
        codigo: datos.codigo.trim(),
        nombre: datos.nombre.trim(),
        ubicacion: datos.ubicacion.trim() || null,
        descripcion: datos.descripcion.trim() || null,
    };

    // `estado` no viene en el form si el recurso está prestado (ver
    // estadoSelectHTML), así que no se manda nada y el backend no lo toca.
    if (datos.estado) payload.estado = datos.estado;

    CAMPOS_POR_TIPO[tipo].forEach((c) => {
        if (c.tipo === "checkbox") {
            payload[c.name] = datos[c.name] === "true";
        } else {
            payload[c.name] = (datos[c.name] || "").trim() || null;
        }
    });

    return payload;
}

async function editarRecurso(form) {
    const datos = formValues(form);
    const boton = form.querySelector('button[type="submit"]');
    const errorDiv = form.querySelector(".form-error-msg");
    const id = form.dataset.id;
    const recurso = recursos.find((r) => r.id === Number(id));

    setBusy(boton, true, "Guardando…");
    showFormError(errorDiv, "");

    try {
        await api.put(`/recursos/${id}`, payloadEdicionDesdeForm(datos, recurso.tipo_recurso));
        closeModal();
        await cargarInventario();
    } catch (e) {
        showFormError(errorDiv, e.message);
        setBusy(boton, false);
    }
}

cargarInventario();
