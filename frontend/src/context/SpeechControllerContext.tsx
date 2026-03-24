import { Accessor, JSX, createContext, createEffect, createSignal, onCleanup, useContext } from 'solid-js';
import { useToast } from './ToastContext';
import { useSpeechSynthesis } from '../hooks/useSpeechSynthesis';
import { splitSpeechSegments } from '../utils/speech';
import { Preferences } from '../pages/settings/types';

type SpeechButtonState = 'idle' | 'speaking' | 'paused';

type SpeechControllerValue = {
  supported: Accessor<boolean>;
  currentMessageId: Accessor<string | null>;
  isSpeaking: Accessor<boolean>;
  isPaused: Accessor<boolean>;
  voices: Accessor<SpeechSynthesisVoice[]>;
  speakMessage: (messageId: string, rawText: string) => boolean;
  toggleMessage: (messageId: string, rawText: string) => boolean;
  stopCurrent: () => void;
  pause: () => void;
  resume: () => void;
  getMessageState: (messageId: string) => SpeechButtonState;
};

const SpeechControllerContext = createContext<SpeechControllerValue>();

type SpeechControllerProviderProps = {
  prefs: Accessor<Preferences>;
  children: JSX.Element;
};

export function SpeechControllerProvider(props: SpeechControllerProviderProps) {
  const toast = useToast();
  const speech = useSpeechSynthesis();
  const [currentMessageId, setCurrentMessageId] = createSignal<string | null>(null);
  const [remoteSpeaking, setRemoteSpeaking] = createSignal(false);
  const [remotePaused, setRemotePaused] = createSignal(false);
  let remoteAudio: HTMLAudioElement | null = null;
  let remoteAudioUrl: string | null = null;

  const engine = () => props.prefs().speech_engine;
  const isOpenAIEngine = () => engine() === 'openai';
  const supported = () => (isOpenAIEngine() ? true : speech.supported());
  const isSpeaking = () => (isOpenAIEngine() ? remoteSpeaking() : speech.isSpeaking());
  const isPaused = () => (isOpenAIEngine() ? remotePaused() : speech.isPaused());

  const resolveVoice = (): SpeechSynthesisVoice | null => {
    const preferredVoiceUri = props.prefs().speech_voice || '';
    const allVoices = speech.voices();
    if (!preferredVoiceUri) return speech.currentVoice();
    return allVoices.find(v => v.voiceURI === preferredVoiceUri) || speech.currentVoice();
  };

  const isLangFamily = (voice: SpeechSynthesisVoice | null | undefined, family: 'zh' | 'en') => {
    if (!voice?.lang) return false;
    return voice.lang.toLowerCase().startsWith(`${family.toLowerCase()}-`) || voice.lang.toLowerCase() === family.toLowerCase();
  };

  const pickVoiceForLang = (langHint: 'zh' | 'en') => {
    const preferred = resolveVoice();
    const voices = speech.voices();
    if (isLangFamily(preferred, langHint)) return preferred;
    const matched = voices.find(v => isLangFamily(v, langHint));
    return matched || preferred;
  };

  const clearRemoteAudio = () => {
    if (remoteAudio) {
      remoteAudio.pause();
      remoteAudio.onended = null;
      remoteAudio.onerror = null;
      remoteAudio = null;
    }
    if (remoteAudioUrl) {
      URL.revokeObjectURL(remoteAudioUrl);
      remoteAudioUrl = null;
    }
    setRemoteSpeaking(false);
    setRemotePaused(false);
  };

  const stopCurrent = () => {
    clearRemoteAudio();
    speech.stop();
    setCurrentMessageId(null);
  };

  const speakWithOpenAI = async (messageId: string, rawText: string): Promise<boolean> => {
    const segments = splitSpeechSegments(rawText, 1200);
    const text = segments.map(s => s.text).join(' ').trim();
    if (!text) return false;

    stopCurrent();
    setCurrentMessageId(messageId);
    try {
      const response = await fetch('/api/speech/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          engine: 'openai',
          model: props.prefs().speech_openai_model,
          voice: props.prefs().speech_openai_voice,
          format: 'mp3',
        }),
      });
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || `HTTP ${response.status}`);
      }
      const blob = await response.blob();
      if (!blob.size) {
        throw new Error('empty_audio');
      }
      remoteAudioUrl = URL.createObjectURL(blob);
      remoteAudio = new Audio(remoteAudioUrl);
      remoteAudio.onended = () => {
        if (remoteAudioUrl) {
          URL.revokeObjectURL(remoteAudioUrl);
          remoteAudioUrl = null;
        }
        setRemoteSpeaking(false);
        setRemotePaused(false);
        setCurrentMessageId(null);
      };
      remoteAudio.onerror = () => {
        setRemoteSpeaking(false);
        setRemotePaused(false);
        setCurrentMessageId(null);
        toast.error('云端语音播放失败，请稍后重试。');
      };
      setRemoteSpeaking(true);
      setRemotePaused(false);
      await remoteAudio.play();
      return true;
    } catch (e: any) {
      setRemoteSpeaking(false);
      setRemotePaused(false);
      setCurrentMessageId(null);
      toast.error(`云端语音合成失败: ${e?.message || 'Unknown error'}`);
      return false;
    }
  };

  const speakMessage = (messageId: string, rawText: string): boolean => {
    if (!supported()) return false;
    if (isOpenAIEngine()) {
      void speakWithOpenAI(messageId, rawText);
      return true;
    }
    const segments = splitSpeechSegments(rawText, 1200);
    if (segments.length === 0) return false;

    stopCurrent();
    setCurrentMessageId(messageId);
    const fixedVoice = resolveVoice();
    const canUseFixedVoice = !!fixedVoice;
    const ok = speech.speakSegments(
      segments.map(seg => {
        if (canUseFixedVoice) {
          // Honor the voice chosen in settings to avoid mismatch between UI selection and playback voice.
          return {
            text: seg.text,
            voice: fixedVoice,
            lang: fixedVoice?.lang || (seg.langHint === 'zh' ? 'zh-CN' : 'en-US'),
          };
        }
        return {
          text: seg.text,
          voice: pickVoiceForLang(seg.langHint),
          lang: seg.langHint === 'zh' ? 'zh-CN' : 'en-US',
        };
      }),
      {
      rate: props.prefs().speech_rate,
      volume: props.prefs().speech_volume,
      onEnd: () => setCurrentMessageId(null),
      onError: () => {
        setCurrentMessageId(null);
        toast.error('语音朗读失败，请稍后重试。');
      },
      },
    );
    if (!ok) {
      setCurrentMessageId(null);
    }
    return ok;
  };

  const toggleMessage = (messageId: string, rawText: string): boolean => {
    const state = getMessageState(messageId);
    if (state === 'speaking' || state === 'paused') {
      stopCurrent();
      return true;
    }
    return speakMessage(messageId, rawText);
  };

  const getMessageState = (messageId: string): SpeechButtonState => {
    if (currentMessageId() !== messageId) return 'idle';
    if (isPaused()) return 'paused';
    if (isSpeaking()) return 'speaking';
    return 'idle';
  };

  const pause = () => {
    if (isOpenAIEngine()) {
      if (remoteAudio && !remoteAudio.paused) {
        remoteAudio.pause();
        setRemotePaused(true);
        setRemoteSpeaking(false);
      }
      return;
    }
    speech.pause();
  };

  const resume = () => {
    if (isOpenAIEngine()) {
      if (remoteAudio && remoteAudio.paused) {
        void remoteAudio.play();
        setRemotePaused(false);
        setRemoteSpeaking(true);
      }
      return;
    }
    speech.resume();
  };

  createEffect(() => {
    engine();
    stopCurrent();
  });

  onCleanup(() => {
    stopCurrent();
  });

  return (
    <SpeechControllerContext.Provider
      value={{
        supported,
        currentMessageId,
        isSpeaking,
        isPaused,
        voices: speech.voices,
        speakMessage,
        toggleMessage,
        stopCurrent,
        pause,
        resume,
        getMessageState,
      }}
    >
      {props.children}
    </SpeechControllerContext.Provider>
  );
}

export function useSpeechController() {
  const ctx = useContext(SpeechControllerContext);
  if (!ctx) {
    throw new Error('useSpeechController must be used within SpeechControllerProvider');
  }
  return ctx;
}

export function useMaybeSpeechController() {
  return useContext(SpeechControllerContext);
}
