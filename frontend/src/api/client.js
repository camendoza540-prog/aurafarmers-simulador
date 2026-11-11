import axios from "axios";

const ACCESS = "af_access";
const REFRESH = "af_refresh";

export const tokens = {
  get access() { return localStorage.getItem(ACCESS); },
  get refresh() { return localStorage.getItem(REFRESH); },
  set({ access, refresh }) {
    if (access) localStorage.setItem(ACCESS, access);
    if (refresh) localStorage.setItem(REFRESH, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS);
    localStorage.removeItem(REFRESH);
  },
};

const api = axios.create({ baseURL: "/api", timeout: 20000 });

api.interceptors.request.use((config) => {
  if (tokens.access) config.headers.Authorization = `Bearer ${tokens.access}`;
  return config;
});

// Renovación automática del token de acceso cuando expira (una sola petición a la vez).
let refreshing = null;
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    const isAuthCall = original?.url?.includes("/auth/login") || original?.url?.includes("/auth/refresh");
    if (error.response?.status === 401 && !original._retry && tokens.refresh && !isAuthCall) {
      original._retry = true;
      try {
        refreshing = refreshing || axios.post("/api/auth/refresh/", { refresh: tokens.refresh });
        const { data } = await refreshing;
        tokens.set(data);
        original.headers.Authorization = `Bearer ${data.access}`;
        return api(original);
      } catch (e) {
        tokens.clear();
        window.dispatchEvent(new Event("af:logout"));
      } finally {
        refreshing = null;
      }
    }
    return Promise.reject(error);
  }
);

/** Convierte un error de DRF en un mensaje legible. */
export function errorMessage(err, fallback = "Algo salió mal. Intenta de nuevo.") {
  if (!err?.response) return "No hay conexión con el servidor. Verifica que el backend esté corriendo en el puerto 8000.";
  const d = err.response.data;
  if (!d || typeof d === "string") return fallback;
  if (d.detail) return d.detail;
  const first = Object.entries(d)[0];
  if (first) {
    const msgs = first[1];
    return Array.isArray(msgs) ? String(msgs[0]) : String(msgs);
  }
  return fallback;
}

/** Errores por campo para formularios. */
export function fieldErrors(err) {
  const d = err?.response?.data;
  if (!d || typeof d !== "object") return {};
  const out = {};
  for (const [k, v] of Object.entries(d)) out[k] = Array.isArray(v) ? v[0] : String(v);
  return out;
}

export default api;
