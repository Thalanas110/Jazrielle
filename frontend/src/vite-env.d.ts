/// <reference types="vite/client" />

interface JazrielleDesktopBridge {
  openTarget: (target: { app?: string | null; url?: string | null }) => Promise<void>;
}

interface Window {
  jazrielleDesktop?: JazrielleDesktopBridge;
}