// Inicio (dashboard de bienvenida, issue #43). Usa datos reales de los
// endpoints que ya existen (/prestamos, /reservas, /recursos). Las secciones
// que dependen de RF4/RF6/RF7 (todavía sin backend) muestran una nota, no
// números inventados.

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

// --- Saludo + chips de rol ----------------------------------------------------

function pintarSaludo() {
  const chips = usuario.roles.map((r) => `<span class="role-chip">${esc(ETIQUETA_ROL[r] || r)}</span>`).join("");
  document.getElementById("saludo").innerHTML =
    `Hola, <b>${esc(usuario.nombres.split(" ")[0])}</b>${chips}`;
}

// --- Stats (préstamos propios, reservas propias) ------------------------------

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

  document.getElementById("stats").innerHTML = stats
    .map((s) => `<div class="stat"><div class="n"${s.color ? ` style="color:var(--${s.color})"` : ""}>${esc(s.n)}</div><div class="l">${esc(s.l)}</div></div>`)
    .join("");
}

// --- Catálogo destacado --------------------------------------------------------

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

// --- Tus préstamos y reservas (actividad real, no inventada) -------------------

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

// --- Bloques por rol ------------------------------------------------------------

const GESTOR_POR_ROL_CUSTODIO = {
  CUSTODIO_CE: "CENTRO_ESTUDIANTES",
  CUSTODIO_INFRA: "INFRAESTRUCTURA",
};

async function bloqueCustodio(rol) {
  const gestor = GESTOR_POR_ROL_CUSTODIO[rol];
  let activos = [];
  try {
    activos = await api.get("/prestamos?estado=ACTIVO");
  } catch {
    return "";
  }
  const delGestor = activos.filter((p) => p.recurso && p.recurso.gestor === gestor);
  const vencenPronto = delGestor.filter((p) => diasHasta(p.fecha_limite) < 2).length;

  return `
    <div class="bloque-rol">
      <div class="block-title">Panel de custodio <span>${esc(ETIQUETA_ROL[rol])}</span></div>
      <div class="stat-row">
        <div class="stat"><div class="n">${delGestor.length}</div><div class="l">Préstamos activos</div></div>
        <div class="stat"><div class="n"${vencenPronto > 0 ? ' style="color:var(--warn)"' : ""}>${vencenPronto}</div><div class="l">Vencen pronto</div></div>
        <div class="stat" style="display:flex;align-items:center;">
          <a href="registrar-prestamo.html" class="btn btn-primary btn-block">Ir al Panel Custodio</a>
        </div>
      </div>
    </div>`;
}

function bloqueDireccion(recursos) {
  const conteos = {};
  for (const r of recursos) conteos[r.tipo_recurso] = (conteos[r.tipo_recurso] || 0) + 1;

  const filas = Object.entries(conteos)
    .map(([tipo, n]) => `<div class="mini-row"><div class="t">${esc(ETIQUETA_TIPO[tipo] || tipo)}</div><div class="s">${esc(n)} recursos</div></div>`)
    .join("");

  return `
    <div class="bloque-rol">
      <div class="block-title">Inventario por tipo <span>Dirección de Escuela</span></div>
      ${filas}
      <p class="nota-futura" style="margin-top:10px;">La bandeja de autorizaciones (RF4) y los reportes completos (RF6) llegan en una próxima entrega.</p>
    </div>`;
}

function bloqueNotaFutura(rol, texto) {
  return `
    <div class="bloque-rol">
      <div class="block-title">${esc(ETIQUETA_ROL[rol])}</div>
      <p class="nota-futura">${texto}</p>
    </div>`;
}

async function bloqueAdministrador() {
  let apiOk = false;
  try {
    const salud = await api.get("/health");
    apiOk = salud.status === "ok";
  } catch {
    apiOk = false;
  }

  return `
    <div class="bloque-rol">
      <div class="block-title">Estado del sistema</div>
      <div class="mini-row"><div class="t">API</div>${apiOk ? badgeEstado("DISPONIBLE") : badgeEstado("MANTENIMIENTO")}</div>
      <p class="nota-futura" style="margin-top:10px;">La gestión de usuarios y roles (RF7) llega en una próxima entrega.</p>
    </div>`;
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

  const bloques = [];
  if (hasRole("CUSTODIO_CE")) bloques.push(await bloqueCustodio("CUSTODIO_CE"));
  if (hasRole("CUSTODIO_INFRA")) bloques.push(await bloqueCustodio("CUSTODIO_INFRA"));
  if (hasRole("DIRECCION_ESCUELA")) bloques.push(bloqueDireccion(recursos));
  if (hasRole("DOCENTE")) {
    bloques.push(
      bloqueNotaFutura("DOCENTE", "Avalar solicitudes académicas de tus alumnos (RF4) llega en una próxima entrega.")
    );
  }
  if (hasRole("ADMINISTRADOR_SISTEMA")) bloques.push(await bloqueAdministrador());

  document.getElementById("bloques-rol").innerHTML = bloques.join("");
}

cargarInicio();
