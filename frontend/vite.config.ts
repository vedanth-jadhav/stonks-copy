import { sveltekit } from "@sveltejs/kit/vite";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backendHttp = env.BACKEND_URL || "http://127.0.0.1:8800";
  const backendWs = env.BACKEND_WS_URL || backendHttp.replace(/^http/, "ws");

  return {
    plugins: [sveltekit()],
    server: {
      port: 5173,
      proxy: {
        "/api": backendHttp,
        "/ws": {
          target: backendWs,
          ws: true,
        },
      },
    },
  };
});
