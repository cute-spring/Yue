export type Agent = {
  id: string;
  name: string;
  system_prompt: string;
  provider: string;
  model: string;
  enabled_tools: string[];
  voice_input_enabled?: boolean;
  voice_input_provider?: 'browser' | 'azure';
  voice_azure_config?: {
    region?: string;
    endpoint_id?: string;
    api_key?: string;
    api_key_configured?: boolean;
  } | null;
  skill_mode?: SkillMode;
  visible_skills?: string[];
  agent_kind?: 'traditional' | 'universal';
  skill_groups?: string[];
  extra_visible_skills?: string[];
  resolved_visible_skills?: string[];
  doc_roots?: string[];
  doc_file_patterns?: string[];
  avatar?: string;
};

export type SkillMode = 'off' | 'manual' | 'auto';

export type VisibleSkillChip = {
  id: string;
  name: string;
  version?: string;
};

export type SkillGroup = {
  id: string;
  name: string;
  description?: string;
  skill_refs: string[];
};

export type SkillSpec = {
  name: string;
  version: string;
  description: string;
  availability?: boolean;
  missing_requirements?: Record<string, string[]>;
  source_path?: string;
  source_layer?: 'builtin' | 'workspace' | 'user' | string;
  source_dir?: string;
  override_from?: string;
};

export type McpTool = {
  id: string;
  name: string;
  description: string;
  server: string;
};

export type SmartDraft = {
  name?: string;
  system_prompt?: string;
  enabled_tools?: string[];
  recommended_tools?: string[];
  tool_reasons?: Record<string, string>;
  tool_risks?: Record<string, string>;
};

export type ChatSession = {
  id: string;
  title: string;
  summary?: string | null;
  tags?: string[];
  updated_at: string;
  active_skill_name?: string | null;
  active_skill_version?: string | null;
};

export type Message = {
  role: string;
  content: string;
  thought?: string;
  images?: string[];
  thought_duration?: number;
  ttft?: number;
  total_duration?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
  tps?: number;
  timestamp?: string;
  provider?: string;
  model?: string;
  tools?: string[];
  tool_calls?: ToolCall[];
  citations?: any[];
  context_id?: string;
  run_id?: string;
  assistant_turn_id?: string;
  supports_reasoning?: boolean;
  deep_thinking_enabled?: boolean;
  reasoning_enabled?: boolean;
  reasoning_disabled_reason_code?: string | null;
  supports_vision?: boolean;
  vision_enabled?: boolean;
  vision_fallback_mode?: string | null;
  image_count?: number;
  error?: string;
  error_code?: string;
  finish_reason?: string;
  active_skill_name?: string;
  active_skill_version?: string;
};

export type ToolCall = {
  call_id: string;
  tool_name: string;
  args?: any;
  result?: any;
  error?: string;
  status: 'running' | 'success' | 'error';
  duration_ms?: number;
  sequence?: number;
  ts?: string;
};

export type ActionState = {
  id?: number | null;
  session_id?: string;
  skill_name: string;
  skill_version?: string | null;
  action_id: string;
  invocation_id?: string | null;
  approval_token?: string | null;
  request_id?: string | null;
  run_id?: string | null;
  assistant_turn_id?: string | null;
  lifecycle_phase?: string | null;
  lifecycle_status: string;
  status?: string | null;
  payload?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
  sequence?: number;
  ts?: string;
};

export type ChatEventEnvelope = {
  version?: string;
  event?: string;
  event_id?: string;
  run_id?: string;
  assistant_turn_id?: string;
  sequence?: number;
  ts?: string;
  payload?: Record<string, any>;
  meta?: Record<string, any>;
  content?: string;
  thought?: string;
  chat_id?: string;
  citations?: any[];
  error?: string;
  call_id?: string;
  tool_name?: string;
  args?: any;
  result?: any;
  duration_ms?: number;
  [key: string]: any;
};

export interface Provider {
  name: string;
  supports_model_refresh: boolean;
  models: string[];
  available_models: string[];
  model_capabilities?: Record<string, string[]>;
  explicit_model_capabilities?: Record<string, string[]>;
}

export type FeatureFlags = {
  chat_trace_ui_enabled?: boolean;
  chat_trace_raw_enabled?: boolean;
  [key: string]: boolean | undefined;
};

export type TraceFieldPolicy = {
  field_name: string;
  exposure: 'safe' | 'raw_only';
  reason?: string | null;
};

export type RequestHistoryItem = {
  role: string;
  content_type: string;
  content_summary?: string | null;
  image_count: number;
  truncated: boolean;
};

export type RequestAttachmentItem = {
  kind: string;
  name?: string | null;
  content_type?: string | null;
  size_bytes?: number | null;
  redacted: boolean;
};

export type RequestSnapshotRecord = {
  chat_id: string;
  assistant_turn_id: string;
  request_id: string;
  run_id: string;
  created_at: string;
  provider?: string | null;
  model?: string | null;
  agent_id?: string | null;
  requested_skill?: string | null;
  deep_thinking_enabled: boolean;
  system_prompt?: string | null;
  user_message: string;
  message_history: RequestHistoryItem[];
  attachments: RequestAttachmentItem[];
  tool_context: Record<string, any>;
  skill_context: Record<string, any>;
  runtime_flags: Record<string, any>;
  redaction: Record<string, any>;
  truncation: Record<string, any>;
};

export type ToolTraceRecord = {
  chat_id: string;
  run_id: string;
  assistant_turn_id: string;
  trace_id: string;
  parent_trace_id?: string | null;
  tool_name: string;
  tool_type?: string | null;
  call_id?: string | null;
  call_index: number;
  status: 'started' | 'success' | 'error' | 'cancelled';
  started_at?: string | null;
  finished_at?: string | null;
  duration_ms?: number | null;
  input_arguments?: any;
  output_result?: any;
  error_type?: string | null;
  error_message?: string | null;
  error_stack?: string | null;
  chain_depth: number;
  raw_event_id?: string | null;
};

export type ChatTraceBundle = {
  mode: 'summary' | 'raw';
  chat_id: string;
  run_id: string;
  assistant_turn_id: string;
  snapshot: RequestSnapshotRecord;
  tool_traces: ToolTraceRecord[];
  field_policies: TraceFieldPolicy[];
};
