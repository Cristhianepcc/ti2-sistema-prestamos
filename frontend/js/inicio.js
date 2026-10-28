// Inicio (dashboard de bienvenida, issue #43). Usa datos reales de los
// endpoints que ya existen (/prestamos, /reservas, /recursos). La
// estructura de cada panel de rol (encabezado + 3 stats + dos columnas)
// sigue el artefacto "Wireframes Préstamos"; donde ese artefacto marcaba
// una sección como "RF4/RF6/RF7 · futuro" (sin backend todavía), se deja
// una nota explícita en vez de inventar números.

if (!requireAuth()) throw new Error("sin sesión");

renderSidebar("inicio");

const usuario = currentUser();

// --- Fechas ------------------------------------------------------------------

function parseFechaLocal(texto) {
  const [anio, mes, dia] = String(texto).slice(0, 10).split("-").map(Number);
  return new Date(anio, mes - 1, dia);
}

function formatearFecha(texto) {
  return parseFechaLocal(texto).toLocaleDateString("es-PE", { day: "numeric", month: "short" });
}

function diasHasta(texto) {
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);
  return Math.round((parseFechaLocal(texto) - hoy) / 86400000);
}

function esHoy(texto) {
  return diasHasta(texto) === 0;
}

// --- Helpers de render compartidos (stats / columnas / filas) ----------------

function statHTML(s) {
  const color = s.color ? ` style="color:var(--${s.color})"` : "";
  return `<div class="stat"><div class="n"${color}>${esc(s.n)}</div><div class="l">${esc(s.l)}</div></div>`;
}

function miniRowHTML(r) {
  const sub = r.s ? `<div class="s">${esc(r.s)}</div>` : "";
  return `<div class="mini-row"><div><div class="t">${esc(r.t)}</div>${sub}</div>${r.badge || ""}</div>`;
}

function colHTML(col) {
  const sub = col.sub ? `<span>${esc(col.sub)}</span>` : "";
  let cuerpo;
  if (col.type === "actions") {
    cuerpo = `<div class="action-list">${col.actions
      .map((a) => `<a href="${a.href}" class="btn btn-ghost btn-sm btn-block">${esc(a.texto)}</a>`)
      .join("")}</div>`;
  } else if (col.nota) {
    cuerpo = `<p class="nota-futura">${col.nota}</p>`;
  } else if (col.rows && col.rows.length) {
    cuerpo = col.rows.map(miniRowHTML).join("");
  } else {
    cuerpo = `<p class="nota-futura">Sin datos por ahora.</p>`;
  }
  return `<div><div class="block-title">${esc(col.titulo)}${sub}</div>${cuerpo}</div>`;
}

function panelRol({ titulo, descripcion, stats, colA, colB }) {
  return `
    <div class="bloque-rol">
      <div class="role-panel-head"><b>${esc(titulo)}</b><span>${descripcion}</span></div>
      <div class="bloque-rol-cuerpo">
        <div class="stat-row">${stats.map(statHTML).join("")}</div>
        <div class="two-col">${colHTML(colA)}${colHTML(colB)}</div>
      </div>
    </div>`;
}

// --- Saludo + chips de rol ----------------------------------------------------

function pintarSaludo() {
  const chips = usuario.roles.map((r) => `<span class="role-chip">${esc(ETIQUETA_ROL[r] || r)}</span>`).join("");
  document.getElementById("saludo").innerHTML =
    `Hola, <b>${esc(usuario.nombres.split(" ")[0])}</b>${chips}`;
}

// --- Panel base (cualquier rol puede solicitar/reservar) ----------------------

function pintarStats(misPrestamos, misReservas) {
  const activos = misPrestamos.filter((p) => p.estado === "ACTIVO" || p.estado === "ATRASADO");
  const pendientesReserva = misReservas.filter((r) => r.estado === "PENDIENTE");

  let vencimiento = { n: "—", l: "Sin préstamos pendientes" };
  if (activos.length > 0) {
    const proximo = activos.reduce((a, b) => (diasHasta(a.fecha_limite) < diasHasta(b.fecha_limite) ? a : b));
    const dias = diasHasta(proximo.fecha_limite);
    vencimiento = {
      n: formatearFecha(proximo.fecha_limite),
      l: `Vence · ${esc(proximo.recurso ? proximo.recurso.nombre : "")}`,
      color: dias < 2 ? "danger" : undefined,
    };
  }

  const stats = [
    { n: activos.length, l: "Préstamos activos" },
    { n: pendientesReserva.length, l: "Reservas pendientes" },
    vencimiento,
  ];

  document.getElementById("stats").innerHTML = stats.map(statHTML).join("");
}

