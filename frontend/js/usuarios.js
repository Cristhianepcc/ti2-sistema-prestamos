// Gestión administrativa de usuarios y roles (RF7).

if (!requireAuth()) throw new Error("sin sesión");

// El backend aplica la misma regla; esta verificación evita mostrar el panel
// al abrir directamente su URL con una cuenta sin permisos.
if (!hasRole("ADMINISTRADOR_SISTEMA")) {
  location.href = "inicio.html";
  throw new Error("solo administradores del sistema");
}

renderSidebar("usuarios");

const tablaUsuarios = document.getElementById("tabla-usuarios");
const buscarUsuario = document.getElementById("buscar-usuario");
const mensajeUsuarios = document.getElementById("mensaje-usuarios");
const ROLES_USUARIO = [
  ["ESTUDIANTE", "Estudiante"],
  ["DOCENTE", "Docente"],
  ["CUSTODIO_CE", "Custodio del Centro de Estudiantes"],
  ["CUSTODIO_INFRA", "Custodio de Infraestructura"],
  ["DIRECCION_ESCUELA", "Dirección de Escuela"],
  ["ADMINISTRADOR_SISTEMA", "Administrador del sistema"],
];

let usuarios = [];

function mostrarMensaje(texto, tipo = "success") {
  mensajeUsuarios.className = tipo === "success" ? "alert-success" : "alert-danger";
  mensajeUsuarios.textContent = texto;
  mensajeUsuarios.hidden = !texto;
}

function rolesCheckboxHTML(seleccionados = []) {
  return ROLES_USUARIO.map(
    ([valor, etiqueta]) => `
      <label class="field field-check">
        <input type="checkbox" name="roles" value="${valor}" ${
          seleccionados.includes(valor) ? "checked" : ""
        }>
        <span>${esc(etiqueta)}</span>
      </label>`
  ).join("");
}

function textoRoles(roles) {
  if (!roles || roles.length === 0) return "Sin roles";
  return roles
    .map((rol) => ETIQUETA_ROL[rol] || rol)
    .map((etiqueta) => `<span class="role-chip">${esc(etiqueta)}</span>`)
    .join("");
}

function pintarUsuarios() {
  const consulta = buscarUsuario.value.trim().toLocaleLowerCase();
  const filtrados = usuarios.filter((usuario) =>
    [usuario.codigo, usuario.nombres, usuario.email]
      .join(" ")
      .toLocaleLowerCase()
      .includes(consulta)
  );

  if (filtrados.length === 0) {
    showEmpty(
      tablaUsuarios,
      usuarios.length ? "No hay usuarios que coincidan con la búsqueda." : "Aún no hay usuarios registrados.",
      5
    );
    return;
  }

  tablaUsuarios.innerHTML = filtrados
    .map(
      (usuario) => `
        <tr>
          <td>${esc(usuario.codigo)}</td>
          <td>${esc(usuario.nombres)}</td>
          <td>${esc(usuario.email)}</td>
          <td>${textoRoles(usuario.roles)}</td>
          <td>
            <button type="button" class="btn btn-ghost btn-sm"
                    data-accion="roles" data-usuario-id="${esc(usuario.id)}">
              Gestionar roles
            </button>
          </td>
        </tr>`
    )
    .join("");
}

async function cargarUsuarios() {
  mostrarMensaje("");
  showLoading(tablaUsuarios, 5);
  try {
    usuarios = await api.get("/usuarios");
    pintarUsuarios();
    return true;
  } catch (error) {
    showError(tablaUsuarios, error.message, 5);
    return false;
  }
}

function abrirModalNuevoUsuario() {
  openModal(
    "Crear usuario",
    `<form data-accion="crear">
      <div class="fila">
        <label class="field">Código institucional
          <input type="text" name="codigo" maxlength="20" autocomplete="off" required>
        </label>
        <label class="field">Nombres y apellidos
          <input type="text" name="nombres" maxlength="120" autocomplete="name" required>
        </label>
      </div>
      <label class="field">Correo institucional
        <input type="email" name="email" maxlength="120" placeholder="usuario@unsa.edu.pe"
               autocomplete="email" required>
      </label>
      <label class="field">Contraseña inicial
        <input type="password" name="password" autocomplete="new-password" required>
        <span class="hint">Se guarda como hash; no se puede consultar después. Máximo 72 bytes UTF-8.</span>
      </label>
      <div class="field">
        Roles
        <div class="form-card">${rolesCheckboxHTML()}</div>
        <span class="hint">Selecciona al menos un rol.</span>
      </div>
      <div class="alert-danger form-error-msg" role="alert" hidden></div>
      <div class="acciones">
        <button type="button" class="btn btn-ghost btn-sm" data-cerrar-modal>Cancelar</button>
        <button type="submit" class="btn btn-primary btn-sm">Crear usuario</button>
      </div>
    </form>`
  );
}

