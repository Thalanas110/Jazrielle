import { afterEach, describe, expect, it, vi } from 'vitest';
import { isTauriRuntime, syncNativeWindow } from './tauri-window';

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
});
