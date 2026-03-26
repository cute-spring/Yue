import { Accessor, createSignal, onCleanup } from 'solid-js';

type BrowserSpeechRecognitionEvent = Event & {
  results?: ArrayLike<{
    isFinal: boolean;
    0?: { transcript?: string };
  }>;
};

type BrowserSpeechRecognitionErrorEvent = Event & {
  error?: string;
};

type BrowserSpeechRecognition = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onstart: ((event: Event) => void) | null;
  onresult: ((event: BrowserSpeechRecognitionEvent) => void) | null;
  onerror: ((event: BrowserSpeechRecognitionErrorEvent) => void) | null;
  onend: ((event: Event) => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
};

type BrowserSpeechRecognitionConstructor = new () => BrowserSpeechRecognition;

type AzureSpeechRecognitionResultEvent = {
  result?: {
    text?: string;
    reason?: number;
  };
};

type AzureSpeechRecognitionCanceledEvent = {
  errorDetails?: string;
  reason?: number;
};

type AzureSpeechConfig = {
  speechRecognitionLanguage?: string;
  endpointId?: string;
};

type AzureAudioConfig = Record<string, unknown>;

type AzureSpeechRecognizer = {
  recognizing?: ((sender: unknown, event: AzureSpeechRecognitionResultEvent) => void) | null;
  recognized?: ((sender: unknown, event: AzureSpeechRecognitionResultEvent) => void) | null;
  canceled?: ((sender: unknown, event: AzureSpeechRecognitionCanceledEvent) => void) | null;
  sessionStopped?: ((sender: unknown, event: Event) => void) | null;
  startContinuousRecognitionAsync: (cb?: () => void, err?: (error: string) => void) => void;
  stopContinuousRecognitionAsync: (cb?: () => void, err?: (error: string) => void) => void;
  close?: () => void;
};

type AzureSpeechSDKNamespace = {
  SpeechConfig: {
    fromAuthorizationToken: (token: string, region: string) => AzureSpeechConfig;
  };
  AudioConfig: {
    fromDefaultMicrophoneInput: () => AzureAudioConfig;
  };
  SpeechRecognizer: new (speechConfig: AzureSpeechConfig, audioConfig: AzureAudioConfig) => AzureSpeechRecognizer;
};

declare global {
  interface Window {
    SpeechRecognition?: BrowserSpeechRecognitionConstructor;
    webkitSpeechRecognition?: BrowserSpeechRecognitionConstructor;
    SpeechSDK?: AzureSpeechSDKNamespace;
  }
}

export type VoiceInputRuntimeConfig = {
  language: string;
  appLanguage?: string;
  provider: 'browser' | 'azure';
  agentId?: string | null;
};

export type VoiceInputPhase = 'idle' | 'recording' | 'finalizing' | 'ready' | 'error';

export type VoiceInputState = {
  supported: Accessor<boolean>;
  provider: Accessor<'browser' | 'azure'>;
  preferredProvider: Accessor<'browser' | 'azure'>;
  phase: Accessor<VoiceInputPhase>;
  isRecording: Accessor<boolean>;
  isProcessing: Accessor<boolean>;
  hasDraft: Accessor<boolean>;
  transcript: Accessor<string>;
  interimTranscript: Accessor<string>;
  previewText: Accessor<string>;
  baseText: Accessor<string>;
  error: Accessor<string | null>;
  fallbackMessage: Accessor<string | null>;
  startRecording: (baseText?: string) => Promise<boolean>;
  stopRecording: () => void;
  cancelRecording: () => void;
  toggleRecording: (baseText?: string) => Promise<boolean>;
  clearError: () => void;
  clearDraft: () => void;
  consumeDraft: () => string;
};

const normalizeWhitespace = (value: string): string => value.replace(/\s+/g, ' ').trim();

const appendWithSpacing = (base: string, addition: string): string => {
  const left = base.trimEnd();
  const right = addition.trim();
  if (!right) return left;
  if (!left) return right;
  return /\s$/.test(base) ? `${base}${right}` : `${left} ${right}`;
};

export const composeVoiceInputText = (
  baseText: string,
  transcript: string,
  interimTranscript: string,
  showInterim: boolean,
): string => {
  const stable = appendWithSpacing(baseText, normalizeWhitespace(transcript));
  if (!showInterim) return stable;
  return appendWithSpacing(stable, normalizeWhitespace(interimTranscript));
};

export const getCommittedVoiceInputText = (transcript: string, interimTranscript: string): string => {
  const stable = normalizeWhitespace(transcript);
  if (stable) return stable;
  return normalizeWhitespace(interimTranscript);
};

const getRecognitionConstructor = (): BrowserSpeechRecognitionConstructor | null => {
  if (typeof window === 'undefined') return null;
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
};

