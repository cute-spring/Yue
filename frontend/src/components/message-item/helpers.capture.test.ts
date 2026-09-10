import { describe, expect, it } from 'vitest';

import {
  getHighSignalUserMemorySuggestion,
  getSessionMemoryDismissalKey,
  getWorkspaceCaptureSuggestion,
} from './helpers';


describe('workspace capture suggestions', () => {
  it('suggests saving a substantial grounded assistant reply', () => {
    expect(
      getWorkspaceCaptureSuggestion(
        {
          role: 'assistant',
          content: '总结：默认使用中文回复，并在输出里保留结构化结论。这个约定会影响后续所有工作区回答。',
          citations: [{ source_id: 'src_1' }],
          workspace_notes: { loaded_note_count: 0 },
          workspace_memory: { loaded_memory_count: 0 },
        },
        {
          hasSelectedWorkspace: true,
          isLatestAssistantMessage: true,
          isTyping: false,
          alreadySavedAsNote: false,
          hasPendingMemoryCandidate: false,
        },
      ),
    ).toEqual({
      show_note_action: true,
      show_memory_action: true,
      reason: 'This reply looks like a reusable preference, rule, or decision worth keeping.',
    });
  });

  it('suppresses note action after the reply was already captured', () => {
    const suggestion = getWorkspaceCaptureSuggestion(
      {
        role: 'assistant',
        content: '决定：今后统一采用 workspace note + memory candidate 的双层机制，并保留来源回链。',
        citations: [],
        workspace_notes: { loaded_note_count: 1 },
        workspace_memory: { loaded_memory_count: 0 },
      },
      {
        hasSelectedWorkspace: true,
        isLatestAssistantMessage: true,
        isTyping: false,
        alreadySavedAsNote: true,
        hasPendingMemoryCandidate: false,
      },
    );

    expect(suggestion?.show_note_action).toBe(false);
    expect(suggestion?.show_memory_action).toBe(true);
  });

  it('returns null for short or non-workspace replies', () => {
    expect(
      getWorkspaceCaptureSuggestion(
        {
          role: 'assistant',
          content: '好的。',
          citations: [],
          workspace_notes: { loaded_note_count: 0 },
          workspace_memory: { loaded_memory_count: 0 },
        },
        {
          hasSelectedWorkspace: true,
          isLatestAssistantMessage: true,
          isTyping: false,
          alreadySavedAsNote: false,
          hasPendingMemoryCandidate: false,
        },
      ),
    ).toBeNull();

    expect(
      getWorkspaceCaptureSuggestion(
        {
          role: 'assistant',
          content: '这是一个足够长的总结，但当前并不在任何工作区里，因此不应该弹出 capture 建议。',
          citations: [],
          workspace_notes: { loaded_note_count: 0 },
          workspace_memory: { loaded_memory_count: 0 },
        },
        {
          hasSelectedWorkspace: false,
          isLatestAssistantMessage: true,
          isTyping: false,
          alreadySavedAsNote: false,
          hasPendingMemoryCandidate: false,
        },
      ),
    ).toBeNull();
  });

  it('preserves backend suggestion shape for downstream UI use', () => {
    const suggestion = {
      workspace_id: 'ws_1',
      show_note_action: true,
      show_memory_action: false,
      reason: 'This substantial answer may be worth capturing for future workspace recall.',
      source: 'backend',
    };

    expect(suggestion.source).toBe('backend');
    expect(suggestion.show_note_action).toBe(true);
    expect(suggestion.show_memory_action).toBe(false);
  });
});

describe('high-signal user memory suggestions', () => {
  it('detects explicit Chinese preference and default statements', () => {
    expect(getHighSignalUserMemorySuggestion('以后默认用中文回答。')).toEqual({
      show_note_action: false,
      show_memory_action: true,
      reason: 'This user preference looks worth reviewing for memory.',
      source: 'high_signal_user_message',
      suggested_scope_type: 'user',
      suggested_destination: 'About You',
      trigger: '以后',
    });

    expect(getHighSignalUserMemorySuggestion('我不喜欢太营销化的页面。')?.suggested_destination).toBe('About You');
  });

  it('detects explicit English durable instructions', () => {
    expect(getHighSignalUserMemorySuggestion('remember that I prefer concise answers')?.trigger).toBe('remember');
    expect(getHighSignalUserMemorySuggestion("don't use adaptive workspace categories")?.suggested_destination).toBe(
      'This Workspace',
    );
    expect(getHighSignalUserMemorySuggestion('always use bullet points for summaries')?.suggested_scope_type).toBe(
      'user',
    );
  });

  it('detects correction language as high-signal memory review input', () => {
    const suggestion = getHighSignalUserMemorySuggestion('Actually, default to English responses now.');

    expect(suggestion).toMatchObject({
      show_memory_action: true,
      reason: 'This correction looks worth reviewing against existing memory.',
      source: 'high_signal_user_message',
      suggested_scope_type: 'user',
      trigger: 'actually',
    });
  });

  it('detects update-style correction language as memory review input', () => {
    const suggestion = getHighSignalUserMemorySuggestion('Update my default language preference to English.');

    expect(suggestion).toMatchObject({
      show_memory_action: true,
      reason: 'This correction looks worth reviewing against existing memory.',
      suggested_scope_type: 'user',
      trigger: 'update',
    });
  });

  it('does not prompt for ordinary chat', () => {
    expect(getHighSignalUserMemorySuggestion('这个怎么做？')).toBeNull();
    expect(getHighSignalUserMemorySuggestion('Thanks, sounds good.')).toBeNull();
    expect(getHighSignalUserMemorySuggestion('Can you explain this code?')).toBeNull();
  });

  it('builds a stable session dismissal key for noisy repeated prompts', () => {
    expect(
      getSessionMemoryDismissalKey({
        workspaceId: 'ws_1',
        chatId: 'chat_1',
        messageId: 3,
        content: '以后默认用中文回答。',
      }),
    ).toBe('ws_1:chat_1:以后默认用中文回答。');

    expect(
      getSessionMemoryDismissalKey({
        workspaceId: 'ws_1',
        chatId: 'chat_1',
        messageId: 4,
        content: '以后默认用中文回答。',
      }),
    ).toBe('ws_1:chat_1:以后默认用中文回答。');
  });
});