function pintarCatalogoDestacado(recursos) {
  const destacados = recursos.filter((r) => r.disponible).slice(0, 4);
  const el = document.getElementById("col-catalogo");
  if (destacados.length === 0) return showEmpty(el, "No hay recursos disponibles ahora mismo.");
  el.innerHTML = destacados
    .map(
      (r) => `<div class="mini-row"><div><div class="t">${esc(r.nombre)}</div><div class="s">${esc(r.codigo)} · ${esc(ETIQUETA_TIPO[r.tipo_recurso])}</div></div>${badgeEstado(r.estado)}</div>`
    )
    .join("");
}

function pintarActividad(misPrestamos, misReservas) {
  const items = [
    ...misPrestamos.map((p) => ({
      fecha: p.fecha_entrega,
      t: p.recurso ? p.recurso.nombre : `Préstamo #${p.id}`,
      s: `Préstamo · ${esc(formatearFecha(p.fecha_entrega))}`,
      badge: badgePrestamo(p.estado),
    })),
    ...misReservas.map((r) => ({
      fecha: r.created_at,
      t: r.recurso ? r.recurso.nombre : `Reserva #${r.id}`,
      s: `Reserva · ${esc(formatearFecha(r.fecha))}`,
      badge: badgeReserva(r.estado),
    })),
  ]
    .sort((a, b) => new Date(b.fecha) - new Date(a.fecha))
    .slice(0, 5);

  const el = document.getElementById("col-actividad");
  if (items.length === 0) return showEmpty(el, "Todavía no tienes préstamos ni reservas.");
  el.innerHTML = items
    .map((i) => `<div class="mini-row"><div><div class="t">${esc(i.t)}</div><div class="s">${i.s}</div></div>${i.badge}</div>`)
    .join("");
}

// --- Paneles por rol -----------------------------------------------------------

const GESTOR_POR_ROL_CUSTODIO = {
  CUSTODIO_CE: "CENTRO_ESTUDIANTES",
  CUSTODIO_INFRA: "INFRAESTRUCTURA",
};

function filaPrestamo(p) {
  const dias = diasHasta(p.fecha_limite);
  const urgencia = dias < 0 ? "Vencido" : dias === 0 ? "Vence hoy" : dias === 1 ? "Vence mañana" : `Vence en ${dias} días`;
  return {
    t: p.recurso ? p.recurso.nombre : `Préstamo #${p.id}`,
    s: `${p.recurso ? p.recurso.codigo + " · " : ""}${urgencia}`,
    badge: badgePrestamo(p.estado),
  };
}

function panelCustodio(rol, prestamosActivos) {
  const gestor = GESTOR_POR_ROL_CUSTODIO[rol];
  const delGestor = prestamosActivos.filter((p) => p.recurso && p.recurso.gestor === gestor);
  const vencenPronto = delGestor.filter((p) => diasHasta(p.fecha_limite) < 2);
  const entregasHoy = delGestor.filter((p) => esHoy(p.fecha_entrega));

  const esCE = rol === "CUSTODIO_CE";

  return panelRol({
    titulo: `Inicio — ${ETIQUETA_ROL[rol]}`,
    descripcion: esCE
      ? "Aprueba automáticamente y registra los préstamos SIMPLE de libros e implementos deportivos."
      : "Registra el préstamo académico una vez resuelta la solicitud. Nunca \"aprueba\": solo registra.",
    stats: [
      { n: delGestor.length, l: `Préstamos activos (${esCE ? "CE" : "Infra"})` },
      { n: vencenPronto.length, l: "Vencen pronto", color: vencenPronto.length > 0 ? "warn" : undefined },
      { n: entregasHoy.length, l: "Entregas registradas hoy" },
    ],
    colA: {
      titulo: "Vencen pronto",
      sub: esCE ? "libros y deportivos" : "académicos",
      rows: vencenPronto.slice(0, 4).map(filaPrestamo),
    },
    colB: {
      titulo: "Accesos rápidos",
      type: "actions",
      actions: [
        { href: "registrar-prestamo.html", texto: "Registrar entrega" },
        { href: "registrar-prestamo.html", texto: "Registrar devolución" },
        { href: "registrar-prestamo.html", texto: "Ver préstamos atrasados" },
      ],
    },
  });
}

