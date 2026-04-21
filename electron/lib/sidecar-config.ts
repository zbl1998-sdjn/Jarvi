export function buildSidecarCommand() {
  return {
    file: 'powershell.exe',
    args: [
      '-NoProfile',
      '-ExecutionPolicy',
      'Bypass',
      '-File',
      'D:\\Jarvis\\scripts\\dev-server.ps1',
    ],
  };
}
