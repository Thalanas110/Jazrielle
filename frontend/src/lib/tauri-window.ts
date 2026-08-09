import { LogicalPosition, LogicalSize } from '@tauri-apps/api/dpi';
import { currentMonitor, getCurrentWindow } from '@tauri-apps/api/window';
import {
  getBottomRightPosition,
  getWindowSize,
  type WindowMode,
} from './window-geometry';

export function isTauriRuntime(): boolean {
  return typeof globalThis !== 'undefined'
    && '__TAURI_INTERNALS__' in globalThis
    && Boolean(Reflect.get(globalThis, '__TAURI_INTERNALS__'));
}

export async function syncNativeWindow(mode: WindowMode): Promise<boolean> {
  if (!isTauriRuntime()) return false;

  const monitor = await currentMonitor();
  if (!monitor) return false;

  const scaleFactor = monitor.scaleFactor;
  const workArea = {
    x: monitor.workArea.position.x / scaleFactor,
    y: monitor.workArea.position.y / scaleFactor,
    width: monitor.workArea.size.width / scaleFactor,
    height: monitor.workArea.size.height / scaleFactor,
  };
  const size = getWindowSize(mode);
  const position = getBottomRightPosition(workArea, mode);
  const nativeWindow = getCurrentWindow();

  await nativeWindow.setSize(new LogicalSize(size.width, size.height));
  await nativeWindow.setPosition(new LogicalPosition(position.x, position.y));
  await nativeWindow.setAlwaysOnTop(true);
  await nativeWindow.setSkipTaskbar(true);
  if (mode === 'expanded') await nativeWindow.setFocus();
  return true;
}

export async function initializeNativeWindow(): Promise<boolean> {
  if (!isTauriRuntime()) return false;

  const nativeWindow = getCurrentWindow();
  await nativeWindow.setAlwaysOnTop(true);
  await nativeWindow.setSkipTaskbar(true);
  await syncNativeWindow('collapsed');
  await nativeWindow.show();
  return true;
}

export async function listenForNativeFocus(onFocusChange: (focused: boolean) => void): Promise<() => void> {
  if (!isTauriRuntime()) return () => undefined;

  return getCurrentWindow().onFocusChanged(({ payload }) => onFocusChange(payload));
}
