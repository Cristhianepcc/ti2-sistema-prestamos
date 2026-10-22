// Prototipo de frontend (sin backend) del flujo Solicitud → Aceptación →
// Notificación descrito en docs/00-contexto-alcance-propuesta.md §8 (hallazgo
// #13) y docs/02-contrato-api.md (Anexo RF3/RF4). Vive solo en localStorage:
// sirve para validar el diseño de las pantallas antes de escribir el backend
// real (no hay endpoint /solicitudes ni /notificaciones todavía).
//
// Requiere api.js (currentUser) ya cargado antes.

const MOCK_SOLICITUDES_KEY = "mock_solicitudes";
const MOCK_NOTIFICACIONES_KEY = "mock_notificaciones";

function mockLeer(key) {
  try {
    return JSON.parse(localStorage.getItem(key)) || [];
  } catch {
    return [];
  }
}

function mockGuardar(key, lista) {
  localStorage.setItem(key, JSON.stringify(lista));
}

function mockSiguienteId(lista) {
  return lista.reduce((max, x) => Math.max(max, x.id), 0) + 1;
}

const GESTOR_POR_ROL_CUSTODIO = {
  CUSTODIO_CE: "CENTRO_ESTUDIANTES",
  CUSTODIO_INFRA: "INFRAESTRUCTURA",
};

const LUGAR_POR_GESTOR = {
  CENTRO_ESTUDIANTES: "el Centro de Estudiantes",
  INFRAESTRUCTURA: "Infraestructura",
};

const MockSolicitudes = {
  listar() {
    return mockLeer(MOCK_SOLICITUDES_KEY);
  },

  // El usuario ya tiene una solicitud sin resolver para ese recurso — evita
  // que mande la misma solicitud diez veces en la demo.
  tieneSolicitudActiva(recursoId, email) {
    return this.listar().some(
      (s) =>
        s.recurso_id === recursoId &&
        s.solicitante_email === email &&
        ["SOLICITADA", "AVALADA", "AUTORIZADA"].includes(s.estado)
    );
  },

  crear({ recurso, tipoSolicitud, motivo }) {
    const usuario = currentUser();
    const lista = this.listar();
    const solicitud = {
      id: mockSiguienteId(lista),
      recurso_id: recurso.id,
      recurso_nombre: recurso.nombre,
      recurso_codigo: recurso.codigo,
      tipo_recurso: recurso.tipo_recurso,
      gestor: recurso.gestor,
      solicitante_email: usuario.email,
      solicitante_nombre: usuario.nombres,
      tipo_solicitud: tipoSolicitud,
      motivo: motivo || null,
      estado: "SOLICITADA",
      motivo_rechazo: null,
      created_at: new Date().toISOString(),
    };
    lista.push(solicitud);
    mockGuardar(MOCK_SOLICITUDES_KEY, lista);
    return solicitud;
  },

  // Bandeja del custodio autenticado: lo que ya puede aceptar o rechazar.
  // SIMPLE llega directo; POR_CURSO/EXCEPCIONAL requieren aval/autorización
  // previos (RF4), que este prototipo no simula — por eso quedan esperando.
  pendientesParaCustodio(rol) {
    const gestor = GESTOR_POR_ROL_CUSTODIO[rol];
    return this.listar().filter((s) => {
      if (s.gestor !== gestor) return false;
      if (s.tipo_solicitud === "SIMPLE") return s.estado === "SOLICITADA";
      if (s.tipo_solicitud === "POR_CURSO") return s.estado === "AVALADA";
      if (s.tipo_solicitud === "EXCEPCIONAL") return s.estado === "AUTORIZADA";
      return false;
    });
  },

  aceptar(id) {
    const lista = this.listar();
    const solicitud = lista.find((s) => s.id === id);
    if (!solicitud) return null;
    solicitud.estado = "ACEPTADA";
    solicitud.aceptado_por_email = currentUser().email;
    mockGuardar(MOCK_SOLICITUDES_KEY, lista);
    this._notificar(solicitud, "SOLICITUD_ACEPTADA");
    return solicitud;
  },

  rechazar(id, motivoRechazo) {
    const lista = this.listar();
    const solicitud = lista.find((s) => s.id === id);
    if (!solicitud) return null;
    solicitud.estado = "RECHAZADA";
    solicitud.motivo_rechazo = motivoRechazo || null;
    mockGuardar(MOCK_SOLICITUDES_KEY, lista);
    this._notificar(solicitud, "SOLICITUD_RECHAZADA");
    return solicitud;
  },

  _notificar(solicitud, tipo) {
    const lugar = LUGAR_POR_GESTOR[solicitud.gestor] || "el custodio";
    const mensaje =
      tipo === "SOLICITUD_ACEPTADA"
        ? `Tu solicitud de "${solicitud.recurso_nombre}" fue aceptada. Preséntate en ${lugar} antes de las 18:00 de hoy para recogerlo.`
        : `Tu solicitud de "${solicitud.recurso_nombre}" fue rechazada.${
            solicitud.motivo_rechazo ? " Motivo: " + solicitud.motivo_rechazo : ""
          }`;
    const lista = mockLeer(MOCK_NOTIFICACIONES_KEY);
    lista.push({
      id: mockSiguienteId(lista),
      usuario_email: solicitud.solicitante_email,
      solicitud_id: solicitud.id,
      tipo,
      mensaje,
      leida: false,
      created_at: new Date().toISOString(),
    });
    mockGuardar(MOCK_NOTIFICACIONES_KEY, lista);
  },
};

const MockNotificaciones = {
  listar(email) {
    return mockLeer(MOCK_NOTIFICACIONES_KEY)
      .filter((n) => n.usuario_email === email)
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  },

  noLeidas(email) {
    return this.listar(email).filter((n) => !n.leida).length;
  },

  marcarLeida(id) {
    const lista = mockLeer(MOCK_NOTIFICACIONES_KEY);
    const n = lista.find((x) => x.id === id);
    if (n) n.leida = true;
    mockGuardar(MOCK_NOTIFICACIONES_KEY, lista);
  },
};
