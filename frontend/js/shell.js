// Sidebar de navegación, compartido por todas las páginas con sesión.
// Requiere api.js (hasRole, currentUser) y render.js (esc) ya cargados antes.

const ICONOS = {
  inicio:
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11l9-7 9 7"/><path d="M5 10v9a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1v-9"/></svg>',
  catalogo:
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="8" height="8" rx="1.5"/><rect x="13" y="3" width="8" height="8" rx="1.5"/><rect x="3" y="13" width="8" height="8" rx="1.5"/><rect x="13" y="13" width="8" height="8" rx="1.5"/></svg>',
  reservas:
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12v18l-6-4-6 4V3z"/></svg>',
  prestamos:
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
  custodio:
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="8" y="2" width="8" height="4" rx="1"/><path d="M8 4H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-2"/><path d="M9 13l2 2 4-4"/></svg>',
  salir:
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/></svg>',
};

// Todo usuario ve Catálogo/Mis Reservas/Mis Préstamos; el Panel de Custodio
// solo si tiene el rol correspondiente (ver #33).
function itemsNav() {
  const items = [
    ["inicio.html", "inicio", "Inicio"],
    ["catalogo.html", "catalogo", "Catálogo"],
    ["mis-reservas.html", "reservas", "Mis Reservas"],
    ["mis-prestamos.html", "prestamos", "Mis Préstamos"],
  ];
  if (hasRole("CUSTODIO_CE", "CUSTODIO_INFRA")) {
    items.push(["registrar-prestamo.html", "custodio", "Panel Custodio"]);
  }
  return items;
}

function renderSidebar(activa) {
  const el = document.getElementById("app-sidebar");
  if (!el) return;

  const usuario = currentUser();
  const nombre = usuario ? usuario.nombres : "";
  const roles = usuario
    ? usuario.roles.map((r) => ETIQUETA_ROL[r] || r).join(" · ")
    : "";

  const items = itemsNav()
    .map(([href, clave, texto]) => {
      const activo = clave === activa ? " active" : "";
      return `<a class="nav-item${activo}" href="${href}">${ICONOS[clave]}<span>${esc(texto)}</span></a>`;
    })
    .join("");

  el.innerHTML = `
    <div class="marca">Sistema de <span>Préstamos</span></div>
    <div class="who"><b>${esc(nombre)}</b>${esc(roles)}</div>
    ${items}
    <button type="button" class="nav-item logout" id="btn-cerrar-sesion">${ICONOS.salir}<span>Cerrar sesión</span></button>`;

  document
    .getElementById("btn-cerrar-sesion")
    .addEventListener("click", () => api.logout());
}
