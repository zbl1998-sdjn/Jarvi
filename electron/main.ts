import { app, BrowserWindow, globalShortcut, ipcMain, Menu, Tray, nativeImage, screen } from 'electron';
import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';

import { buildSidecarCommand } from './lib/sidecar-config.js';
import { resolveRendererUrl } from './lib/resolve-renderer-url.js';
import { createMainWindowOptions, createOrbWindowOptions } from './lib/window-options.js';

const TRAY_ICON =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAOCAQAAAC1QeVaAAAASUlEQVR4AWOgNnD6z0AEYBxVSFJQkGCgJ2BkZmBg+M8ABUQxkGJgYGB4h6EYiGQGQv4HibEA4j8gH2M0gCkGkQ1QjQYkLQAAQ2wL3s0lJ4QAAAAASUVORK5CYII=';
let isQuitting = false;
let tray: Tray | null = null;

function createMainWindow(): BrowserWindow {
  const preloadPath = path.join(app.getAppPath(), 'dist-electron', 'preload.js');
  const mainWindow = new BrowserWindow(createMainWindowOptions(preloadPath));

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  const devServerUrl = process.env.VITE_DEV_SERVER_URL;
  if (devServerUrl) {
    void mainWindow.loadURL(resolveRendererUrl(devServerUrl));
    mainWindow.webContents.openDevTools({ mode: 'detach' });
    return mainWindow;
  }

  const rendererIndexPath = path.join(
    app.getAppPath(),
    'jarvis-ui',
    'dist',
    'index.html',
  );

  if (existsSync(rendererIndexPath)) {
    void mainWindow.loadFile(rendererIndexPath);
    return mainWindow;
  }

  void mainWindow.loadURL(resolveRendererUrl(undefined));
  return mainWindow;
}

function createOrbWindow(): BrowserWindow {
  const preloadPath = path.join(app.getAppPath(), 'dist-electron', 'preload.js');
  const orb = new BrowserWindow(createOrbWindowOptions(preloadPath));
  const display = screen.getPrimaryDisplay();
  const { width, height } = display.workAreaSize;
  orb.setBounds({ x: width - 210, y: height - 230, width: 180, height: 180 });

  const hash = '#/orb';
  const devServerUrl = process.env.VITE_DEV_SERVER_URL;
  if (devServerUrl) {
    void orb.loadURL(resolveRendererUrl(devServerUrl) + hash);
  } else {
    const rendererIndexPath = path.join(
      app.getAppPath(),
      'jarvis-ui',
      'dist',
      'index.html',
    );
    if (existsSync(rendererIndexPath)) {
      void orb.loadFile(rendererIndexPath, { hash: '/orb' });
    } else {
      void orb.loadURL(resolveRendererUrl(undefined) + hash);
    }
  }
  return orb;
}

function createTray(mainWindow: BrowserWindow): Tray {
  const trayInstance = new Tray(nativeImage.createFromDataURL(TRAY_ICON));
  trayInstance.setToolTip('Jarvis 智能助手');
  trayInstance.setContextMenu(
    Menu.buildFromTemplate([
      {
        label: '显示主控台',
        click: () => {
          mainWindow.show();
          mainWindow.focus();
        },
      },
      {
        label: '隐藏到托盘',
        click: () => {
          mainWindow.hide();
        },
      },
      { type: 'separator' },
      {
        label: '退出 Jarvis',
        click: () => {
          isQuitting = true;
          app.quit();
        },
      },
    ]),
  );
  trayInstance.on('double-click', () => {
    mainWindow.show();
    mainWindow.focus();
  });
  return trayInstance;
}

app.whenReady().then(() => {
  if (process.env.JARVIS_SIDECAR_MANAGED !== 'external') {
    const sidecar = buildSidecarCommand(app.getAppPath());
    spawn(sidecar.file, sidecar.args, {
      stdio: 'inherit',
      windowsHide: false,
    });
  }

  const mainWindow = createMainWindow();
  tray = createTray(mainWindow);

  let ambientMode = false;
  let prevBounds = mainWindow.getBounds();

  function applyAmbientMode(enabled: boolean) {
    if (enabled === ambientMode) return;
    ambientMode = enabled;
    if (enabled) {
      prevBounds = mainWindow.getBounds();
      const display = screen.getPrimaryDisplay();
      const { width, height } = display.workAreaSize;
      mainWindow.setResizable(true);
      mainWindow.setBounds({ x: width - 380, y: 60, width: 360, height: 520 });
      mainWindow.setAlwaysOnTop(true, 'screen-saver');
      mainWindow.setSkipTaskbar(true);
    } else {
      mainWindow.setAlwaysOnTop(false);
      mainWindow.setSkipTaskbar(false);
      mainWindow.setIgnoreMouseEvents(false);
      mainWindow.setBounds(prevBounds);
    }
    mainWindow.webContents.send('jarvis-ambient-state', enabled);
  }

  ipcMain.on('jarvis-ambient-mode', (_event, enabled: boolean) => {
    applyAmbientMode(!!enabled);
  });
  ipcMain.on('jarvis-click-through', (_event, enabled: boolean) => {
    if (!ambientMode) return;
    mainWindow.setIgnoreMouseEvents(!!enabled, { forward: true });
  });

  let orbWindow: BrowserWindow | null = null;
  ipcMain.on('jarvis-orb-mode', (_event, enabled: boolean) => {
    if (enabled) {
      if (!orbWindow || orbWindow.isDestroyed()) {
        orbWindow = createOrbWindow();
        orbWindow.on('closed', () => {
          orbWindow = null;
        });
      }
      orbWindow.show();
      orbWindow.setIgnoreMouseEvents(false);
    } else if (orbWindow && !orbWindow.isDestroyed()) {
      orbWindow.hide();
    }
  });
  ipcMain.on('jarvis-orb-click-through', (_event, enabled: boolean) => {
    if (orbWindow && !orbWindow.isDestroyed()) {
      orbWindow.setIgnoreMouseEvents(!!enabled, { forward: true });
    }
  });
  mainWindow.on('close', (event) => {
    if (isQuitting) {
      return;
    }
    event.preventDefault();
    mainWindow.hide();
  });
  globalShortcut.register('CommandOrControl+Shift+J', () => {
    mainWindow.webContents.send('jarvis-hotkey-triggered');
    if (!mainWindow.isVisible()) {
      mainWindow.show();
    }
    mainWindow.focus();
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('will-quit', () => {
  isQuitting = true;
  tray?.destroy();
  tray = null;
  globalShortcut.unregisterAll();
});
