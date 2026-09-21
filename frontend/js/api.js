// Helper de API (issue #5) — molde reutilizable para consumir la API con fetch.
//
// Uso rápido:
//   await api.login(email, password);          // guarda el token
//   const recursos = await api.get("/recursos?disponible=true");
//   api.logout();
//
// Ejemplos completos (login y catálogo) en frontend/README.md.
// Contrato de la API: docs/02-contrato-api.md

const API_BASE = "http://localhost:8000/api";
const LOGIN_PAGE = "index.html";

// --- Sesión -----------------------------------------------------------------

function getToken() {
  return localStorage.getItem("token");
}

function setSession(token, user) {
  localStorage.setItem("token", token);
  localStorage.setItem("user", JSON.stringify(user));
}

function clearSession() {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
}

// Usuario logueado (lo guardamos en el login para no llamar a /auth/me en cada página).
function currentUser() {
  try {
    return JSON.parse(localStorage.getItem("user"));
  } catch {
    return null;
  }
}

function hasRole(...roles) {
  const user = currentUser();
  return !!user && roles.some((rol) => user.roles.includes(rol));
}

function onLoginPage() {
  const archivo = location.pathname.split("/").pop();
  // "" cubre el caso de servir la carpeta como raíz: http://localhost:5500/
  return archivo === "" || archivo === LOGIN_PAGE;
}

// Poné esto al inicio de toda página que requiera sesión.
function requireAuth() {
  if (!getToken()) {
    location.href = LOGIN_PAGE;
    return false;
  }
  return true;
}

// --- Errores ----------------------------------------------------------------

// Error con el código HTTP, para poder ramificar: if (e.status === 403) ...
class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function errorMessage(status, data) {
  const detail = data && data.detail;
  if (typeof detail === "string") return detail;
  // El 422 de FastAPI trae una lista de errores de validación, no un string.
  if (Array.isArray(detail)) return "Revisá los datos del formulario.";
  return `Error ${status}`;
}

// --- fetch ------------------------------------------------------------------

async function apiFetch(path, { method = "GET", body = null, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : null,
    });
  } catch {
    // Falla de red: la API está caída, el puerto es otro, o falta el origen en CORS.
    throw new ApiError(0, "No se pudo conectar con la API. ¿Está corriendo en :8000?");
  }

  const data = res.status !== 204 ? await res.json().catch(() => null) : null;

  if (res.ok) return data;

  // OJO: un 401 solo significa "sesión vencida" en llamadas que van con token.
  // En el login (auth: false) un 401 es "credenciales inválidas" y hay que dejar
  // que la página lo muestre, no redirigir ni borrar nada.
  if (res.status === 401 && auth) {
    clearSession();
    if (!onLoginPage()) location.href = LOGIN_PAGE;
  }

  throw new ApiError(res.status, errorMessage(res.status, data));
}

// --- API pública ------------------------------------------------------------

const api = {
  get: (p, o = {}) => apiFetch(p, { ...o, method: "GET" }),
  post: (p, body, o = {}) => apiFetch(p, { ...o, method: "POST", body }),
  put: (p, body, o = {}) => apiFetch(p, { ...o, method: "PUT", body }),
  patch: (p, body, o = {}) => apiFetch(p, { ...o, method: "PATCH", body }),
  del: (p, o = {}) => apiFetch(p, { ...o, method: "DELETE" }),

  // Hace login y deja la sesión guardada. Devuelve el usuario.
  // Si las credenciales son incorrectas lanza ApiError con status 401 y el
  // mensaje del backend ("Credenciales inválidas" / "Usuario inactivo").
  async login(email, password) {
    const data = await apiFetch("/auth/login", {
      method: "POST",
      body: { email, password },
      auth: false,
    });
    setSession(data.access_token, data.user);
    return data.user;
  },

  logout() {
    clearSession();
    location.href = LOGIN_PAGE;
  },

  // Revalida la sesión contra el backend (útil al recargar una página protegida).
  me: () => apiFetch("/auth/me"),
};
