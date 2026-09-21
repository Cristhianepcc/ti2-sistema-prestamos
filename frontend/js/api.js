// Helper de API (issue #5) — molde reutilizable para consumir la API con fetch.
// Uso:  const recursos = await api.get("/recursos");
//       await api.post("/auth/login", { email, password }, { auth: false });

const API_BASE = "http://localhost:8000/api";

function getToken() { return localStorage.getItem("token"); }
function setToken(t) { localStorage.setItem("token", t); }
function clearToken() { localStorage.removeItem("token"); }

async function apiFetch(path, { method = "GET", body = null, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const t = getToken();
    if (t) headers["Authorization"] = `Bearer ${t}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : null,
  });

  // Sesión vencida o sin permiso
  if (res.status === 401) {
    clearToken();
    if (!location.pathname.endsWith("index.html")) location.href = "index.html";
    throw new Error("Sesión expirada");
  }

  const data = res.status !== 204 ? await res.json().catch(() => null) : null;
  if (!res.ok) throw new Error((data && data.detail) || `Error ${res.status}`);
  return data;
}

const api = {
  get: (p, o = {}) => apiFetch(p, { ...o, method: "GET" }),
  post: (p, body, o = {}) => apiFetch(p, { ...o, method: "POST", body }),
  put: (p, body, o = {}) => apiFetch(p, { ...o, method: "PUT", body }),
  del: (p, o = {}) => apiFetch(p, { ...o, method: "DELETE" }),
};
