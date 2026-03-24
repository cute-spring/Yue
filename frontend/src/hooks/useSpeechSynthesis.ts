import { Accessor, createSignal, onCleanup } from 'solid-js';

export type SpeechOptions = {
  rate?: number;
  pitch?: number;
  volume?: number;
  voice?: SpeechSynthesisVoice | null;
  lang?: string;
  onStart?: () => void;
  onEnd?: () => void;
  onError?: (event?: SpeechSynthesisErrorEvent | Event) => void;
};

export type SpeechSegmentInput = {
  text: string;
  voice?: SpeechSynthesisVoice | null;
  lang?: string;
};

export type SpeechState = {
  isSpeaking: Accessor<boolean>;
  isPaused: Accessor<boolean>;
  supported: Accessor<boolean>;
  voices: Accessor<SpeechSynthesisVoice[]>;
  currentVoice: Accessor<SpeechSynthesisVoice | null>;
};

export function useSpeechSynthesis() {
  const [isSpeaking, setIsSpeaking] = createSignal(false);
  const [isPaused, setIsPaused] = createSignal(false);
  const [supported, setSupported] = createSignal(false);
  const [voices, setVoices] = createSignal<SpeechSynthesisVoice[]>([]);
  const [currentVoice, setCurrentVoice] = createSignal<SpeechSynthesisVoice | null>(null);
  let activeUtterance: SpeechSynthesisUtterance | null = null;

  const loadVoices = () => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return;
    const nextVoices = window.speechSynthesis.getVoices() || [];
    setVoices(nextVoices);
    if (!currentVoice() && nextVoices.length > 0) {
      const defaultVoice = nextVoices.find(v => v.default) || nextVoices[0];
      setCurrentVoice(defaultVoice);
    }
  };

  if (typeof window !== 'undefined' && window.speechSynthesis) {
    setSupported(true);
    loadVoices();
    const handleVoicesChanged = () => loadVoices();
    window.speechSynthesis.addEventListener('voiceschanged', handleVoicesChanged);
    onCleanup(() => {
      window.speechSynthesis.removeEventListener('voiceschanged', handleVoicesChanged);
    });
  } else {
    setSupported(false);
  }

  const stop = () => {
    if (!supported() || typeof window === 'undefined') return;
    window.speechSynthesis.cancel();
    activeUtterance = null;
    setIsSpeaking(false);
    setIsPaused(false);
  };

  const pause = () => {
    if (!supported() || typeof window === 'undefined') return;
    window.speechSynthesis.pause();
    setIsPaused(true);
  };

  const resume = () => {
    if (!supported() || typeof window === 'undefined') return;
    window.speechSynthesis.resume();
    setIsPaused(false);
  };

  const setVoice = (voice: SpeechSynthesisVoice | null) => {
    setCurrentVoice(voice);
  };

  const speak = (text: string, options: SpeechOptions = {}): boolean => {
    if (!supported() || typeof window === 'undefined') return false;
    const normalized = text.trim();
    if (!normalized) return false;

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(normalized);
    activeUtterance = utterance;

    const resolvedVoice = options.voice ?? currentVoice();
    if (resolvedVoice) {
      utterance.voice = resolvedVoice;
      utterance.lang = options.lang || resolvedVoice.lang;
    } else if (options.lang) {
      utterance.lang = options.lang;
    }
    utterance.rate = options.rate ?? 1;
    utterance.pitch = options.pitch ?? 1;
    utterance.volume = options.volume ?? 1;

    utterance.onstart = () => {
      setIsSpeaking(true);
      setIsPaused(false);
      options.onStart?.();
    };
    utterance.onend = () => {
      if (activeUtterance === utterance) {
        activeUtterance = null;
      }
      setIsSpeaking(false);
      setIsPaused(false);
      options.onEnd?.();
    };
    utterance.onerror = (event) => {
      if (activeUtterance === utterance) {
        activeUtterance = null;
      }
      setIsSpeaking(false);
      setIsPaused(false);
      options.onError?.(event);
    };

    window.speechSynthesis.speak(utterance);
    return true;
  };

  const speakSegments = (segments: SpeechSegmentInput[], options: SpeechOptions = {}): boolean => {
    if (!supported() || typeof window === 'undefined') return false;
    const queue = segments.filter(s => s.text.trim().length > 0);
    if (queue.length === 0) return false;

    window.speechSynthesis.cancel();
    let cancelled = false;
    setIsSpeaking(false);
    setIsPaused(false);

    const speakAt = (index: number) => {
      if (cancelled || index >= queue.length) {
        setIsSpeaking(false);
        setIsPaused(false);
        options.onEnd?.();
        return;
      }
      const seg = queue[index];
      const utterance = new SpeechSynthesisUtterance(seg.text);
      activeUtterance = utterance;
      const resolvedVoice = seg.voice ?? options.voice ?? currentVoice();
      if (resolvedVoice) {
        utterance.voice = resolvedVoice;
      }
      utterance.lang = seg.lang || resolvedVoice?.lang || options.lang || '';
      utterance.rate = options.rate ?? 1;
      utterance.pitch = options.pitch ?? 1;
      utterance.volume = options.volume ?? 1;
      utterance.onstart = () => {
        setIsSpeaking(true);
        setIsPaused(false);
        if (index === 0) {
          options.onStart?.();
        }
      };
      utterance.onerror = (event) => {
        cancelled = true;
        setIsSpeaking(false);
        setIsPaused(false);
        options.onError?.(event);
      };
      utterance.onend = () => {
        if (cancelled) return;
        speakAt(index + 1);
      };
      window.speechSynthesis.speak(utterance);
    };

    speakAt(0);
    return true;
  };

  return {
    isSpeaking,
    isPaused,
    supported,
    voices,
    currentVoice,
    speak,
    speakSegments,
    pause,
    resume,
    stop,
    setVoice,
  };
}
