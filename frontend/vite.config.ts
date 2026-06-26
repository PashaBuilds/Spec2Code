import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// Dev: proxy API + WS to the FastAPI backend so the SPA can call relative paths.
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  server: {
    port: 5181,
    proxy: {
      "/api": { target: "http://127.0.0.1:8077", changeOrigin: true },
      "/ws": { target: "ws://127.0.0.1:8077", ws: true },
    },
  },
});
