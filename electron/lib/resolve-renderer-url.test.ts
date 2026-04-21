import { describe, expect, it } from 'vitest';

import { resolveRendererUrl } from './resolve-renderer-url';

describe('resolveRendererUrl', () => {
  it('uses the Vite dev server URL when provided', () => {
    expect(resolveRendererUrl('http://127.0.0.1:5173')).toBe(
      'http://127.0.0.1:5173',
    );
  });

  it('falls back to about:blank without a dev server URL', () => {
    expect(resolveRendererUrl(undefined)).toBe('about:blank');
  });
});
