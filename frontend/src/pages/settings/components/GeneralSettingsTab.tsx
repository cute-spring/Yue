import type { Accessor, Setter } from 'solid-js';
import type { Agent, DocAccess, FeatureFlags, Preferences } from '../types';
import { DocumentAccessSection } from './general/DocumentAccessSection';
import { FeatureFlagsSection } from './general/FeatureFlagsSection';
import { UserPreferencesForm } from './general/UserPreferencesForm';

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

export const buildPreferencesFromFormData = (
  formData: FormData,
  currentPrefs: Preferences,
): Preferences => {
  const rate = Number(formData.get('speech_rate') ?? currentPrefs.speech_rate);
  const volume = Number(formData.get('speech_volume') ?? currentPrefs.speech_volume);
  const providerValue = formData.get('voice_input_provider');
  const nextVoiceInputProvider = providerValue === 'azure' || providerValue === 'browser'
    ? providerValue
    : currentPrefs.voice_input_provider;

  return {
    theme: String(formData.get('theme') || currentPrefs.theme),
    language: String(formData.get('language') || currentPrefs.language),
    default_agent: String(formData.get('default_agent') || currentPrefs.default_agent),
    advanced_mode: formData.get('advanced_mode') !== null,
    voice_input_enabled: formData.get('voice_input_enabled') !== null,
    voice_input_provider: nextVoiceInputProvider,
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
};

export function GeneralSettingsTab(props: GeneralSettingsTabProps) {
  const savePreferences = (event: SubmitEvent) => {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    const formData = new FormData(form);
    const next = buildPreferencesFromFormData(formData, props.prefs());

    props.setPrefs(next);
    props.savePrefs(next);
  };

  const saveFeatureFlags = async () => {
    const next: FeatureFlags = {
      chat_trace_ui_enabled: props.featureFlags().chat_trace_ui_enabled,
      chat_trace_raw_enabled: props.featureFlags().chat_trace_raw_enabled,
      mcp_smart_paste_enabled: props.featureFlags().mcp_smart_paste_enabled,
    };
    props.setFeatureFlags(next);
    await props.saveFeatureFlags(next);
  };

  return (
    <div class="max-w-2xl space-y-6">
      <UserPreferencesForm
        prefs={props.prefs}
        agents={props.agents}
        onSubmit={savePreferences}
      />
      <FeatureFlagsSection
        featureFlags={props.featureFlags}
        setFeatureFlags={props.setFeatureFlags}
        onSave={saveFeatureFlags}
      />
      <DocumentAccessSection
        docAccess={props.docAccess}
        docAllowText={props.docAllowText}
        setDocAllowText={props.setDocAllowText}
        docDenyText={props.docDenyText}
        setDocDenyText={props.setDocDenyText}
        isSavingDocAccess={props.isSavingDocAccess}
        onSave={props.saveDocAccess}
      />
    </div>
  );
}
