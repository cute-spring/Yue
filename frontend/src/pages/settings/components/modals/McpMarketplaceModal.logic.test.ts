import { describe, expect, it } from 'vitest';
import { resolveMcpMarketplaceOnboardingState } from './McpMarketplaceModal';

describe('resolveMcpMarketplaceOnboardingState', () => {
  it('shows onboarding notes for jira-company', () => {
    const state = resolveMcpMarketplaceOnboardingState('jira-company');

    expect(state.showNotes).toBe(true);
    expect(state.notes).toEqual([
      'Default to base URL plus personal token; username/email should stay optional unless your company MCP requires it.',
      'Keep the server disabled until the real internal Jira MCP package or executable is confirmed.',
      'Start with read-only scope hints such as allowed projects, default JQL, or explicit read-only flags.',
    ]);
  });

  it('hides onboarding notes for templates without custom guidance', () => {
    const state = resolveMcpMarketplaceOnboardingState('custom-company-mcp');

    expect(state.showNotes).toBe(false);
    expect(state.notes).toEqual([]);
  });
});
