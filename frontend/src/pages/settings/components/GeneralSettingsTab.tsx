import { For, Show, createSignal, onCleanup, type Accessor, type Setter } from 'solid-js';
import type { Agent, DocAccess, FeatureFlags, Preferences } from '../types';
import { useSpeechSynthesis } from '../../../hooks/useSpeechSynthesis';

type GeneralSettingsTabProps = {
  prefs: Accessor<Preferences>;
  setPrefs: Setter<Preferences>;
  agents: Accessor<Agent[]>;
  savePrefs: (prefs?: Preferences) => void;
  featureFlags: Accessor<FeatureFlags>;
  setFeatureFlags: Setter<FeatureFlags>;
  saveFeatureFlags: (featureFlags?: FeatureFlags) => void;
  docAccess: Accessor<DocAccess>;
  docAllowText: Accessor<string>;
  setDocAllowText: Setter<string>;
  docDenyText: Accessor<string>;
  setDocDenyText: Setter<string>;
  isSavingDocAccess: Accessor<boolean>;
  saveDocAccess: () => void;
};

export function GeneralSettingsTab(props: GeneralSettingsTabProps) {
  const speech = useSpeechSynthesis();
  const [isPreviewing, setIsPreviewing] = createSignal(false);
  const [previewError, setPreviewError] = createSignal('');
  let formRef: HTMLFormElement | undefined;
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

  const previewSample = async () => {
    if (!formRef) return;
    if (isPreviewing()) {
      stopPreview();
      return;
    }
    setPreviewError('');
    const formData = new FormData(formRef);
    const engine = formData.get('speech_engine') === 'openai' ? 'openai' : 'browser';
    const rate = Number(formData.get('speech_rate') ?? props.prefs().speech_rate);
    const volume = Number(formData.get('speech_volume') ?? props.prefs().speech_volume);
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

  const savePreferences = (event: SubmitEvent) => {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    const formData = new FormData(form);
    const rate = Number(formData.get('speech_rate') ?? props.prefs().speech_rate);
    const volume = Number(formData.get('speech_volume') ?? props.prefs().speech_volume);
    const next: Preferences = {
      theme: String(formData.get('theme') || props.prefs().theme),
      language: String(formData.get('language') || props.prefs().language),
      default_agent: String(formData.get('default_agent') || props.prefs().default_agent),
      advanced_mode: formData.get('advanced_mode') !== null,
      voice_input_enabled: formData.get('voice_input_enabled') !== null,
      voice_input_provider: formData.get('voice_input_provider') === 'azure' ? 'azure' : 'browser',
      voice_input_language: String(formData.get('voice_input_language') || 'auto'),
      voice_input_show_interim: formData.get('voice_input_show_interim') !== null,
      auto_speech_enabled: formData.get('auto_speech_enabled') !== null,
      speech_voice: String(formData.get('speech_voice') || ''),
      speech_rate: Number.isFinite(rate) ? Math.min(2, Math.max(0.5, rate)) : 1.0,
      speech_volume: Number.isFinite(volume) ? Math.min(1, Math.max(0, volume)) : 1.0,
      speech_engine: formData.get('speech_engine') === 'openai' ? 'openai' : 'browser',
      speech_openai_voice: String(formData.get('speech_openai_voice') || 'alloy'),
      speech_openai_model: String(formData.get('speech_openai_model') || 'gpt-4o-mini-tts'),
    };

    props.setPrefs(next);
    props.savePrefs(next);
  };

  const saveFeatureFlags = async () => {
    const next: FeatureFlags = {
      chat_trace_ui_enabled: props.featureFlags().chat_trace_ui_enabled,
      chat_trace_raw_enabled: props.featureFlags().chat_trace_raw_enabled,
    };
    props.setFeatureFlags(next);
    await props.saveFeatureFlags(next);
  };

  const SettingSection = (sectionProps: { title: string; description?: string; children: any; icon?: string }) => (
    <div class="bg-white rounded-2xl border border-gray-100 p-6 space-y-4 shadow-sm">
      <div class="flex items-start gap-4">
        <Show when={sectionProps.icon}>
          <div class="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={sectionProps.icon} />
            </svg>
          </div>
        </Show>
        <div class="flex-1">
          <h3 class="text-lg font-bold text-gray-800">{sectionProps.title}</h3>
          <Show when={sectionProps.description}>
            <p class="text-sm text-gray-500 mt-0.5">{sectionProps.description}</p>
          </Show>
        </div>
      </div>
      <div class="pt-2">{sectionProps.children}</div>
    </div>
  );

  return (
    <div class="max-w-4xl space-y-8 pb-12">
      <form ref={formRef} class="space-y-8" onSubmit={savePreferences}>
        <SettingSection 
          title="App Appearance & Language" 
          description="Customize the look and feel of your workspace."
          icon="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"
        >
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-2">Theme</label>
              <select
                data-testid="settings-theme-select"
                name="theme"
                class="w-full border border-gray-200 rounded-xl p-2.5 bg-gray-50 focus:ring-2 focus:ring-emerald-500 transition-all outline-none"
              >
                <option value="light" selected={props.prefs().theme === 'light'}>Light</option>
                <option value="dark" selected={props.prefs().theme === 'dark'}>Dark</option>
                <option value="system" selected={props.prefs().theme === 'system'}>System</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-2">Language</label>
              <select
                data-testid="settings-language-select"
                name="language"
                class="w-full border border-gray-200 rounded-xl p-2.5 bg-gray-50 focus:ring-2 focus:ring-emerald-500 transition-all outline-none"
              >
                <option value="en" selected={props.prefs().language === 'en'}>English</option>
                <option value="zh" selected={props.prefs().language === 'zh'}>Chinese</option>
              </select>
            </div>
          </div>
          <div>
            <div class="flex items-center justify-between gap-3 mb-2">
              <label class="block text-sm font-semibold text-gray-700">Default Agent</label>
              <a href="/agents" class="text-emerald-600 hover:text-emerald-700 text-xs font-bold flex items-center gap-1">
                Manage agents
                <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clip-rule="evenodd" />
                </svg>
              </a>
            </div>
            <select
              data-testid="settings-default-agent-select"
              name="default_agent"
              class="w-full border border-gray-200 rounded-xl p-2.5 bg-gray-50 focus:ring-2 focus:ring-emerald-500 transition-all outline-none"
            >
              <For each={props.agents()}>
                {(a) => (
                  <option value={a.id} selected={props.prefs().default_agent === a.id}>
                    {a.name}
                  </option>
                )}
              </For>
            </select>
          </div>
        </SettingSection>

        <SettingSection 
          title="Advanced Mode" 
          description="Show granular controls for model selection, routing roles, and trace details."
          icon="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37a1.724 1.724 0 002.572-1.065z"
        >
          <label class="flex items-center justify-between p-4 bg-emerald-50/50 rounded-xl border border-emerald-100 cursor-pointer group transition-all hover:bg-emerald-50">
            <div class="flex-1">
              <span class="text-sm font-bold text-emerald-900 block">Enable advanced mode</span>
              <span class="text-xs text-emerald-700/70 mt-0.5">Recommended for power users who need more control over internal mechanics.</span>
            </div>
            <input
              type="checkbox"
              name="advanced_mode"
              class="h-5 w-5 accent-emerald-600 rounded"
              checked={props.prefs().advanced_mode}
            />
          </label>
        </SettingSection>

        <SettingSection 
          title="Voice & Speech" 
          description="Configure how you interact with Yue using voice input and speech synthesis."
          icon="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
        >
          <div class="space-y-6">
            <div class="space-y-4">
              <h4 class="text-sm font-bold text-gray-800 flex items-center gap-2">
                <span class="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                Voice Input
              </h4>
              <div class="p-4 bg-gray-50 rounded-xl border border-gray-100 space-y-4">
                <label class="flex items-center justify-between gap-3 cursor-pointer">
                  <span class="text-sm font-medium text-gray-700">Enable voice input</span>
                  <input
                    type="checkbox"
                    name="voice_input_enabled"
                    class="h-5 w-5 accent-emerald-600 rounded"
                    checked={props.prefs().voice_input_enabled}
                  />
                </label>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label class="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wider">Default Provider</label>
                    <select name="voice_input_provider" class="w-full border border-gray-200 rounded-lg p-2 bg-white outline-none focus:ring-2 focus:ring-emerald-500">
                      <option value="browser" selected={props.prefs().voice_input_provider === 'browser'}>Browser Speech API</option>
                      <option value="azure" selected={props.prefs().voice_input_provider === 'azure'}>Azure Speech</option>
                    </select>
                  </div>
                  <div>
                    <label class="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wider">Language</label>
                    <select name="voice_input_language" class="w-full border border-gray-200 rounded-lg p-2 bg-white outline-none focus:ring-2 focus:ring-emerald-500">
                      <option value="auto" selected={props.prefs().voice_input_language === 'auto'}>Auto Detect</option>
                      <option value="zh-CN" selected={props.prefs().voice_input_language === 'zh-CN'}>Chinese (Simplified)</option>
                      <option value="en-US" selected={props.prefs().voice_input_language === 'en-US'}>English (US)</option>
                    </select>
                  </div>
                </div>
                <label class="flex items-center justify-between gap-3 cursor-pointer">
                  <span class="text-sm font-medium text-gray-700">Live preview while listening</span>
                  <input
                    type="checkbox"
                    name="voice_input_show_interim"
                    class="h-5 w-5 accent-emerald-600 rounded"
                    checked={props.prefs().voice_input_show_interim}
                  />
                </label>
              </div>
            </div>

            <div class="space-y-4">
              <h4 class="text-sm font-bold text-gray-800 flex items-center gap-2">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                Speech Synthesis
              </h4>
              <div class="p-4 bg-gray-50 rounded-xl border border-gray-100 space-y-4">
                <label class="flex items-center justify-between gap-3 cursor-pointer">
                  <span class="text-sm font-medium text-gray-700">Auto-read assistant replies</span>
                  <input
                    type="checkbox"
                    name="auto_speech_enabled"
                    class="h-5 w-5 accent-emerald-600 rounded"
                    checked={props.prefs().auto_speech_enabled}
                  />
                </label>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label class="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wider">Engine</label>
                    <select name="speech_engine" class="w-full border border-gray-200 rounded-lg p-2 bg-white outline-none focus:ring-2 focus:ring-emerald-500">
                      <option value="browser" selected={props.prefs().speech_engine === 'browser'}>Browser (Free)</option>
                      <option value="openai" selected={props.prefs().speech_engine === 'openai'}>OpenAI (HD)</option>
                    </select>
                  </div>
                  <div>
                    <label class="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wider">Browser Voice</label>
                    <select
                      name="speech_voice"
                      class="w-full border border-gray-200 rounded-lg p-2 bg-white outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50"
                      disabled={!speech.supported()}
                    >
                      <option value="" selected={props.prefs().speech_voice === ''}>Default</option>
                      <For each={speech.voices()}>
                        {(voice) => (
                          <option value={voice.voiceURI} selected={props.prefs().speech_voice === voice.voiceURI}>
                            {voice.name}
                          </option>
                        )}
                      </For>
                    </select>
                  </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
                  <div class="space-y-2">
                    <div class="flex justify-between">
                      <label class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Rate</label>
                      <span class="text-xs font-bold text-emerald-600">{props.prefs().speech_rate.toFixed(1)}x</span>
                    </div>
                    <input type="range" name="speech_rate" min="0.5" max="2" step="0.1" value={props.prefs().speech_rate} class="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-emerald-600" />
                  </div>
                  <div class="space-y-2">
                    <div class="flex justify-between">
                      <label class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Volume</label>
                      <span class="text-xs font-bold text-emerald-600">{Math.round(props.prefs().speech_volume * 100)}%</span>
                    </div>
                    <input type="range" name="speech_volume" min="0" max="1" step="0.1" value={props.prefs().speech_volume} class="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-emerald-600" />
                  </div>
                </div>

                <div class="pt-4 border-t border-gray-200 flex items-center gap-4">
                  <button
                    type="button"
                    onClick={() => { void previewSample(); }}
                    class={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold transition-all shadow-sm ${
                      isPreviewing() ? 'bg-rose-50 text-rose-600 border border-rose-100' : 'bg-white text-gray-700 border border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <Show when={isPreviewing()} fallback={<span class="w-2 h-2 rounded-full bg-emerald-500"></span>}>
                      <span class="w-2 h-2 rounded-full bg-rose-500 animate-ping"></span>
                    </Show>
                    {isPreviewing() ? 'Stop Preview' : 'Test Speech'}
                  </button>
                  <Show when={previewError()}>
                    <span class="text-xs text-rose-600 font-medium">{previewError()}</span>
                  </Show>
                </div>
              </div>
            </div>
          </div>
        </SettingSection>

        <div class="flex items-center justify-end pt-4">
          <button
            data-testid="settings-save-preferences"
            type="submit"
            class="bg-emerald-600 text-white px-8 py-3 rounded-2xl font-bold hover:bg-emerald-700 transition-all shadow-lg hover:shadow-xl active:scale-95 flex items-center gap-2"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
            </svg>
            Save All Preferences
          </button>
        </div>
      </form>

      <div class="space-y-8">
        <SettingSection 
          title="Feature Flags" 
          description="Toggle internal controls and experimental features."
          icon="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37a1.724 1.724 0 002.572-1.065z"
        >
          <div class="space-y-4">
            <label class="flex items-start gap-4 p-4 hover:bg-gray-50 rounded-xl transition-all cursor-pointer border border-transparent hover:border-gray-100">
              <input
                type="checkbox"
                class="mt-1 h-5 w-5 accent-emerald-600 rounded"
                checked={props.featureFlags().chat_trace_ui_enabled}
                onChange={(e) =>
                  props.setFeatureFlags((current) => ({
                    ...current,
                    chat_trace_ui_enabled: e.currentTarget.checked,
                  }))
                }
              />
              <span class="space-y-1">
                <span class="block text-sm font-bold text-gray-800">Trace Inspector UI</span>
                <span class="block text-xs text-gray-500 leading-relaxed">
                  Shows the read-only trace drawer in chat so you can inspect historical request and tool call data.
                </span>
              </span>
            </label>
            <label class="flex items-start gap-4 p-4 hover:bg-gray-50 rounded-xl transition-all cursor-pointer border border-transparent hover:border-gray-100">
              <input
                type="checkbox"
                class="mt-1 h-5 w-5 accent-emerald-600 rounded"
                checked={props.featureFlags().chat_trace_raw_enabled}
                onChange={(e) =>
                  props.setFeatureFlags((current) => ({
                    ...current,
                    chat_trace_raw_enabled: e.currentTarget.checked,
                  }))
                }
              />
              <span class="space-y-1">
                <span class="block text-sm font-bold text-gray-800">Raw Trace Access</span>
                <span class="block text-xs text-gray-500 leading-relaxed">
                  Allows the trace drawer to switch into raw payload mode for deeper debugging.
                </span>
              </span>
            </label>
            <div class="flex items-center justify-end pt-2">
              <button
                type="button"
                onClick={() => { void saveFeatureFlags(); }}
                class="bg-emerald-600 text-white px-6 py-2 rounded-xl font-bold hover:bg-emerald-700 transition-all shadow-md active:scale-95"
              >
                Save Flags
              </button>
            </div>
          </div>
        </SettingSection>

        <SettingSection 
          title="Document Access" 
          description="Manage security boundaries for local file access tools."
          icon="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        >
          <div class="space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="space-y-2">
                <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider">Allow Roots</label>
                <textarea
                  class="w-full border border-gray-200 rounded-xl p-3 bg-gray-50 font-mono text-xs h-32 focus:ring-2 focus:ring-emerald-500 outline-none"
                  placeholder="/Users/example/workspace"
                  value={props.docAllowText()}
                  onInput={(e) => props.setDocAllowText(e.currentTarget.value)}
                />
              </div>
              <div class="space-y-2">
                <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider">Deny Roots</label>
                <textarea
                  class="w-full border border-gray-200 rounded-xl p-3 bg-gray-50 font-mono text-xs h-32 focus:ring-2 focus:ring-emerald-500 outline-none"
                  placeholder="/Users/example/workspace/private"
                  value={props.docDenyText()}
                  onInput={(e) => props.setDocDenyText(e.currentTarget.value)}
                />
              </div>
            </div>
            <div class="flex items-center justify-between gap-3 pt-2">
              <div class="text-xs text-gray-500 font-medium">
                Active: {props.docAccess().allow_roots.length} allow • {props.docAccess().deny_roots.length} deny
              </div>
              <button
                onClick={props.saveDocAccess}
                disabled={props.isSavingDocAccess()}
                class={`px-6 py-2 rounded-xl font-bold transition-all shadow-md active:scale-95 ${
                  props.isSavingDocAccess()
                    ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                    : 'bg-emerald-600 text-white hover:bg-emerald-700'
                }`}
              >
                {props.isSavingDocAccess() ? 'Saving...' : 'Save Document Access'}
              </button>
            </div>
          </div>
        </SettingSection>
      </div>
    </div>
  );
}
