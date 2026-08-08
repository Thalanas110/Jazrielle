/// <reference types="vite/client" />

interface KaelithDesktopBridge {
  openTarget: (target: { app?: string | null; url?: string | null }) => Promise<void>;
}

interface Window {
  kaelithDesktop?: KaelithDesktopBridge;
}