function abrirModalRoles(usuario) {
  openModal(
    "Gestionar roles",
    `<form data-accion="roles" data-usuario-id="${esc(usuario.id)}">
      <p class="hint">Selecciona los roles de <b>${esc(usuario.nombres)}</b>. La selección reemplazará los roles actuales.</p>
      <div class="form-card">${rolesCheckboxHTML(usuario.roles || [])}</div>
      <span class="hint">El usuario debe conservar al menos un rol.</span>
      <div class="alert-danger form-error-msg" role="alert" hidden></div>
      <div class="acciones">
        <button type="button" class="btn btn-ghost btn-sm" data-cerrar-modal>Cancelar</button>
        <button type="submit" class="btn btn-primary btn-sm">Guardar roles</button>
      </div>
    </form>`
  );
}

async function crearUsuario(form) {
  const boton = form.querySelector('button[type="submit"]');
  const error = form.querySelector(".form-error-msg");
  const formData = new FormData(form);
  const roles = formData.getAll("roles");
  if (roles.length === 0) {
    showFormError(error, "Selecciona al menos un rol.");
    return;
  }

  const datos = Object.fromEntries(formData.entries());
  delete datos.roles;
  datos.codigo = datos.codigo.trim();
  datos.nombres = datos.nombres.trim();
  datos.email = datos.email.trim().toLowerCase();
  datos.roles = roles;

  setBusy(boton, true, "Creando…");
  showFormError(error, "");
  try {
    await api.post("/usuarios", datos);
    closeModal();
    const listaActualizada = await cargarUsuarios();
    mostrarMensaje(
      listaActualizada
        ? "Usuario creado correctamente."
        : "Usuario creado; no se pudo actualizar la lista. Recarga la página."
    );
  } catch (e) {
    showFormError(error, e.message);
    setBusy(boton, false);
  }
}

async function guardarRoles(form) {
  const boton = form.querySelector('button[type="submit"]');
  const error = form.querySelector(".form-error-msg");
  const roles = new FormData(form).getAll("roles");
  if (roles.length === 0) {
    showFormError(error, "El usuario debe conservar al menos un rol.");
    return;
  }

  const usuarioId = Number(form.dataset.usuarioId);
  setBusy(boton, true, "Guardando…");
  showFormError(error, "");
  try {
    const actualizado = await api.put(`/usuarios/${usuarioId}/roles`, { roles });
    closeModal();
    const sesion = currentUser();
    if (sesion && sesion.id === actualizado.id) {
      localStorage.setItem("user", JSON.stringify(actualizado));
      if (!actualizado.roles.includes("ADMINISTRADOR_SISTEMA")) {
        location.href = "inicio.html";
        return;
      }
      renderSidebar("usuarios");
    }
    const listaActualizada = await cargarUsuarios();
    mostrarMensaje(
      listaActualizada
        ? "Roles actualizados correctamente."
        : "Roles actualizados; no se pudo actualizar la lista. Recarga la página."
    );
  } catch (e) {
    showFormError(error, e.message);
    setBusy(boton, false);
  }
}

document.getElementById("btn-nuevo-usuario").addEventListener("click", abrirModalNuevoUsuario);
buscarUsuario.addEventListener("input", pintarUsuarios);

document.addEventListener("click", (evento) => {
  if (evento.target.closest("[data-cerrar-modal]")) {
    closeModal();
    return;
  }

  const boton = evento.target.closest('[data-accion="roles"][data-usuario-id]');
  if (!boton || boton.closest(".modal-body")) return;
  const usuario = usuarios.find((item) => item.id === Number(boton.dataset.usuarioId));
  if (usuario) abrirModalRoles(usuario);
});

document.addEventListener("submit", (evento) => {
  const form = evento.target.closest(".modal-body form[data-accion]");
  if (!form) return;
  evento.preventDefault();
  if (form.dataset.accion === "crear") crearUsuario(form);
  if (form.dataset.accion === "roles") guardarRoles(form);
});

cargarUsuarios();
