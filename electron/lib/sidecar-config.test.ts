import { describe, expect, it } from 'vitest';

import { buildSidecarCommand } from './sidecar-config';

describe('buildSidecarCommand', () => {
  it('builds the dev server script path from the app root', () => {
    expect(buildSidecarCommand('D:\\Projects\\Jarvis')).toEqual({
      file: 'powershell.exe',
      args: [
        '-NoProfile',
        '-ExecutionPolicy',
        'Bypass',
        '-File',
        'D:\\Projects\\Jarvis\\scripts\\dev-server.ps1',
      ],
    });
  });
});
