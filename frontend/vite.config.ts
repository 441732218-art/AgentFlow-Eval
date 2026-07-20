/* (c) 2026 AgentFlow-Eval — production Vite config with code-splitting + PWA */
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import { resolve } from "path";

export default defineConfig(({ mode }) => {
  const isElectron = mode === "electron" || process.env.ELECTRON === "1";

  return {
    // Relative base for Electron file:// / custom protocol packaging
    base: isElectron ? "./" : "/",
    plugins: [
      react(),
      VitePWA({
        registerType: "autoUpdate",
        includeAssets: [
          "favicon.svg",
          "assets/logo/favicon.svg",
          "assets/logo/logo.svg",
          "assets/logo/logo-dark.svg",
          "brand/*.svg",
        ],
        manifest: {
          name: "AgentFlow Intelligence",
          short_name: "AgentFlow",
          description:
            "Enterprise AI Agent Observability · Evaluation · Diagnosis platform",
          theme_color: "#050816",
          background_color: "#050816",
          display: "standalone",
          orientation: "any",
          start_url: "/",
          scope: "/",
          lang: "zh-CN",
          categories: ["productivity", "developer", "business"],
          icons: [
            {
              src: "/assets/logo/logo.svg",
              sizes: "any",
              type: "image/svg+xml",
              purpose: "any",
            },
            {
              src: "/assets/logo/favicon.svg",
              sizes: "any",
              type: "image/svg+xml",
              purpose: "maskable",
            },
            {
              src: "/pwa-192.png",
              sizes: "192x192",
              type: "image/png",
              purpose: "any",
            },
            {
              src: "/pwa-512.png",
              sizes: "512x512",
              type: "image/png",
              purpose: "any",
            },
          ],
          shortcuts: [
            {
              name: "Dashboard",
              short_name: "驾驶舱",
              url: "/dashboard",
              icons: [{ src: "/assets/logo/favicon.svg", sizes: "any" }],
            },
            {
              name: "Tasks",
              short_name: "任务",
              url: "/tasks",
              icons: [{ src: "/assets/logo/favicon.svg", sizes: "any" }],
            },
          ],
        },
        workbox: {
          // App shell + static assets; API always network-first
          globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2,json}"],
          navigateFallback: "/index.html",
          navigateFallbackDenylist: [/^\/api\//, /^\/health/, /^\/metrics/, /^\/docs/],
          runtimeCaching: [
            {
              urlPattern: ({ url }) =>
                url.pathname.startsWith("/api/") ||
                url.pathname.startsWith("/health") ||
                url.pathname.startsWith("/metrics"),
              handler: "NetworkOnly",
            },
            {
              urlPattern: /^https:\/\/fonts\.(googleapis|gstatic)\.com\/.*/i,
              handler: "CacheFirst",
              options: {
                cacheName: "google-fonts",
                expiration: { maxEntries: 20, maxAgeSeconds: 60 * 60 * 24 * 365 },
              },
            },
          ],
        },
        devOptions: {
          enabled: false,
        },
      }),
    ],
    resolve: {
      alias: {
        "@": resolve(__dirname, "src"),
      },
    },
    server: {
      host: "0.0.0.0",
      port: 5173,
      proxy: {
        "/api": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
          ws: true,
          secure: false,
        },
        "/health": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
        },
      },
    },
    build: {
      target: "es2020",
      cssCodeSplit: true,
      sourcemap: false,
      chunkSizeWarningLimit: 900,
      outDir: "dist",
      emptyOutDir: true,
      rollupOptions: {
        output: {
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
  };
});
