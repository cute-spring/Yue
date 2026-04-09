import { describe, expect, it } from 'vitest';
import { getEditShortcutAction, getNormalizedEditedQuestion } from './MessageItem';

describe('MessageItem edit helpers', () => {
  it('normalizes edited question by trimming whitespace', () => {
    expect(getNormalizedEditedQuestion('  hello  ')).toBe('hello');
    expect(getNormalizedEditedQuestion('   ')).toBe('');
  });

  it('maps keyboard events to edit actions', () => {
    expect(getEditShortcutAction({ key: 'Escape', metaKey: false, ctrlKey: false, shiftKey: false })).toBe('cancel');
    expect(getEditShortcutAction({ key: 'Enter', metaKey: true, ctrlKey: false, shiftKey: false })).toBe('submit');
    expect(getEditShortcutAction({ key: 'Enter', metaKey: false, ctrlKey: true, shiftKey: false })).toBe('submit');
    expect(getEditShortcutAction({ key: 'Enter', metaKey: false, ctrlKey: false, shiftKey: false })).toBe('none');
  });
});
