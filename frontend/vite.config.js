import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// El proxy envía /api y /admin al backend Django: no hay problemas de CORS en desarrollo.
// En GitHub Codespaces la página llega por *.app.github.dev y no hay navegador que abrir.
const inCodespaces = Boolean(process.env.CODESPACES);

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    open: !inCodespaces,
    allowedHosts: ["localhost", "127.0.0.1", ".app.github.dev", ".github.dev"],
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/admin": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/static": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/media": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
