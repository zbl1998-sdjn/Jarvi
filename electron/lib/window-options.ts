import type { BrowserWindowConstructorOptions } from 'electron';

export function createMainWindowOptions(
  preloadPath: string,
): BrowserWindowConstructorOptions {
  return {
    width: 1600,
    height: 980,
    minWidth: 1280,
    minHeight: 720,
    backgroundColor: '#07111f',
    title: 'Jarvis 智能助手',
    webPreferences: {
      preload: preloadPath,
      contextIsolation: true,
      nodeIntegration: false,
    },
  };
}
