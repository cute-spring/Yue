export type Agent = {
  id: string;
  name: string;
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
