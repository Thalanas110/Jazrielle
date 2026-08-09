import { afterEach, describe, expect, it, vi } from 'vitest';
import { getApiBaseUrl } from './api';

describe('getApiBaseUrl', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it('uses VITE_API_URL when configured', () => {
    vi.stubEnv('VITE_API_URL', 'http://localhost:9100/api');
    vi.stubGlobal('__TAURI_INTERNALS__', undefined);

    expect(getApiBaseUrl()).toBe('http://localhost:9100/api');
  });

  it('uses the browser proxy outside Tauri', () => {
    vi.stubGlobal('__TAURI_INTERNALS__', undefined);

    expect(getApiBaseUrl()).toBe('/api');
  });

  it('uses the loopback backend inside Tauri', () => {
    vi.stubGlobal('__TAURI_INTERNALS__', { invoke: vi.fn() });

    expect(getApiBaseUrl()).toBe('http://127.0.0.1:8000/api');
  });
});
