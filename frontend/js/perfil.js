// Perfil (datos del usuario logueado). Solo lectura por ahora: no hay
// endpoint para editar nombre/email ni para cambiar contraseña.

if (!requireAuth()) throw new Error("sin sesión");

renderSidebar("perfil");

const usuario = currentUser();

function iniciales(nombre) {
  const partes = nombre.trim().split(/\s+/);
  return (partes[0][0] + (partes[1] ? partes[1][0] : "")).toUpperCase();
}

document.getElementById("perfil-avatar").textContent = iniciales(usuario.nombres);
document.getElementById("perfil-nombre").textContent = usuario.nombres;
document.getElementById("perfil-roles").innerHTML = usuario.roles
  .map((r) => `<span class="role-chip">${esc(ETIQUETA_ROL[r] || r)}</span>`)
  .join("");
document.getElementById("perfil-codigo").textContent = usuario.codigo;
document.getElementById("perfil-email").textContent = usuario.email;