export const resolveVoiceInputLanguage = (preferred: string, appLanguage?: string) => {
  if (preferred && preferred !== 'auto') return preferred;
  if (appLanguage === 'zh') return 'zh-CN';
  if (appLanguage === 'en') return 'en-US';
  if (typeof navigator !== 'undefined' && navigator.language) return navigator.language;
  return 'en-US';
};

const mapBrowserRecognitionError = (error?: string) => {
  switch (error) {
    case 'not-allowed':
    case 'service-not-allowed':
      return 'Microphone permission was denied.';
    case 'audio-capture':
      return 'No microphone was found for voice input.';
    case 'network':
      return 'Browser speech recognition hit a network error.';
    case 'no-speech':
      return 'No speech was detected. Please try again.';
    case 'aborted':
      return null;
    default:
      return error ? `Voice input failed: ${error}.` : 'Voice input failed.';
  }
};

const AZURE_SDK_URL =
  'https://cdn.jsdelivr.net/npm/microsoft-cognitiveservices-speech-sdk@1.39.0/distrib/browser/microsoft.cognitiveservices.speech.sdk.bundle-min.js';
const AUTO_STOP_AFTER_SPEECH_MS = 1800;

let azureSpeechSdkPromise: Promise<AzureSpeechSDKNamespace> | null = null;

const loadAzureSpeechSdk = async (): Promise<AzureSpeechSDKNamespace> => {
  if (typeof window === 'undefined') {
    throw new Error('Azure speech SDK requires a browser environment.');
  }
  if (window.SpeechSDK) return window.SpeechSDK;
  if (azureSpeechSdkPromise) return azureSpeechSdkPromise;

  azureSpeechSdkPromise = new Promise<AzureSpeechSDKNamespace>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${AZURE_SDK_URL}"]`);
    const onReady = () => {
      if (window.SpeechSDK) {
        resolve(window.SpeechSDK);
        return true;
      }
      return false;
    };
    if (existing) {
      if (!onReady()) {
        existing.addEventListener('load', () => onReady());
        existing.addEventListener('error', () => reject(new Error('Failed to load Azure Speech SDK.')));
      }
      return;
    }

    const script = document.createElement('script');
    script.src = AZURE_SDK_URL;
    script.async = true;
    script.onload = () => {
      if (!onReady()) reject(new Error('Azure Speech SDK did not initialize.'));
    };
    script.onerror = () => reject(new Error('Failed to load Azure Speech SDK.'));
    document.head.appendChild(script);
  });

  try {
    return await azureSpeechSdkPromise;
  } finally {
    azureSpeechSdkPromise = null;
  }
};

const getAzureSupported = (config: VoiceInputRuntimeConfig) =>
  !!config.agentId && typeof window !== 'undefined' && !!navigator.mediaDevices?.getUserMedia;

