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
  inventario:
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7l9-4 9 4v10l-9 4-9-4V7z"/><path d="M3 7l9 4 9-4"/><path d="M12 11v10"/></svg>',
  reportes:
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><rect x="7" y="12" width="3" height="6"/><rect x="12" y="8" width="3" height="10"/><rect x="17" y="5" width="3" height="13"/></svg>',
  usuarios:
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="8" r="3.3"/><path d="M3 20c0-3.6 2.7-6 6-6s6 2.4 6 6"/><circle cx="18" cy="9" r="2.6"/><path d="M15.5 14.2c2.6.3 4.5 2.3 4.5 5.3"/></svg>',
  solicitudes:
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M9 13l2 2 4-4"/></svg>',
  notificaciones:
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/></svg>',
  perfil:
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4.4 3.6-7 8-7s8 2.6 8 7"/></svg>',
  salir:
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/></svg>',
};

// La navegación depende del rol (ver artefacto "Wireframes Préstamos" ·
// NAV): quien presta/reserva para sí mismo (Estudiante, Docente) ve
// Mis Reservas/Mis Préstamos; un Custodio solo gestiona su Panel Custodio;
// Dirección de Escuela ve Reportes (RF6) y Usuarios y Roles (RF7), igual
// que Administrador del Sistema. Un usuario con varios roles ve la unión.
function itemsNav() {
  const items = [
    ["inicio.html", "inicio", "Inicio"],
    ["catalogo.html", "catalogo", "Catálogo"],
  ];
  if (hasRole("ESTUDIANTE", "DOCENTE")) {
    items.push(["mis-reservas.html", "reservas", "Mis Reservas"]);
    items.push(["mis-prestamos.html", "prestamos", "Mis Préstamos"]);
  }
  if (hasRole("CUSTODIO_CE", "CUSTODIO_INFRA")) {
    // Bandeja de Solicitudes es el flujo normal (hallazgo #13); Panel Custodio
    // queda como registro directo para casos que no nacieron de una solicitud.
    items.push(["solicitudes.html", "solicitudes", "Bandeja de Solicitudes"]);
    items.push(["registrar-prestamo.html", "custodio", "Panel Custodio"]);
    // Alta y consulta del catálogo que administra cada custodio (RF1).
    items.push(["inventario.html", "inventario", "Inventario"]);
  }
  if (hasRole("DIRECCION_ESCUELA")) {
    items.push(["reportes.html", "reportes", "Reportes"]);
  }
  if (hasRole("DIRECCION_ESCUELA", "ADMINISTRADOR_SISTEMA")) {
    items.push(["usuarios.html", "usuarios", "Usuarios y Roles"]);
  }
  // Notificaciones y Perfil van al final, cerca de "Cerrar sesión": son
  // iguales para cualquier rol.
  items.push(["notificaciones.html", "notificaciones", "Notificaciones"]);
  items.push(["perfil.html", "perfil", "Perfil"]);
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

  // El contador de notificaciones no leídas es del prototipo de frontend
  // (ver js/mock-solicitudes.js); solo se muestra si esa librería está cargada.
  const noLeidas =
    usuario && typeof MockNotificaciones !== "undefined" ? MockNotificaciones.noLeidas(usuario.email) : 0;

  const items = itemsNav()
    .map(([href, clave, texto]) => {
      const activo = clave === activa ? " active" : "";
      const badge =
        clave === "notificaciones" && noLeidas > 0 ? `<span class="nav-badge">${noLeidas}</span>` : "";
      return `<a class="nav-item${activo}" href="${href}">${ICONOS[clave]}<span>${esc(texto)}</span>${badge}</a>`;
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