function panelDireccion(recursos) {
  const conteos = {};
  for (const r of recursos) conteos[r.tipo_recurso] = (conteos[r.tipo_recurso] || 0) + 1;

  return panelRol({
    titulo: "Inicio — Dirección de Escuela",
    descripcion: "Autoriza solo las solicitudes EXCEPCIONAL ya avaladas por un docente. También es la única con vista de reportes de todo el sistema (RF6, próxima entrega).",
    stats: [
      // GET /prestamos?estado=ACTIVO es solo para custodios (403 para este
      // rol) — un reporte "préstamos activos (sistema)" para Dirección
      // necesita un endpoint propio de RF6, que todavía no existe.
      { n: "—", l: "Préstamos activos (sistema, RF6)" },
      { n: "—", l: "Sanciones activas (RF5)" },
      { n: "—", l: "Por autorizar · excepcional (RF4)" },
    ],
    colA: {
      titulo: "Por autorizar",
      sub: "RF4 · futuro · solo EXCEPCIONAL",
      nota: "La bandeja de autorizaciones llega en una próxima entrega.",
    },
    colB: {
      titulo: "Inventario por tipo",
      rows: Object.entries(conteos).map(([tipo, n]) => ({ t: ETIQUETA_TIPO[tipo] || tipo, s: `${n} recursos` })),
    },
  });
}

function panelDocente() {
  return panelRol({
    titulo: "Inicio — Docente",
    descripcion: "Avala las solicitudes académicas de sus alumnos antes de que pasen a Dirección (RF4, próxima entrega). Para préstamos propios usa las mismas pantallas que cualquier usuario.",
    stats: [
      { n: "—", l: "Solicitudes por avalar (RF4)" },
      { n: "—", l: "Avaladas este mes (RF4)" },
      { n: "—", l: "Rechazadas este mes (RF4)" },
    ],
    colA: {
      titulo: "Solicitudes de mis alumnos",
      sub: "RF4 · futuro",
      nota: "Avalar solicitudes académicas llega en una próxima entrega.",
    },
    colB: {
      titulo: "Avales recientes",
      sub: "RF4 · futuro",
      nota: "Todavía no hay historial de avales.",
    },
  });
}

async function panelAdministrador() {
  let apiOk = false;
  try {
    apiOk = (await api.get("/health")).status === "ok";
  } catch {
    apiOk = false;
  }

  return panelRol({
    titulo: "Inicio — Administrador del Sistema",
    descripcion: "Gestiona cuentas y permisos (RF7). Rol técnico: no aprueba préstamos.",
    stats: [
      { n: "—", l: "Usuarios activos (RF7)" },
      { n: "—", l: "Roles distintos (RF7)" },
      { n: "—", l: "Cuentas inactivas (RF7)" },
    ],
    colA: {
      titulo: "Usuarios recientes",
      sub: "RF7 · futuro",
      nota: "La gestión de usuarios y roles llega en una próxima entrega.",
    },
    colB: {
      titulo: "Estado del sistema",
      rows: [{ t: "API", s: "/api/health", badge: apiOk ? badgeEstado("DISPONIBLE") : badgeEstado("MANTENIMIENTO") }],
    },
  });
}

// --- Carga -----------------------------------------------------------------

async function cargarInicio() {
  pintarSaludo();

  const [misPrestamos, misReservas, recursos] = await Promise.all([
    api.get("/prestamos?mios=true").catch(() => []),
    api.get("/reservas?mias=true").catch(() => []),
    api.get("/recursos").catch(() => []),
  ]);

  pintarStats(misPrestamos, misReservas);
  pintarCatalogoDestacado(recursos);
  pintarActividad(misPrestamos, misReservas);

  const esCustodio = hasRole("CUSTODIO_CE", "CUSTODIO_INFRA");
  let prestamosActivos = [];
  if (esCustodio) {
    prestamosActivos = await api.get("/prestamos?estado=ACTIVO").catch(() => []);
  }

  const paneles = [];
  if (hasRole("CUSTODIO_CE")) paneles.push(panelCustodio("CUSTODIO_CE", prestamosActivos));
  if (hasRole("CUSTODIO_INFRA")) paneles.push(panelCustodio("CUSTODIO_INFRA", prestamosActivos));
  if (hasRole("DIRECCION_ESCUELA")) paneles.push(panelDireccion(recursos));
  if (hasRole("DOCENTE")) paneles.push(panelDocente());
  if (hasRole("ADMINISTRADOR_SISTEMA")) paneles.push(await panelAdministrador());

  document.getElementById("bloques-rol").innerHTML = paneles.join("");
}

cargarInicio();
