import { createSignal, onCleanup, type Accessor } from 'solid-js';
import { useSpeechSynthesis } from '../../../../hooks/useSpeechSynthesis';
import type { Preferences } from '../../types';

type UseVoicePreviewOptions = {
  prefs: Accessor<Preferences>;
};

export const useVoicePreview = ({ prefs }: UseVoicePreviewOptions) => {
  const speech = useSpeechSynthesis();
  const [isPreviewing, setIsPreviewing] = createSignal(false);
  const [previewError, setPreviewError] = createSignal('');
  let previewAudio: HTMLAudioElement | null = null;
  let previewAudioUrl: string | null = null;

  const clearPreviewAudio = () => {
    if (previewAudio) {
      previewAudio.pause();
      previewAudio.onended = null;
      previewAudio.onerror = null;
      previewAudio = null;
    }
    if (previewAudioUrl) {
      URL.revokeObjectURL(previewAudioUrl);
      previewAudioUrl = null;
    }
    setIsPreviewing(false);
  };

  const stopPreview = () => {
    clearPreviewAudio();
    speech.stop();
    setPreviewError('');
  };

  const previewSample = async (form: HTMLFormElement | undefined) => {
    if (!form) return;
    if (isPreviewing()) {
      stopPreview();
      return;
    }
    setPreviewError('');
    const formData = new FormData(form);
    const engine = formData.get('speech_engine') === 'openai' ? 'openai' : 'browser';
    const rate = Number(formData.get('speech_rate') ?? prefs().speech_rate);
    const volume = Number(formData.get('speech_volume') ?? prefs().speech_volume);
    const previewText = '你好，这是一段语音试听。This is a voice preview for mixed Chinese and English.';

    if (engine === 'browser') {
      if (!speech.supported()) {
        setPreviewError('Current browser does not support speech synthesis preview.');
        return;
      }
      const voiceUri = String(formData.get('speech_voice') || '');
      const voice = speech.voices().find(v => v.voiceURI === voiceUri) || null;
      setIsPreviewing(true);
      const ok = speech.speak(previewText, {
        rate: Number.isFinite(rate) ? Math.min(2, Math.max(0.5, rate)) : 1.0,
        volume: Number.isFinite(volume) ? Math.min(1, Math.max(0, volume)) : 1.0,
        voice,
        onEnd: () => setIsPreviewing(false),
        onError: () => {
          setIsPreviewing(false);
          setPreviewError('Browser voice preview failed.');
        },
      });
      if (!ok) {
        setIsPreviewing(false);
        setPreviewError('Browser voice preview failed.');
      }
      return;
    }

    try {
      setIsPreviewing(true);
      const response = await fetch('/api/speech/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: previewText,
          engine: 'openai',
          voice: String(formData.get('speech_openai_voice') || 'alloy'),
          model: String(formData.get('speech_openai_model') || 'gpt-4o-mini-tts'),
          format: 'mp3',
        }),
      });
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || `HTTP ${response.status}`);
      }
      const blob = await response.blob();
      if (!blob.size) throw new Error('empty audio');
      previewAudioUrl = URL.createObjectURL(blob);
      previewAudio = new Audio(previewAudioUrl);
      previewAudio.onended = () => clearPreviewAudio();
      previewAudio.onerror = () => {
        clearPreviewAudio();
        setPreviewError('OpenAI voice preview playback failed.');
      };
      await previewAudio.play();
    } catch (e: any) {
      clearPreviewAudio();
      setPreviewError(`OpenAI voice preview failed: ${e?.message || 'Unknown error'}`);
    }
  };

  onCleanup(() => {
    stopPreview();
  });

  return {
    speech,
    isPreviewing,
    previewError,
    previewSample,
    stopPreview,
  };
};
