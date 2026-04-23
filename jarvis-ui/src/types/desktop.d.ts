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
      setAmbientMode?: (enabled: boolean) => void;
      setClickThrough?: (enabled: boolean) => void;
      setOrbMode?: (enabled: boolean) => void;
      setOrbClickThrough?: (enabled: boolean) => void;
    };
  }
}

export {};
