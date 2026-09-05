import { describe, expect, it, vi } from 'vitest';
import {
  buildClarifyModePrompt,
  buildSessionHandoffArtifact,
  handleChatCommand,
  parseClarifyModeTask,
  redactSessionHandoffText,
} from './chatCommands';
import { Message, SessionHandoffArtifactInput } from '../../../types';

const createCommandHarness = () => {
  const messages: Message[] = [];
  let input = '';
  const submitText = vi.fn();
  const saveSessionHandoffArtifact = vi.fn(async (_handoff: SessionHandoffArtifactInput) => undefined);
  const harness = {
    messages,
    submitText,
    saveSessionHandoffArtifact,
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
        saveSessionHandoffArtifact: harness.saveSessionHandoffArtifact,
        messages: harness.messages,
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

  it('builds a redacted session handoff with continuation sections and provenance', () => {
    const handoff = buildSessionHandoffArtifact(
      [
        {
          id: 1,
          role: 'user',
          content: 'Implement the handoff. api_key=super-secret-value',
        },
        {
          id: 2,
          role: 'assistant',
          content: 'Completed command wiring. Decision: save as workspace artifact. Blocker: missing review.',
          citations: [{ url: 'https://example.test/source' }],
        },
      ],
      new Date('2026-09-05T12:00:00.000Z'),
    );

    expect(handoff.title).toBe('Session handoff - 2026-09-05');
    expect(handoff.markdown).toContain('## Objective');
    expect(handoff.markdown).toContain('## Current State');
    expect(handoff.markdown).toContain('## Decisions');
    expect(handoff.markdown).toContain('## Sources');
    expect(handoff.markdown).toContain('## Artifacts');
    expect(handoff.markdown).toContain('## Blockers');
    expect(handoff.markdown).toContain('## Open Questions');
    expect(handoff.markdown).toContain('## Proposed Next Actions');
    expect(handoff.markdown).toContain('## Continuation Prompt');
    expect(handoff.markdown).toContain('api_key=[REDACTED]');
    expect(handoff.markdown).not.toContain('super-secret-value');
    expect(handoff.latest_source_message_id).toBe(2);
    expect(handoff.source_message_ids).toEqual([1, 2]);
    expect(handoff.artifact_metadata.no_external_side_effects).toBe(true);
  });

  it('redacts common credential shapes from handoff text', () => {
    const redacted = redactSessionHandoffText(
      'password=hunter2 token: abcdefghijklmnopqrstuvwxyz Bearer abcdefghijklmnopqrstuvwxyz sk-abcdefghijklmnop',
    );

    expect(redacted).toContain('password=[REDACTED]');
    expect(redacted).toContain('token=[REDACTED]');
    expect(redacted).toContain('Bearer [REDACTED_TOKEN]');
    expect(redacted).toContain('[REDACTED_OPENAI_KEY]');
    expect(redacted).not.toContain('hunter2');
  });

  it('saves slash handoff as a workspace artifact without submitting chat text', () => {
    const harness = createCommandHarness();
    harness.messages.push(
      { id: 1, role: 'user', content: 'Continue ticket 03' },
      { id: 2, role: 'assistant', content: 'Decision: save handoff as artifact.' },
    );

    const handled = harness.runCommand('/handoff');

    expect(handled).toBe(true);
    expect(harness.submitText).not.toHaveBeenCalled();
    expect(harness.saveSessionHandoffArtifact).toHaveBeenCalledTimes(1);
    expect(harness.saveSessionHandoffArtifact.mock.calls[0][0].markdown).toContain('Session Handoff');
    expect(harness.getInput()).toBe('');
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
