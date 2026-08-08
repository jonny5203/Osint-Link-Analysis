import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    include: ["src/**/*.test.{ts,tsx}"],
  },
  server: {
    port: 5173,
    proxy: {
      "/graphql": {
        target: process.env.NEXUS_API_TARGET ?? "http://localhost:8080",
        changeOrigin: true,
      },
    },
  },
});
