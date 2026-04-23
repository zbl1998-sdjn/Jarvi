import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { loadHealth } from './assistant-client';

// Stub window.jarvisDesktop so getServerBaseUrl() returns a predictable value
const BASE = 'http://127.0.0.1:8001';

describe('fetchJson header merging', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'jarvisDesktop', {
      value: undefined,
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('preserves default Content-Type when caller also passes custom headers', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({ ok: true, service: 'test', mode: 'mock', degraded: false, dependencies: { database: 'ok' } }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );

    // loadHealth passes { headers: { Accept: 'application/json' } }
    // which previously clobbered the merged Content-Type header
    await loadHealth();

    expect(fetchSpy).toHaveBeenCalledOnce();
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];

    expect(url).toBe(`${BASE}/api/health`);

    // Both the default and the caller-supplied header must survive
    const headers = init.headers as Record<string, string>;
    expect(headers['Content-Type']).toBe('application/json');
    expect(headers['Accept']).toBe('application/json');
  });
});
