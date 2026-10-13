import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    extensions: [".tsx", ".ts", ".jsx", ".js", ".json"],
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: parseInt(process.env.WEB_PORT || "5173"),
    proxy: {
      "/api": `http://localhost:${process.env.API_PORT || "8000"}`,
      "/site": `http://localhost:${process.env.API_PORT || "8000"}`,
      // B330: avatars. nginx serves /uploads/ in production; without nginx
      // the API does, and the SPA fallback would otherwise return index.html.
      "/uploads": `http://localhost:${process.env.API_PORT || "8000"}`,
      "/openapi.json": `http://localhost:${process.env.API_PORT || "8000"}`,
      "/openapi.yaml": `http://localhost:${process.env.API_PORT || "8000"}`,
    },
  },
});
