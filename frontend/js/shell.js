// Sidebar de navegación, compartido por todas las páginas con sesión.
// Requiere api.js (hasRole, currentUser) y render.js (esc) ya cargados antes.

const ICONOS = {
  inicio:
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11l9-7 9 7"/><path d="M5 10v9a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1v-9"/></svg>',
  catalogo:
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="8" height="8" rx="1.5"/><rect x="13" y="3" width="8" height="8" rx="1.5"/><rect x="3" y="13" width="8" height="8" rx="1.5"/><rect x="13" y="13" width="8" height="8" rx="1.5"/></svg>',
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
  actividades:
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l9 5-9 5-9-5 9-5z"/><path d="M3 12l9 5 9-5"/><path d="M3 17l9 5 9-5"/></svg>',
  sanciones:
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l9 16H3L12 3z"/><path d="M12 9v4M12 16h.01"/></svg>',
  notificaciones:
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/></svg>',
  perfil:
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4.4 3.6-7 8-7s8 2.6 8 7"/></svg>',
  salir:
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/></svg>',
};

// La navegación depende del rol (ver artefacto "Wireframes Préstamos" · NAV),
// pero "cualquier rol puede solicitar/reservar para sí mismo" (docs/00, §4) es
// una regla real del backend y del catálogo (catalogo.js no filtra por rol los
// botones Solicitar/Reservar) — así que Mis Actividades (solicitudes, reservas,
// préstamos e historial, en pestañas) es universal, incluso para custodios y
// admin, que además gestionan su Panel Custodio o Reportes. Un usuario con
// varios roles ve la unión.
function itemsNav() {
  const items = [
    ["inicio.html", "inicio", "Inicio"],
    ["catalogo.html", "catalogo", "Catálogo"],
    ["mis-actividades.html", "actividades", "Mis Actividades"],
    ["sanciones.html", "sanciones", "Sanciones"],
  ];
  if (
    hasRole("CUSTODIO_CE", "CUSTODIO_INFRA", "DOCENTE", "ADMINISTRADOR_SISTEMA")
  ) {
    items.push(["solicitudes.html", "solicitudes", "Bandeja de Solicitudes"]);
  }
  if (hasRole("CUSTODIO_CE", "CUSTODIO_INFRA")) {
    // Los custodios gestionan inventario, entregas y devoluciones.
    items.push(["registrar-prestamo.html", "custodio", "Panel Custodio"]);
  }
  if (hasRole("CUSTODIO_CE", "CUSTODIO_INFRA", "ADMINISTRADOR_SISTEMA")) {
    // Alta y consulta del catálogo (RF1): cada custodio administra su
    // gestor; el administrador ve y administra los dos.
    items.push(["inventario.html", "inventario", "Inventario"]);
  }
  if (hasRole("ADMINISTRADOR_SISTEMA")) {
    items.push(["reportes.html", "reportes", "Reportes"]);
  }
  if (hasRole("ADMINISTRADOR_SISTEMA")) {
    items.push(["usuarios.html", "usuarios", "Usuarios y Roles"]);
  }
  // Perfil va al final, cerca de "Cerrar sesión": igual para cualquier rol.
  // Notificaciones no está acá: es el ícono junto a la marca, arriba del todo
  // (ver renderSidebar), no una fila más de esta lista.
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

  const items = itemsNav()
    .map(([href, clave, texto]) => {
      const activo = clave === activa ? " active" : "";
      return `<a class="nav-item${activo}" href="${href}">${ICONOS[clave]}<span>${esc(texto)}</span></a>`;
    })
    .join("");

  el.innerHTML = `
    <div class="sidebar-header">
      <div class="marca">Sistema de <span>Préstamos</span></div>
      <button type="button" class="btn-notif-icono" id="btn-notificaciones" aria-label="Notificaciones">
        ${ICONOS.notificaciones}
        <span class="nav-badge badge-icono" id="notif-badge" hidden>0</span>
      </button>
    </div>
    <div class="who"><b>${esc(nombre)}</b>${esc(roles)}</div>
    ${items}
    <button type="button" class="nav-item logout" id="btn-cerrar-sesion">${ICONOS.salir}<span>Cerrar sesión</span></button>`;

  document
    .getElementById("btn-cerrar-sesion")
    .addEventListener("click", () => api.logout());

  if (usuario) {
    api.get("/notificaciones?leidas=false")
      .then((noLeidas) => actualizarBadgeNotif(Array.isArray(noLeidas) ? noLeidas.length : 0))
      .catch(() => {});
  }
}

