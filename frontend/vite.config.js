import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server na porta 5173. O backend (FastAPI) roda em :8000 e tem CORS
// liberado, então o fetch direto funciona. Se preferir evitar CORS, dá pra
// usar o proxy abaixo e chamar "/api/..." no lugar de VITE_API_BASE.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "https://meu-minerador-exclusivo.loca.lt",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
