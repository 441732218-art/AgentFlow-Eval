/* (c) 2026 AgentFlow-Eval — production Vite config with code-splitting */
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        ws: true,
      },
    },
  },
  build: {
    target: "es2020",
    cssCodeSplit: true,
    sourcemap: false,
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        /**
         * Manual chunks keep large vendor libs out of the main entry so
         * route-level lazy pages download smaller graphs on first paint.
         */
        // Split only heavy leaf vendors; let Rollup keep React shared to avoid circular chunks
        manualChunks: {
          "vendor-antd": ["antd", "@ant-design/icons"],
          "vendor-charts": ["recharts"],
          "vendor-echarts": ["echarts", "echarts-for-react"],
          "vendor-flow": ["@xyflow/react"],
          "vendor-export": ["html2canvas", "jspdf", "jspdf-autotable"],
          "vendor-query": ["@tanstack/react-query"],
        },
      },
    },
  },
  optimizeDeps: {
    include: [
      "react",
      "react-dom",
      "react-router-dom",
      "@tanstack/react-query",
      "antd",
      "axios",
      "dayjs",
      "zustand",
    ],
  },
});
