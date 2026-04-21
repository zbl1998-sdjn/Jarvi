import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import path from 'node:path';

import { describe, expect, it } from 'vitest';

const projectRoot = path.resolve(import.meta.dirname, '..', '..');
const devElectronScript = path.join(projectRoot, 'scripts', 'dev-electron.ps1');
const DEV_ELECTRON_TIMEOUT_MS = 10_000;

describe('desktop dev startup path', () => {
  it('routes npm dev:electron through the helper script', () => {
    const packageJson = JSON.parse(
      readFileSync(path.join(projectRoot, 'package.json'), 'utf8'),
    ) as { scripts: Record<string, string> };

    expect(packageJson.scripts['dev:electron']).toContain('dev-electron.ps1');
    expect(packageJson.scripts['dev:electron']).not.toContain('tcp:8001');
  });

  it('builds the local renderer bundle without depending on a ui dev server', () => {
    const packageJson = JSON.parse(
      readFileSync(path.join(projectRoot, 'package.json'), 'utf8'),
    ) as { scripts: Record<string, string>; workspaces?: string[] };

    expect(packageJson.scripts['build:ui']).toContain('jarvis-ui');
    expect(packageJson.scripts['dev:desktop']).toContain('npm run build:ui');
    expect(packageJson.scripts['dev:desktop']).not.toContain('npm:dev:ui');
    expect(packageJson.workspaces).toBeUndefined();
    expect(packageJson.scripts['dev:ui']).toBeUndefined();
    expect(packageJson.scripts['test:ui']).toBeUndefined();
  });

  it('uses the configured server host and port without waiting on a ui dev server', () => {
    const output = execFileSync(
      'powershell',
      ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', devElectronScript],
      {
        cwd: projectRoot,
        encoding: 'utf8',
        timeout: DEV_ELECTRON_TIMEOUT_MS,
        env: {
          ...process.env,
          JARVIS_SERVER_DRY_RUN: '1',
          JARVIS_SERVER_HOST: '0.0.0.0',
          JARVIS_SERVER_PORT: '9123',
          VITE_DEV_SERVER_URL: 'http://127.0.0.1:5173',
        },
      },
    );

    expect(output).toContain('WAIT_ON=tcp:0.0.0.0:9123 file:dist-electron/main.js');
    expect(output).not.toContain('tcp:5173');
    expect(output).not.toContain('VITE_DEV_SERVER_URL=');
  });
});
