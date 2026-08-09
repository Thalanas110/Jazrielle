import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  initializeNativeWindow,
  isTauriRuntime,
  listenForNativeFocus,
  syncNativeWindow,
} from './tauri-window';

describe('tauri window adapter', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('detects browser development without native internals', () => {
    vi.stubGlobal('__TAURI_INTERNALS__', undefined);
    expect(isTauriRuntime()).toBe(false);
  });

  it('does not reject when geometry is requested in the browser', async () => {
    vi.stubGlobal('__TAURI_INTERNALS__', undefined);
    await expect(syncNativeWindow('collapsed')).resolves.toBe(false);
  });

  it('keeps native startup a no-op in the browser', async () => {
    vi.stubGlobal('__TAURI_INTERNALS__', undefined);

    await expect(initializeNativeWindow()).resolves.toBe(false);
  });

  it('returns a harmless focus cleanup in the browser', async () => {
    vi.stubGlobal('__TAURI_INTERNALS__', undefined);

    const cleanup = await listenForNativeFocus(vi.fn());

    expect(cleanup()).toBeUndefined();
  });
});
