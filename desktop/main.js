/**
 * AgentFlow Intelligence — Electron shell
 * Loads packaged SPA (extraResources/ui) or AGENTFLOW_UI_URL for remote.
 * API: AGENTFLOW_API_URL (default http://127.0.0.1:8000)
 */
const { app, BrowserWindow, shell, ipcMain, Menu } = require("electron");
const path = require("path");
const fs = require("fs");

const isDev = !app.isPackaged;
const API_URL = process.env.AGENTFLOW_API_URL || "http://127.0.0.1:8000";
const UI_URL = process.env.AGENTFLOW_UI_URL || "";

/** @type {BrowserWindow | null} */
let mainWindow = null;

function uiRoot() {
  if (isDev) {
    // Prefer Vite dev server when available
    return null;
  }
  return path.join(process.resourcesPath, "ui");
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 360,
    minHeight: 560,
    show: false,
    backgroundColor: "#050816",
    title: "AgentFlow Intelligence",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.once("ready-to-show", () => mainWindow?.show());

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  // Inject API base for renderer (settings / axios can read)
  mainWindow.webContents.on("did-finish-load", () => {
    mainWindow?.webContents
      .executeJavaScript(
        `try{localStorage.setItem('agentflow_api_base', ${JSON.stringify(API_URL)});}catch(e){}`
      )
      .catch(() => {});
  });

  if (UI_URL) {
    mainWindow.loadURL(UI_URL);
  } else if (isDev) {
    const devUrl = process.env.AGENTFLOW_DEV_URL || "http://127.0.0.1:5173";
    mainWindow.loadURL(devUrl).catch(() => {
      const distIndex = path.join(__dirname, "..", "frontend", "dist", "index.html");
      if (fs.existsSync(distIndex)) {
        mainWindow.loadFile(distIndex);
      }
    });
  } else {
    const indexHtml = path.join(uiRoot(), "index.html");
    mainWindow.loadFile(indexHtml);
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

function buildMenu() {
  const template = [
    {
      label: "AgentFlow",
      submenu: [
        {
          label: "Reload",
          role: "reload",
        },
        {
          label: "Toggle DevTools",
          role: "toggleDevTools",
        },
        { type: "separator" },
        {
          label: "Quit",
          role: "quit",
        },
      ],
    },
    {
      label: "View",
      submenu: [
        { role: "zoomIn" },
        { role: "zoomOut" },
        { role: "resetZoom" },
        { type: "separator" },
        { role: "togglefullscreen" },
      ],
    },
    {
      label: "Help",
      submenu: [
        {
          label: "API Health",
          click: () => shell.openExternal(`${API_URL}/health/ready`),
        },
        {
          label: "Documentation",
          click: () =>
            shell.openExternal("https://github.com/441732218-art/AgentFlow-Eval"),
        },
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

app.whenReady().then(() => {
  buildMenu();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

ipcMain.handle("agentflow:get-config", () => ({
  apiUrl: API_URL,
  platform: process.platform,
  version: app.getVersion(),
  packaged: app.isPackaged,
}));
