import { createRoot } from 'solid-js';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSpeechSynthesis } from './useSpeechSynthesis';

type UtteranceLike = {
  text: string;
  voice?: SpeechSynthesisVoice;
  lang?: string;
  rate?: number;
  pitch?: number;
  volume?: number;
  onstart?: () => void;
  onend?: () => void;
  onerror?: () => void;
};

describe('useSpeechSynthesis', () => {
  const voices = [
    { name: 'A', lang: 'en-US', default: true, voiceURI: 'voice-a' },
    { name: 'B', lang: 'zh-CN', default: false, voiceURI: 'voice-b' },
  ] as SpeechSynthesisVoice[];

  beforeEach(() => {
    const listeners = new Map<string, Set<() => void>>();
    const speechSynthesis = {
      speak: vi.fn((u: UtteranceLike) => u.onstart?.()),
      cancel: vi.fn(),
      pause: vi.fn(),
      resume: vi.fn(),
      getVoices: vi.fn(() => voices),
      addEventListener: vi.fn((event: string, cb: () => void) => {
        const bucket = listeners.get(event) || new Set();
        bucket.add(cb);
        listeners.set(event, bucket);
      }),
      removeEventListener: vi.fn((event: string, cb: () => void) => {
        listeners.get(event)?.delete(cb);
      }),
    };

    (globalThis as any).window = { speechSynthesis };
    (globalThis as any).SpeechSynthesisUtterance = class {
      text: string;
      voice?: SpeechSynthesisVoice;
      lang?: string;
      rate?: number;
      pitch?: number;
      volume?: number;
      onstart?: () => void;
      onend?: () => void;
      onerror?: () => void;
      constructor(text: string) {
        this.text = text;
      }
    };
  });

  it('detects support and loads voices', () => {
    createRoot(dispose => {
      const speech = useSpeechSynthesis();
      expect(speech.supported()).toBe(true);
      expect(speech.voices()).toHaveLength(2);
      dispose();
    });
  });

  it('updates speaking state through speak and stop', () => {
    createRoot(dispose => {
      const speech = useSpeechSynthesis();
      expect(speech.speak('hello')).toBe(true);
      expect(speech.isSpeaking()).toBe(true);
      speech.stop();
      expect(speech.isSpeaking()).toBe(false);
      dispose();
    });
  });
});
