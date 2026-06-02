import { For, Show, type Accessor } from 'solid-js';
import type { Agent, Preferences } from '../../types';
import { useVoicePreview } from './useVoicePreview';

type UserPreferencesFormProps = {
  prefs: Accessor<Preferences>;
  agents: Accessor<Agent[]>;
  onSubmit: (event: SubmitEvent) => void;
};

export function UserPreferencesForm(props: UserPreferencesFormProps) {
  const { speech, isPreviewing, previewError, previewSample } = useVoicePreview({
    prefs: props.prefs,
  });
  let formRef: HTMLFormElement | undefined;

  return (
    <form ref={formRef} class="grid gap-4" onSubmit={props.onSubmit}>
      <h3 class="text-xl font-semibold border-b pb-2">User Preferences</h3>
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Theme</label>
        <select
          data-testid="settings-theme-select"
          name="theme"
          class="w-full border rounded-lg p-2 bg-gray-50"
        >
          <option value="light" selected={props.prefs().theme === 'light'}>
            Light
          </option>
          <option value="dark" selected={props.prefs().theme === 'dark'}>
            Dark
          </option>
          <option value="system" selected={props.prefs().theme === 'system'}>
            System
          </option>
        </select>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Language</label>
        <select
          data-testid="settings-language-select"
          name="language"
          class="w-full border rounded-lg p-2 bg-gray-50"
        >
          <option value="en" selected={props.prefs().language === 'en'}>
            English
          </option>
          <option value="zh" selected={props.prefs().language === 'zh'}>
            Chinese
          </option>
        </select>
      </div>
      <div>
        <div class="flex items-center justify-between gap-3 mb-1">
          <label class="block text-sm font-medium text-gray-700">Default Agent</label>
          <a href="/agents" class="text-emerald-600 hover:underline text-sm font-medium">
            Manage agents →
          </a>
        </div>
        <select
          data-testid="settings-default-agent-select"
          name="default_agent"
          class="w-full border rounded-lg p-2 bg-gray-50"
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
      <div class="rounded-lg border border-gray-200 bg-gray-50/80 p-4 space-y-4">
        <h4 class="text-sm font-semibold text-gray-800">Advanced Mode</h4>
        <label class="flex items-center justify-between gap-3 cursor-pointer">
          <div class="flex-1">
            <span class="text-sm font-medium text-gray-700 block">Enable advanced mode</span>
            <span class="text-xs text-gray-500">Show granular controls for model selection, routing roles, and trace details.</span>
          </div>
          <input
            type="checkbox"
            name="advanced_mode"
            class="h-4 w-4 accent-emerald-600"
            checked={props.prefs().advanced_mode}
          />
        </label>
      </div>
      <div class="rounded-lg border border-gray-200 bg-gray-50/80 p-4 space-y-4">
        <h4 class="text-sm font-semibold text-gray-800">Voice Input</h4>
        <div class="text-xs text-gray-500">
          Voice input now works in two steps: listen first, then review a voice draft and insert it into the composer when it looks right.
        </div>
        <label class="flex items-center justify-between gap-3">
          <span class="text-sm font-medium text-gray-700">Enable voice input</span>
          <input
            type="checkbox"
            name="voice_input_enabled"
            class="h-4 w-4 accent-emerald-600"
            checked={props.prefs().voice_input_enabled}
          />
        </label>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Default Voice Provider</label>
          <select name="voice_input_provider" class="w-full border rounded-lg p-2 bg-white">
            <option value="browser" selected={props.prefs().voice_input_provider === 'browser'}>
              Browser Speech API
            </option>
            <option value="azure" selected={props.prefs().voice_input_provider === 'azure'}>
              Azure Speech (when current agent is configured)
            </option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Recognition Language</label>
          <select name="voice_input_language" class="w-full border rounded-lg p-2 bg-white">
            <option value="auto" selected={props.prefs().voice_input_language === 'auto'}>
              Auto (Follow app language, then browser language)
            </option>
            <option value="zh-CN" selected={props.prefs().voice_input_language === 'zh-CN'}>
              Chinese (Simplified)
            </option>
            <option value="en-US" selected={props.prefs().voice_input_language === 'en-US'}>
              English (US)
            </option>
          </select>
        </div>
        <label class="flex items-center justify-between gap-3">
          <span class="text-sm font-medium text-gray-700">Show live voice preview while listening</span>
          <input
            type="checkbox"
            name="voice_input_show_interim"
            class="h-4 w-4 accent-emerald-600"
            checked={props.prefs().voice_input_show_interim}
          />
        </label>
        <div class="text-xs text-gray-500">
          Auto mode follows the app language first. For Chinese input, choose Chinese explicitly or keep the app in Chinese. The live preview appears in the voice status card, not directly in the message box.
        </div>
      </div>
      <div class="rounded-lg border border-gray-200 bg-gray-50/80 p-4 space-y-4">
        <h4 class="text-sm font-semibold text-gray-800">Speech Synthesis</h4>
        <label class="flex items-center justify-between gap-3">
          <span class="text-sm font-medium text-gray-700">Auto-read assistant replies</span>
          <input
            type="checkbox"
            name="auto_speech_enabled"
            class="h-4 w-4 accent-emerald-600"
            checked={props.prefs().auto_speech_enabled}
          />
        </label>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Speech Engine</label>
          <select name="speech_engine" class="w-full border rounded-lg p-2 bg-white">
            <option value="browser" selected={props.prefs().speech_engine === 'browser'}>
              Browser (Free)
            </option>
            <option value="openai" selected={props.prefs().speech_engine === 'openai'}>
              OpenAI (High Quality)
            </option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Speech Rate ({props.prefs().speech_rate.toFixed(1)}x)
          </label>
          <input
            type="range"
            name="speech_rate"
            min="0.5"
            max="2"
            step="0.1"
            value={props.prefs().speech_rate}
            class="w-full"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Volume ({Math.round(props.prefs().speech_volume * 100)}%)
          </label>
          <input
            type="range"
            name="speech_volume"
            min="0"
            max="1"
            step="0.1"
            value={props.prefs().speech_volume}
            class="w-full"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Browser Voice</label>
          <select
            name="speech_voice"
            class="w-full border rounded-lg p-2 bg-white disabled:opacity-60"
            disabled={!speech.supported()}
          >
            <option value="" selected={props.prefs().speech_voice === ''}>
              Browser Default
            </option>
            <For each={speech.voices()}>
              {(voice) => (
                <option value={voice.voiceURI} selected={props.prefs().speech_voice === voice.voiceURI}>
                  {voice.name} ({voice.lang})
                </option>
              )}
            </For>
          </select>
        </div>
        <div class="grid gap-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">OpenAI Voice</label>
            <select name="speech_openai_voice" class="w-full border rounded-lg p-2 bg-white">
              <option value="alloy" selected={props.prefs().speech_openai_voice === 'alloy'}>Alloy</option>
              <option value="ash" selected={props.prefs().speech_openai_voice === 'ash'}>Ash</option>
              <option value="coral" selected={props.prefs().speech_openai_voice === 'coral'}>Coral</option>
              <option value="echo" selected={props.prefs().speech_openai_voice === 'echo'}>Echo</option>
              <option value="fable" selected={props.prefs().speech_openai_voice === 'fable'}>Fable</option>
              <option value="onyx" selected={props.prefs().speech_openai_voice === 'onyx'}>Onyx</option>
              <option value="nova" selected={props.prefs().speech_openai_voice === 'nova'}>Nova</option>
              <option value="sage" selected={props.prefs().speech_openai_voice === 'sage'}>Sage</option>
              <option value="shimmer" selected={props.prefs().speech_openai_voice === 'shimmer'}>Shimmer</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">OpenAI TTS Model</label>
            <select name="speech_openai_model" class="w-full border rounded-lg p-2 bg-white">
              <option value="gpt-4o-mini-tts" selected={props.prefs().speech_openai_model === 'gpt-4o-mini-tts'}>gpt-4o-mini-tts</option>
              <option value="gpt-4o-tts" selected={props.prefs().speech_openai_model === 'gpt-4o-tts'}>gpt-4o-tts</option>
              <option value="tts-1" selected={props.prefs().speech_openai_model === 'tts-1'}>tts-1</option>
              <option value="tts-1-hd" selected={props.prefs().speech_openai_model === 'tts-1-hd'}>tts-1-hd</option>
            </select>
          </div>
        </div>
        <div class="text-xs text-gray-500">
          Browser engine is free but quality depends on OS/browser voices. OpenAI usually sounds more natural.
        </div>
        <div class="flex items-center gap-3">
          <button
            type="button"
            onClick={() => { void previewSample(formRef); }}
            class={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              isPreviewing() ? 'bg-rose-600 hover:bg-rose-700 text-white' : 'bg-sky-600 hover:bg-sky-700 text-white'
            }`}
          >
            {isPreviewing() ? 'Stop Preview' : 'Preview Voice'}
          </button>
          <span class="text-xs text-gray-500">Uses current form values, no need to save first.</span>
        </div>
        <Show when={previewError()}>
          <div class="text-xs text-rose-600 bg-rose-50 border border-rose-200 rounded-md px-3 py-2">
            {previewError()}
          </div>
        </Show>
      </div>
      <div>
        <button
          data-testid="settings-save-preferences"
          type="submit"
          class="bg-emerald-600 text-white px-6 py-2 rounded-lg hover:bg-emerald-700 transition-colors shadow-md"
        >
          Save Preferences
        </button>
      </div>
    </form>
  );
}
