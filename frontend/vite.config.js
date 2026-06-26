import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,        // fail loudly if 5173 is taken instead of silently shifting
    proxy: {
      // use 127.0.0.1 (not localhost) so Node doesn't try IPv6 ::1 first and fail
      "/api": "http://127.0.0.1:8000",
      // app data socket → backend. Exact-path match so it never catches Vite's HMR socket.
      "/ws": { target: "ws://127.0.0.1:8000", ws: true, rewriteWsOrigin: true },
    },
  },
});
