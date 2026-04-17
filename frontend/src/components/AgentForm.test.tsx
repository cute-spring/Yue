import { describe, expect, test } from 'vitest';

import { AgentForm, resolveAgentModelUiState } from './AgentForm';


describe('AgentForm', () => {
  test('exports component function', () => {
    expect(typeof AgentForm).toBe('function');
  });

  test('defaults to tier controls when advanced direct picker is collapsed', () => {
    expect(resolveAgentModelUiState('tier', false)).toEqual({
      showTierCards: true,
      showDirectPicker: false,
    });
  });

  test('shows direct picker when switched to direct mode', () => {
    expect(resolveAgentModelUiState('direct', false)).toEqual({
      showTierCards: false,
      showDirectPicker: true,
    });
  });
});
