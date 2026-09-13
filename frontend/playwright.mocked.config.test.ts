import { describe, expect, it } from 'vitest';
import config from './playwright.mocked.config';

describe('mocked Playwright configuration', () => {
  it('starts isolated frontend and backend services', () => {
    expect(config.webServer).toHaveLength(2);
    expect(config.webServer).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ reuseExistingServer: false }),
        expect.objectContaining({
          reuseExistingServer: false,
          command: expect.stringContaining('YUE_DATA_DIR='),
        }),
      ]),
    );
  });
});
