export type Agent = {
  id: string;
  name: string;
  system_prompt: string;
  provider: string;
  model: string;
  enabled_tools: string[];
  doc_roots?: string[];
  doc_file_patterns?: string[];
  avatar?: string;
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
  updated_at: string;
};

export type Message = {
  role: string;
  content: string;
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
  citations?: any[];
  context_id?: string;
  error?: string;
  finish_reason?: string;
};

export interface Provider {
  name: string;
  supports_model_refresh: boolean;
  models: string[];
  available_models: string[];
}
