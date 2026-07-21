/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

interface ElectronAPI {
  getConfig: () => Promise<{
    apiUrl: string;
    platform: string;
    version: string;
    packaged: boolean;
  }>;
  platform: string;
  isDesktop: boolean;
}

interface Window {
  electronAPI?: ElectronAPI;
}
