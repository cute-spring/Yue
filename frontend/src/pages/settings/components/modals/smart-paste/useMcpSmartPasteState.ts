import { createSignal, onCleanup, type Accessor, type Setter } from 'solid-js';
import type { ParsedMcpConfig, SmartPasteResponse } from '../../../types';
import {
  applyReplacements,
  applyTransportChange,
  detectSensitiveValues,
  findNameConflicts,
  validateSmartPasteInput,
} from '../McpSmartPasteModal.logic';
import type { SensitiveDetection } from '../McpSmartPasteModal.logic';

export type SmartPastePhase = 'idle' | 'sensitive_check' | 'parsing' | 'preview' | 'saving';

type UseMcpSmartPasteStateOptions = {
  existingNames: string[];
  onClose: () => void;
  onParse: (rawText: string, signal: AbortSignal) => Promise<SmartPasteResponse>;
  onSave: (configs: ParsedMcpConfig[]) => Promise<void>;
};

export type McpSmartPasteState = {
  phase: Accessor<SmartPastePhase>;
  rawText: Accessor<string>;
  setRawText: Setter<string>;
  results: Accessor<ParsedMcpConfig[]>;
  parseError: Accessor<string | null>;
  saveError: Accessor<string | null>;
  saveSuccess: Accessor<boolean>;
  sensitiveDetections: Accessor<SensitiveDetection[]>;
  replacedText: Accessor<string>;
  parseHint: Accessor<string>;
  handleParse: () => Promise<void>;
  handleCancelParse: () => void;
  handleSensitiveReplaceAll: () => void;
  handleSensitiveSendAnyway: () => void;
  handleSensitiveBackToEdit: () => void;
  handleRetry: () => void;
  handleReparse: () => void;
  handleUpdateCandidate: (index: number, updates: Partial<ParsedMcpConfig>) => void;
  handleTransportChange: (index: number, newTransport: 'stdio' | 'streamable_http') => void;
  handleToggleSelected: (index: number) => void;
  handleDeleteCandidate: (index: number) => void;
  handleUpdateHeader: (configIndex: number, key: string, value: string) => void;
  handleRemoveHeader: (configIndex: number, key: string) => void;
  handleAddHeader: (configIndex: number) => void;
  handleUpdateEnv: (configIndex: number, key: string, value: string) => void;
  handleRemoveEnv: (configIndex: number, key: string) => void;
  handleAddEnv: (configIndex: number) => void;
  handleSave: () => Promise<void>;
};

