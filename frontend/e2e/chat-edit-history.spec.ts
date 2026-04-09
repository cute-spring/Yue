import { test } from '@playwright/test';

test.skip('edit old question truncates subsequent history and resubmits', async () => {
  // This scenario depends on deterministic chat-stream responses.
  // Enable once e2e fixtures/mocks are available for:
  // 1) send Q1 -> A1 and Q2 -> A2
  // 2) edit Q1 and submit
  // 3) verify old Q2/A2 removed and replaced by new branch
});
