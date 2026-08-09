import { useEffect, type RefObject } from 'react';
import {
  initializeNativeWindow,
  isTauriRuntime,
  listenForNativeFocus,
  syncNativeWindow,
} from './tauri-window';
import type { WindowMode } from './window-geometry';

export function useLauncherWindow(
  mode: WindowMode,
  rootRef: RefObject<HTMLElement | null> | { current: HTMLElement | null },
  onClose: () => void,
) {
  const native = isTauriRuntime();

  useEffect(() => {
    void initializeNativeWindow();
  }, []);

  useEffect(() => {
    void syncNativeWindow(mode);
  }, [mode]);

  useEffect(() => {
    if (!native) return undefined;

    let mounted = true;
    let unlisten: (() => void) | undefined;
    void listenForNativeFocus((focused) => {
      if (mounted && mode === 'expanded' && !focused) onClose();
    }).then((cleanup) => {
      if (mounted) unlisten = cleanup;
      else cleanup();
    });

    return () => {
      mounted = false;
      unlisten?.();
    };
  }, [mode, native, onClose]);

  useEffect(() => {
    if (native || mode !== 'expanded') return undefined;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    const handlePointerDown = (event: PointerEvent) => {
      const root = rootRef.current;
      if (root && !root.contains(event.target as Node)) onClose();
    };

    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('pointerdown', handlePointerDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('pointerdown', handlePointerDown);
    };
  }, [mode, native, onClose, rootRef]);
}
