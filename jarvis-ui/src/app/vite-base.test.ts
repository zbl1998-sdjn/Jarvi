// @vitest-environment node

import config from '../../vite.config';

it('uses relative asset paths for the Electron file renderer', () => {
  expect(config.base).toBe('./');
});
