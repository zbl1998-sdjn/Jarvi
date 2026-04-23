import { describe, expect, it } from 'vitest';

import { createMainWindowOptions, createOrbWindowOptions } from './window-options';

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

describe('createOrbWindowOptions', () => {
  it('is a small, transparent, borderless, always-on-top hologram orb', () => {
    const options = createOrbWindowOptions('D:\\preload.js');

    expect(options.frame).toBe(false);
    expect(options.transparent).toBe(true);
    expect(options.alwaysOnTop).toBe(true);
    expect(options.skipTaskbar).toBe(true);
    expect(options.resizable).toBe(false);
    expect(options.hasShadow).toBe(false);
    expect(options.width).toBe(180);
    expect(options.height).toBe(180);
    expect(options.show).toBe(false);
  });
});