export function useMcpSmartPasteState(options: UseMcpSmartPasteStateOptions): McpSmartPasteState {
  const [phase, setPhase] = createSignal<SmartPastePhase>('idle');
  const [rawText, setRawText] = createSignal('');
  const [results, setResults] = createSignal<ParsedMcpConfig[]>([]);
  const [parseError, setParseError] = createSignal<string | null>(null);
  const [saveError, setSaveError] = createSignal<string | null>(null);
  const [saveSuccess, setSaveSuccess] = createSignal(false);
  const [sensitiveDetections, setSensitiveDetections] = createSignal<SensitiveDetection[]>([]);
  const [replacedText, setReplacedText] = createSignal('');
  const [parseHint, setParseHint] = createSignal('');
  let abortController: AbortController | null = null;
  let parseHintTimer: ReturnType<typeof setTimeout> | undefined;

  onCleanup(() => {
    if (abortController) {
      abortController.abort();
    }
  });

  const doParse = async (text: string) => {
    setPhase('parsing');
    setParseHint('');
    abortController = new AbortController();
    parseHintTimer = setTimeout(() => setParseHint('AI Analyzing, please wait...'), 1500);

    try {
      const response = await options.onParse(text, abortController.signal);
      if (response.ok && response.results.length > 0) {
        setResults(response.results);
        setPhase('preview');
      } else {
        setParseError(response.error || 'Unable to parse valid MCP configurations from input');
        setPhase('idle');
      }
    } catch (e: any) {
      if (e?.name === 'AbortError') {
        setPhase('idle');
        return;
      }
      setParseError(e?.message || 'Parse failed, please try again');
      setPhase('idle');
    } finally {
      clearTimeout(parseHintTimer);
      setParseHint('');
      abortController = null;
    }
  };

  const handleParse = async () => {
    const validation = validateSmartPasteInput(rawText());
    if (validation.kind === 'empty') {
      return;
    }
    if (validation.kind === 'too_long') {
      setParseError('Input text is too long, please shorten it and try again');
      return;
    }

    setParseError(null);

    const detections = detectSensitiveValues(rawText());
    if (detections.length > 0) {
      setSensitiveDetections(detections);
      setReplacedText(applyReplacements(rawText(), detections));
      setPhase('sensitive_check');
      return;
    }

    await doParse(rawText());
  };

  const handleCancelParse = () => {
    if (abortController) {
      abortController.abort();
      abortController = null;
    }
    setPhase('idle');
  };

  const handleSensitiveReplaceAll = () => {
    const cleanText = applyReplacements(rawText(), sensitiveDetections());
    setRawText(cleanText);
    setPhase('idle');
    void doParse(cleanText);
  };

  const handleSensitiveSendAnyway = () => {
    setPhase('idle');
    void doParse(rawText());
  };

  const handleSensitiveBackToEdit = () => {
    setPhase('idle');
  };

  const handleRetry = () => {
    setPhase('idle');
    setParseError(null);
  };

  const handleReparse = () => {
    setPhase('idle');
    setParseError(null);
  };

  const handleUpdateCandidate = (index: number, updates: Partial<ParsedMcpConfig>) => {
    setResults((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], ...updates };
      return next;
    });
  };

  const handleTransportChange = (index: number, newTransport: 'stdio' | 'streamable_http') => {
    setResults((prev) => {
      const next = [...prev];
      next[index] = applyTransportChange(next[index], newTransport);
      return next;
    });
  };

  const handleToggleSelected = (index: number) => {
    setResults((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], _selected: !next[index]._selected };
      return next;
    });
  };

  const handleDeleteCandidate = (index: number) => {
    setResults((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpdateHeader = (configIndex: number, key: string, value: string) => {
    setResults((prev) => {
      const next = [...prev];
      const headers = { ...(next[configIndex].headers || {}) };
      if (value === '' && !(key in headers)) return prev;
      headers[key] = value;
      next[configIndex] = { ...next[configIndex], headers };
      return next;
    });
  };

  const handleRemoveHeader = (configIndex: number, key: string) => {
    setResults((prev) => {
      const next = [...prev];
      const headers = { ...(next[configIndex].headers || {}) };
      delete headers[key];
      next[configIndex] = { ...next[configIndex], headers };
      return next;
    });
  };

  const handleAddHeader = (configIndex: number) => {
    setResults((prev) => {
      const next = [...prev];
      const headers = { ...(next[configIndex].headers || {}) };
      let i = 0;
      while (`header_${i}` in headers) i++;
      headers[`header_${i}`] = '';
      next[configIndex] = { ...next[configIndex], headers };
      return next;
    });
  };

  const handleUpdateEnv = (configIndex: number, key: string, value: string) => {
    setResults((prev) => {
      const next = [...prev];
      const env = { ...(next[configIndex].env || {}) };
      if (value === '' && !(key in env)) return prev;
      env[key] = value;
      next[configIndex] = { ...next[configIndex], env };
      return next;
    });
  };

  const handleRemoveEnv = (configIndex: number, key: string) => {
    setResults((prev) => {
      const next = [...prev];
      const env = { ...(next[configIndex].env || {}) };
      delete env[key];
      next[configIndex] = { ...next[configIndex], env };
      return next;
    });
  };

  const handleAddEnv = (configIndex: number) => {
    setResults((prev) => {
      const next = [...prev];
      const env = { ...(next[configIndex].env || {}) };
      let i = 0;
      while (`ENV_${i}` in env) i++;
      env[`ENV_${i}`] = '';
      next[configIndex] = { ...next[configIndex], env };
      return next;
    });
  };

  const handleSave = async () => {
    const selected = results().filter((r) => r._selected !== false);
    if (selected.length === 0) {
      setSaveError('Please select at least one configuration to save');
      return;
    }

    const conflicts = findNameConflicts(options.existingNames, selected);
    if (conflicts.length > 0) {
      setSaveError(`Configuration name already exists: ${conflicts.join(', ')}`);
      return;
    }

    setPhase('saving');
    setSaveError(null);

    try {
      await options.onSave(selected);
      setSaveSuccess(true);
      setTimeout(() => options.onClose(), 1000);
    } catch (e: any) {
      setSaveError(e?.message || 'Save failed');
      setPhase('preview');
    }
  };

  return {
    phase,
    rawText,
    setRawText,
    results,
    parseError,
    saveError,
    saveSuccess,
    sensitiveDetections,
    replacedText,
    parseHint,
    handleParse,
    handleCancelParse,
    handleSensitiveReplaceAll,
    handleSensitiveSendAnyway,
    handleSensitiveBackToEdit,
    handleRetry,
    handleReparse,
    handleUpdateCandidate,
    handleTransportChange,
    handleToggleSelected,
    handleDeleteCandidate,
    handleUpdateHeader,
    handleRemoveHeader,
    handleAddHeader,
    handleUpdateEnv,
    handleRemoveEnv,
    handleAddEnv,
    handleSave,
  };
}
