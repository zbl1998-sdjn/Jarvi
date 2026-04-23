import type { BrowserWindowConstructorOptions } from 'electron';

export function createMainWindowOptions(
  preloadPath: string,
): BrowserWindowConstructorOptions {
  return {
    width: 1600,
    height: 980,
    minWidth: 360,
    minHeight: 400,
    backgroundColor: '#07111f',
    title: 'Jarvis 智能助手',
    webPreferences: {
      preload: preloadPath,
      contextIsolation: true,
      nodeIntegration: false,
    },
  };
}

export function createOrbWindowOptions(
  preloadPath: string,
): BrowserWindowConstructorOptions {
  return {
    width: 180,
    height: 180,
    show: false,
    frame: false,
    transparent: true,
    resizable: false,
    skipTaskbar: true,
    alwaysOnTop: true,
    hasShadow: false,
    backgroundColor: '#00000000',
    title: 'Jarvis Orb',
    webPreferences: {
      preload: preloadPath,
      contextIsolation: true,
      nodeIntegration: false,
    },
  };
}

