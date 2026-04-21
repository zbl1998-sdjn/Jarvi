import { describe, expect, it } from 'vitest';

import { createMainWindowOptions } from './window-options';

describe('createMainWindowOptions', () => {
  it('uses the Jarvis preload bridge and dark background', () => {
    const options = createMainWindowOptions(
      'D:\\Jarvis\\dist-electron\\preload.js',
    );

    expect(options.width).toBe(1600);
    expect(options.backgroundColor).toBe('#07111f');
    expect(options.title).toBe('Jarvis 智能助手');
    expect(options.webPreferences?.preload).toBe(
      'D:\\Jarvis\\dist-electron\\preload.js',
    );
  });
});
