import { describe, expect, it, vi } from 'vitest';
import { buildClarifyModePrompt, handleChatCommand, parseClarifyModeTask } from './chatCommands';
import { Message } from '../../../types';

const createCommandHarness = () => {
  const messages: Message[] = [];
  let input = '';
  const submitText = vi.fn();
  const harness = {
    messages,
    submitText,
    setMessages: (value: Message[] | ((prev: Message[]) => Message[])) => {
      const next = typeof value === 'function' ? value(messages) : value;
      messages.splice(0, messages.length, ...next);
    },
    setInput: (value: string) => {
      input = value;
    },
    getInput: () => input,
  };
  return {
    ...harness,
    runCommand: (trimmedInput: string) =>
      handleChatCommand({
        trimmedInput,
        setMessages: harness.setMessages,
        setInput: harness.setInput,
        submitText: harness.submitText,
        saveLastAssistantAsWorkspaceNote: async () => null,
        saveLastAssistantAsResearchArtifact: async () => undefined,
        toast: {
          error: () => undefined,
          success: () => undefined,
        },
      }),
  };
};

describe('chat commands', () => {
  it('builds a Clarify Mode prompt that asks one decision round and keeps recommendations separate', () => {
    const prompt = buildClarifyModePrompt('Plan the Yue built-in skills rollout');

    expect(prompt).toContain('Clarify Mode');
    expect(prompt).toContain('Plan the Yue built-in skills rollout');
    expect(prompt).toContain('Ask one round');
    expect(prompt).toContain('Recommended answer');
    expect(prompt).toContain('User-approved decision');
    expect(prompt).toContain('## Decision Brief');
    expect(prompt).toContain('Next workbench mode:');
    expect(prompt).toContain('Follow-up handoff text:');
    expect(prompt).toContain('Do not execute');
  });

  it('parses slash and natural-language manual clarify triggers without catching prefixes', () => {
    expect(parseClarifyModeTask('/clarify Plan the rollout')).toBe('Plan the rollout');
    expect(parseClarifyModeTask('/clarify')).toBe('');
    expect(parseClarifyModeTask('clarify this: Plan the rollout')).toBe('Plan the rollout');
    expect(parseClarifyModeTask('help me shape this: Plan the rollout')).toBe('Plan the rollout');
    expect(parseClarifyModeTask('/clarifyfoo')).toBeNull();
    expect(parseClarifyModeTask('Can you clarify the API behavior?')).toBeNull();
  });

  it('submits slash clarify with the transformed prompt', () => {
    const harness = createCommandHarness();

    const handled = harness.runCommand('/clarify Plan the Yue built-in skills rollout');

    expect(handled).toBe(true);
    expect(harness.submitText).toHaveBeenCalledTimes(1);
    expect(harness.submitText.mock.calls[0][0]).toContain('Clarify Mode');
    expect(harness.submitText.mock.calls[0][0]).toContain('Plan the Yue built-in skills rollout');
    expect(harness.getInput()).toBe('');
  });

  it('shows lightweight guidance for slash clarify without a task', () => {
    const harness = createCommandHarness();

    const handled = harness.runCommand('/clarify');

    expect(handled).toBe(true);
    expect(harness.submitText).not.toHaveBeenCalled();
    expect(harness.messages.at(-1)?.content).toContain('/clarify');
    expect(harness.getInput()).toBe('');
  });

  it('does not capture ordinary chat or slash prefixes that are not commands', () => {
    const harness = createCommandHarness();

    const handled = harness.runCommand('/clarifyfoo');

    expect(handled).toBe(false);
    expect(harness.submitText).not.toHaveBeenCalled();
    expect(harness.messages).toHaveLength(0);
  });

  it('submits natural-language manual clarify trigger with the transformed prompt', () => {
    const harness = createCommandHarness();

    const handled = harness.runCommand('clarify this: Plan the Yue built-in skills rollout');

    expect(handled).toBe(true);
    expect(harness.submitText).toHaveBeenCalledTimes(1);
    expect(harness.submitText.mock.calls[0][0]).toContain('## Clarifying Questions');
    expect(harness.submitText.mock.calls[0][0]).toContain('## Decision Brief');
  });
});
