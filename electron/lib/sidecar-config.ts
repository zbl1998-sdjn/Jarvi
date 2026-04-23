import path from 'node:path';

export function buildSidecarCommand(appRoot: string) {
  return {
    file: 'powershell.exe',
    args: [
      '-NoProfile',
      '-ExecutionPolicy',
      'Bypass',
      '-File',
      path.win32.join(appRoot, 'scripts', 'dev-server.ps1'),
    ],
  };
}