// --- Notificaciones: dropdown en vez de página -------------------------------
//
// Con solo 2 tipos de notificación (solicitud aceptada/rechazada), sin
// acciones propias más que marcar como leída, no amerita sacar al usuario de
// la página en la que está — antes vivía en notificaciones.html/.js, ahora es
// un panel flotante que cuelga del botón del sidebar (mismo patrón de overlay
// singleton que modal.js, pero sin bloquear el resto de la página).

let panelNotif;

function asegurarPanelNotif() {
  if (panelNotif) return panelNotif;
  panelNotif = document.createElement("div");
  panelNotif.className = "notif-panel";
  panelNotif.hidden = true;
  panelNotif.innerHTML = `
    <div class="notif-panel-head">Notificaciones</div>
    <div class="notif-panel-body"></div>`;
  document.body.appendChild(panelNotif);
  return panelNotif;
}

function actualizarBadgeNotif(cantidad) {
  const badge = document.getElementById("notif-badge");
  if (!badge) return;
  badge.hidden = cantidad === 0;
  badge.textContent = cantidad;
}

function formatearFechaHoraNotif(iso) {
  return new Date(iso).toLocaleString("es-PE", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function filaNotif(n) {
  const accion = n.leida
    ? ""
    : `<button type="button" class="btn btn-ghost btn-sm btn-marcar-leida" data-id="${esc(n.id)}">Marcar como leída</button>`;
  return `<div class="loan${n.leida ? "" : " alert"}">
    <div><div class="t">${esc(n.mensaje)}</div><div class="s">${esc(formatearFechaHoraNotif(n.created_at))}</div></div>
    ${accion}
  </div>`;
}

async function cargarPanelNotif() {
  const body = asegurarPanelNotif().querySelector(".notif-panel-body");
  showLoading(body);
  try {
    const notificaciones = await api.get("/notificaciones");
    renderList(body, notificaciones, filaNotif, "No tienes notificaciones todavía.");
    actualizarBadgeNotif(notificaciones.filter((n) => !n.leida).length);
  } catch (e) {
    showError(body, e.message);
  }
}

// Escritorio: el sidebar es angosto y fijo a la izquierda, el panel sale a su
// derecha. Layout angosto (sidebar como barra horizontal arriba, @media
// 760px en styles.css): sale hacia abajo, pegado al botón.
function posicionarPanelNotif(boton) {
  const el = asegurarPanelNotif();
  const r = boton.getBoundingClientRect();
  const angosto = window.innerWidth <= 760;
  el.style.top = `${angosto ? r.bottom + 6 : r.top}px`;
  el.style.left = `${angosto ? r.left : r.right + 10}px`;
}

function abrirPanelNotif(boton) {
  posicionarPanelNotif(boton);
  asegurarPanelNotif().hidden = false;
  cargarPanelNotif();
}

function cerrarPanelNotif() {
  if (panelNotif) panelNotif.hidden = true;
}

document.addEventListener("click", async (evento) => {
  const btnNotif = evento.target.closest("#btn-notificaciones");
  if (btnNotif) {
    const el = asegurarPanelNotif();
    if (el.hidden) abrirPanelNotif(btnNotif);
    else cerrarPanelNotif();
    return;
  }

  const btnLeida = evento.target.closest(".btn-marcar-leida");
  if (btnLeida && panelNotif && panelNotif.contains(btnLeida)) {
    btnLeida.disabled = true;
    try {
      await api.patch(`/notificaciones/${Number(btnLeida.dataset.id)}`, { leida: true });
      await cargarPanelNotif();
    } catch (e) {
      alert(e.message);
      btnLeida.disabled = false;
    }
    return;
  }

  if (panelNotif && !panelNotif.hidden && !panelNotif.contains(evento.target)) {
    cerrarPanelNotif();
  }
});

document.addEventListener("keydown", (evento) => {
  if (evento.key === "Escape" && panelNotif && !panelNotif.hidden) cerrarPanelNotif();
});
