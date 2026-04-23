import { contextBridge, ipcRenderer } from 'electron';

function getServerBaseUrl() {
  const host =
    process.env.JARVIS_SERVER_HOST === '0.0.0.0'
      ? '127.0.0.1'
      : (process.env.JARVIS_SERVER_HOST ?? '127.0.0.1');
  const port = process.env.JARVIS_SERVER_PORT ?? '8001';
  return `http://${host}:${port}`;
}

contextBridge.exposeInMainWorld('jarvisDesktop', {
  getShellInfo: () => ({
    app: 'Jarvis',
    mode: 'm6',
    resident: true,
  }),
  getServerBaseUrl,
  onHotkeyTriggered: (callback: () => void) => {
    const listener = () => callback();
    ipcRenderer.on('jarvis-hotkey-triggered', listener);
    return () => {
      ipcRenderer.removeListener('jarvis-hotkey-triggered', listener);
    };
  },
  setAmbientMode: (enabled: boolean) => {
    ipcRenderer.send('jarvis-ambient-mode', enabled);
  },
  setClickThrough: (enabled: boolean) => {
    ipcRenderer.send('jarvis-click-through', enabled);
  },
  setOrbMode: (enabled: boolean) => {
    ipcRenderer.send('jarvis-orb-mode', enabled);
  },
  setOrbClickThrough: (enabled: boolean) => {
    ipcRenderer.send('jarvis-orb-click-through', enabled);
  },
});
