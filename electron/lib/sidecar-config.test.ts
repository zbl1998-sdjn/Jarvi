import { describe, expect, it } from 'vitest';

import { buildSidecarCommand } from './sidecar-config';

describe('buildSidecarCommand', () => {
  it('returns the uvicorn dev command for Windows PowerShell', () => {
    expect(buildSidecarCommand()).toEqual({
      file: 'powershell.exe',
      args: [
        '-NoProfile',
        '-ExecutionPolicy',
        'Bypass',
        '-File',
        'D:\\Jarvis\\scripts\\dev-server.ps1',
      ],
    });
  });
});
