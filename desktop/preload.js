const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  getConfig: () => ipcRenderer.invoke("agentflow:get-config"),
  platform: process.platform,
  isDesktop: true,
});
