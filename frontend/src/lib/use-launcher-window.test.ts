import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { syncNativeWindow } from './tauri-window';
import { useLauncherWindow } from './use-launcher-window';

vi.mock('./tauri-window', () => ({
  isTauriRuntime: vi.fn(() => false),
  syncNativeWindow: vi.fn(() => Promise.resolve(false)),
  initializeNativeWindow: vi.fn(() => Promise.resolve(false)),
  listenForNativeFocus: vi.fn(() => Promise.resolve(() => undefined)),
}));

describe('useLauncherWindow', () => {
  afterEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = '';
  });

  it('synchronizes the requested browser-safe mode', async () => {
    const root = document.createElement('div');
    document.body.appendChild(root);
    const rootRef = { current: root };

    renderHook(() => useLauncherWindow('expanded', rootRef, vi.fn()));

    await waitFor(() => expect(syncNativeWindow).toHaveBeenCalledWith('expanded'));
  });

  it('closes on Escape and outside pointer events', async () => {
    const root = document.createElement('div');
    document.body.appendChild(root);
    const onClose = vi.fn();
    const rootRef = { current: root };
    renderHook(() => useLauncherWindow('expanded', rootRef, onClose));

    act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
      document.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));
    });

    expect(onClose).toHaveBeenCalledTimes(2);
  });
});
