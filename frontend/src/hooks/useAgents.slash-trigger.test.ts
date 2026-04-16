import { describe, expect, it } from 'vitest';
import { Agent } from '../types';
import {
  deriveSlashAgentSelectorState,
  filterAgentsByQuery,
  getAgentSelectorKeyAction,
  rewriteInputAfterSlashAgentSelection,
} from './useAgents';

const AGENTS: Agent[] = [
  {
    id: 'a1',
    name: 'Developer',
    system_prompt: '',
    provider: 'openai',
    model: 'gpt-4o-mini',
    enabled_tools: [],
  },
  {
    id: 'a2',
    name: 'Design Assistant',
    system_prompt: '',
    provider: 'openai',
    model: 'gpt-4o-mini',
    enabled_tools: [],
  },
  {
    id: 'a3',
    name: 'Doc Writer',
    system_prompt: '',
    provider: 'openai',
    model: 'gpt-4o-mini',
    enabled_tools: [],
  },
];

describe('deriveSlashAgentSelectorState', () => {
  it('shows selector when only slash is typed at beginning', () => {
    expect(deriveSlashAgentSelectorState('/', 1)).toEqual({
      show: true,
      filter: '',
    });
  });

  it('narrows filter as user keeps typing after slash', () => {
    expect(deriveSlashAgentSelectorState('/dev', 4)).toEqual({
      show: true,
      filter: 'dev',
    });
  });

  it('does not trigger when slash is not at beginning', () => {
    expect(deriveSlashAgentSelectorState('hello /dev', 10)).toEqual({
      show: false,
      filter: '',
    });
  });

  it('hides selector when whitespace appears in the prefix segment', () => {
    expect(deriveSlashAgentSelectorState('/dev notes', 10)).toEqual({
      show: false,
      filter: '',
    });
  });
});

describe('filterAgentsByQuery', () => {
  it('filters agents by case-insensitive name match', () => {
    const matched = filterAgentsByQuery(AGENTS, 'de');
    expect(matched.map((agent) => agent.name)).toEqual(['Developer', 'Design Assistant']);
  });
});

describe('rewriteInputAfterSlashAgentSelection', () => {
  it('removes slash token when selecting an agent', () => {
    expect(rewriteInputAfterSlashAgentSelection('/dev', 4)).toBe('');
  });

  it('preserves trailing prompt text after removing slash token', () => {
    expect(rewriteInputAfterSlashAgentSelection('/dev build me a plan', 4)).toBe('build me a plan');
  });

  it('is a no-op when input is not slash-token form', () => {
    expect(rewriteInputAfterSlashAgentSelection('hello /dev', 10)).toBe('hello /dev');
  });
});

describe('getAgentSelectorKeyAction', () => {
  it('submits on Enter when selector is visible but there are no matches', () => {
    expect(getAgentSelectorKeyAction(true, 0, 'Enter', false)).toBe('submit');
  });

  it('ignores arrow navigation when there are no matches', () => {
    expect(getAgentSelectorKeyAction(true, 0, 'ArrowDown', false)).toBe('none');
  });

  it('selects highlighted agent on Enter when matches exist', () => {
    expect(getAgentSelectorKeyAction(true, 2, 'Enter', false)).toBe('select');
  });

  it('closes on Escape even with no matches', () => {
    expect(getAgentSelectorKeyAction(true, 0, 'Escape', false)).toBe('close');
  });
});