export function useVoiceInput(config: Accessor<VoiceInputRuntimeConfig>): VoiceInputState {
  const [phase, setPhase] = createSignal<VoiceInputPhase>('idle');
  const [transcript, setTranscript] = createSignal('');
  const [interimTranscript, setInterimTranscript] = createSignal('');
  const [error, setError] = createSignal<string | null>(null);
  const [fallbackMessage, setFallbackMessage] = createSignal<string | null>(null);
  const [activeProvider, setActiveProvider] = createSignal<'browser' | 'azure'>('browser');
  const [baseText, setBaseText] = createSignal('');
  let browserRecognition: BrowserSpeechRecognition | null = null;
  let azureRecognizer: AzureSpeechRecognizer | null = null;
  let autoStopTimer: ReturnType<typeof setTimeout> | null = null;
  let activeSessionId = 0;

  const preferredProvider = () => (config().provider === 'azure' ? 'azure' : 'browser');
  const browserSupported = () => !!getRecognitionConstructor();
  const azureSupported = () => getAzureSupported(config());
  const provider = () => activeProvider();
  const supported = () =>
    preferredProvider() === 'azure' ? (azureSupported() || browserSupported()) : browserSupported();
  const isRecording = () => phase() === 'recording';
  const isProcessing = () => phase() === 'finalizing';
  const hasDraft = () => !!getCommittedVoiceInputText(transcript(), interimTranscript());
  const previewText = () => composeVoiceInputText('', transcript(), interimTranscript(), true);

  const clearActiveResources = () => {
    if (autoStopTimer) {
      clearTimeout(autoStopTimer);
      autoStopTimer = null;
    }
    if (browserRecognition) {
      browserRecognition.onstart = null;
      browserRecognition.onresult = null;
      browserRecognition.onerror = null;
      browserRecognition.onend = null;
      browserRecognition = null;
    }
    if (azureRecognizer) {
      azureRecognizer.recognizing = null;
      azureRecognizer.recognized = null;
      azureRecognizer.canceled = null;
      azureRecognizer.sessionStopped = null;
      azureRecognizer.close?.();
      azureRecognizer = null;
    }
  };

  const setSessionPhase = (sessionId: number, nextPhase: VoiceInputPhase) => {
    if (sessionId !== activeSessionId) return;
    setPhase(nextPhase);
  };

  const clearDraft = () => {
    activeSessionId += 1;
    clearActiveResources();
    setTranscript('');
    setInterimTranscript('');
    setFallbackMessage(null);
    setError(null);
    setPhase('idle');
  };

  const resetSession = (nextPhase: VoiceInputPhase = 'idle') => {
    clearActiveResources();
    setTranscript('');
    setInterimTranscript('');
    setActiveProvider(preferredProvider() === 'azure' && azureSupported() ? 'azure' : 'browser');
    setPhase(nextPhase);
  };

  const finalizeSession = (sessionId: number) => {
    if (sessionId !== activeSessionId) return;
    clearActiveResources();
    const committedText = getCommittedVoiceInputText(transcript(), interimTranscript());
    setInterimTranscript('');
    setPhase(committedText ? 'ready' : (error() ? 'error' : 'idle'));
  };

  const scheduleAutoStop = (sessionId: number) => {
    if (autoStopTimer) clearTimeout(autoStopTimer);
    autoStopTimer = setTimeout(() => {
      autoStopTimer = null;
      if (sessionId !== activeSessionId || phase() !== 'recording') return;
      stopRecording();
    }, AUTO_STOP_AFTER_SPEECH_MS);
  };

  const beginNewSession = (nextBaseText: string) => {
    clearActiveResources();
    activeSessionId += 1;
    setTranscript('');
    setInterimTranscript('');
    setError(null);
    setFallbackMessage(null);
    setBaseText(nextBaseText);
    return activeSessionId;
  };

  const startBrowserRecognition = async (sessionId: number) => {
    const Recognition = getRecognitionConstructor();
    if (!Recognition) {
      setError('This browser does not support voice input.');
      setSessionPhase(sessionId, 'error');
      return false;
    }

    setActiveProvider('browser');
    browserRecognition = new Recognition();
    browserRecognition.continuous = true;
    browserRecognition.interimResults = true;
    browserRecognition.lang = resolveVoiceInputLanguage(config().language, config().appLanguage);
    browserRecognition.onstart = () => {
      setSessionPhase(sessionId, 'recording');
    };
    browserRecognition.onresult = (event) => {
      if (sessionId !== activeSessionId) return;
      const results = Array.from(event.results || []);
      const finalChunks: string[] = [];
      const interimChunks: string[] = [];
      for (const result of results) {
        const text = result?.[0]?.transcript || '';
        if (!text.trim()) continue;
        if (result.isFinal) finalChunks.push(text);
        else interimChunks.push(text);
      }
      setTranscript(normalizeWhitespace(finalChunks.join(' ')));
      setInterimTranscript(normalizeWhitespace(interimChunks.join(' ')));
      if (finalChunks.length > 0 || interimChunks.length > 0) {
        scheduleAutoStop(sessionId);
      }
    };
    browserRecognition.onerror = (event) => {
      if (sessionId !== activeSessionId) return;
      const nextError = mapBrowserRecognitionError(event.error);
      if (nextError) {
        setError(nextError);
        setSessionPhase(sessionId, 'error');
      }
      if (event.error === 'aborted') {
        resetSession();
      }
    };
    browserRecognition.onend = () => {
      finalizeSession(sessionId);
    };

    try {
      browserRecognition.start();
      return true;
    } catch (e: any) {
      if (sessionId !== activeSessionId) return false;
      resetSession();
      setError(e?.message ? `Voice input failed: ${e.message}` : 'Voice input failed to start.');
      setPhase('error');
      return false;
    }
  };

  const startAzureRecognition = async (sessionId: number) => {
    const agentId = config().agentId;
    if (!agentId) {
      setError('Azure voice input requires an agent with cloud STT configured.');
      setSessionPhase(sessionId, 'error');
      return false;
    }
    try {
      setActiveProvider('azure');
      const sdk = await loadAzureSpeechSdk();
      if (sessionId !== activeSessionId) return false;
      const response = await fetch(`/api/speech/stt/token?agent_id=${encodeURIComponent(agentId)}`);
      if (sessionId !== activeSessionId) return false;
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || `HTTP ${response.status}`);
      }
      const tokenPayload = await response.json();
      const speechConfig = sdk.SpeechConfig.fromAuthorizationToken(tokenPayload.token, tokenPayload.region);
      speechConfig.speechRecognitionLanguage = resolveVoiceInputLanguage(config().language, config().appLanguage);
      if (tokenPayload.endpoint_id) {
        speechConfig.endpointId = tokenPayload.endpoint_id;
      }
      const audioConfig = sdk.AudioConfig.fromDefaultMicrophoneInput();
      azureRecognizer = new sdk.SpeechRecognizer(speechConfig, audioConfig);
      azureRecognizer.recognizing = (_sender, event) => {
        if (sessionId !== activeSessionId) return;
        const next = normalizeWhitespace(event.result?.text || '');
        setInterimTranscript(next);
        if (next) {
          scheduleAutoStop(sessionId);
        }
      };
      azureRecognizer.recognized = (_sender, event) => {
        if (sessionId !== activeSessionId) return;
        const next = normalizeWhitespace(event.result?.text || '');
        if (!next) return;
        setTranscript((current) => appendWithSpacing(current, next));
        setInterimTranscript('');
        scheduleAutoStop(sessionId);
      };
      azureRecognizer.canceled = (_sender, event) => {
        if (sessionId !== activeSessionId) return;
        setError(event.errorDetails || 'Azure Speech recognition was canceled.');
        clearActiveResources();
        setPhase('error');
      };
      azureRecognizer.sessionStopped = () => {
        finalizeSession(sessionId);
      };
      await new Promise<void>((resolve, reject) => {
        azureRecognizer?.startContinuousRecognitionAsync(
          () => resolve(),
          (sdkError) => reject(new Error(sdkError)),
        );
      });
      if (sessionId !== activeSessionId) return false;
      setSessionPhase(sessionId, 'recording');
      return true;
    } catch (e: any) {
      if (sessionId !== activeSessionId) return false;
      clearActiveResources();
      const fallbackAvailable = browserSupported();
      if (fallbackAvailable) {
        setFallbackMessage('Azure Speech unavailable. Switched to browser dictation.');
        setError(null);
        return startBrowserRecognition(sessionId);
      }
      setError(e?.message ? `Azure voice input failed: ${e.message}` : 'Azure voice input failed.');
      setPhase('error');
      return false;
    }
  };

  const startRecording = async (_baseText = '') => {
    if (!supported()) {
      setError(preferredProvider() === 'azure' ? 'Azure voice input is not available in this browser, and browser dictation is unavailable too.' : 'This browser does not support voice input.');
      setPhase('error');
      return false;
    }
    const sessionId = beginNewSession(_baseText);
    setPhase('finalizing');
    const ok = preferredProvider() === 'azure' ? await startAzureRecognition(sessionId) : await startBrowserRecognition(sessionId);
    if (!ok && sessionId === activeSessionId && phase() === 'finalizing') {
      setPhase(error() ? 'error' : 'idle');
    }
    return ok;
  };

  const stopRecording = () => {
    if (phase() !== 'recording') return;
    const sessionId = activeSessionId;
    setPhase('finalizing');
    if (provider() === 'azure') {
      if (!azureRecognizer) {
        finalizeSession(sessionId);
        return;
      }
      azureRecognizer.stopContinuousRecognitionAsync(
        () => undefined,
        (sdkError) => {
          if (sessionId !== activeSessionId) return;
          setError(`Azure voice input failed: ${sdkError}`);
          clearActiveResources();
          setPhase('error');
        },
      );
      return;
    }

    if (!browserRecognition) {
      finalizeSession(sessionId);
      return;
    }
    try {
      browserRecognition.stop();
    } catch {
      finalizeSession(sessionId);
    }
  };

  const cancelRecording = () => {
    const currentAzureRecognizer = azureRecognizer;
    const currentBrowserRecognition = browserRecognition;
    activeSessionId += 1;
    clearActiveResources();
    if (provider() === 'azure') {
      currentAzureRecognizer?.stopContinuousRecognitionAsync(() => undefined, () => undefined);
    } else {
      currentBrowserRecognition?.abort();
    }
    resetSession();
  };

  const toggleRecording = async (baseText = '') => {
    if (isRecording()) {
      stopRecording();
      return true;
    }
    if (isProcessing()) return true;
    return startRecording(baseText);
  };

  const clearError = () => {
    setError(null);
    if (phase() === 'error' && !hasDraft()) {
      setPhase('idle');
    }
  };

  const consumeDraft = () => {
    const draft = getCommittedVoiceInputText(transcript(), interimTranscript());
    const next = draft ? composeVoiceInputText(baseText(), draft, '', false) : baseText();
    clearDraft();
    return next;
  };

  onCleanup(() => {
    cancelRecording();
  });

  return {
    supported,
    provider,
    preferredProvider,
    phase,
    isRecording,
    isProcessing,
    hasDraft,
    transcript,
    interimTranscript,
    previewText,
    baseText,
    error,
    fallbackMessage,
    startRecording,
    stopRecording,
    cancelRecording,
    toggleRecording,
    clearError,
    clearDraft,
    consumeDraft,
  };
}
