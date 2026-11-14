import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

// In dev, proxy API calls to the FastAPI backend (override with VITE_BACKEND_URL).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "VITE_");
  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: { "/api": env.VITE_BACKEND_URL ?? "http://localhost:8000" },
    },
  };
});
