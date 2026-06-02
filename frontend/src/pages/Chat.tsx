import 'highlight.js/styles/github-dark.css';
import 'katex/dist/katex.min.css';
import { SpeechControllerProvider } from '../context/SpeechControllerContext';
import ChatPageContent from './chat/components/ChatPageContent';
import { useChatPageConfig } from './chat/hooks/useChatPageConfig';

export default function Chat() {
  const { speechPrefs, featureFlags } = useChatPageConfig();

  return (
    <SpeechControllerProvider prefs={speechPrefs}>
      <ChatPageContent
        speechPrefs={speechPrefs}
        traceUiEnabled={speechPrefs().advanced_mode || !!featureFlags().chat_trace_ui_enabled}
        traceRawEnabled={!!featureFlags().chat_trace_raw_enabled}
      />
    </SpeechControllerProvider>
  );
}
