export type Agent = {
  id: string;
  name: string;
  system_prompt: string;
  provider: string;
  model: string;
  enabled_tools: string[];
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
