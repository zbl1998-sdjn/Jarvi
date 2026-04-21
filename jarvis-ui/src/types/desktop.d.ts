declare global {
  interface Window {
    jarvisDesktop?: {
      getShellInfo: () => {
        app: string;
        mode: string;
        resident?: boolean;
      };
      getServerBaseUrl: () => string;
      onHotkeyTriggered?: (callback: () => void) => (() => void) | void;
    };
  }
}

export {};
