import type { CustomModel, NewCustomModelDraft } from './types';

const trimOptional = (value: string | undefined) => {
  const trimmed = value?.trim();
  return trimmed ? trimmed : undefined;
};

const normalizeBaseUrl = (value: string | undefined) => {
  let normalized = trimOptional(value);
  if (!normalized) return undefined;
  normalized = normalized.replace(/\/+$/, '');
  normalized = normalized.replace(/\/chat\/completions$/i, '');
  return normalized;
};

export const normalizeCustomModelDraft = (draft: NewCustomModelDraft): NewCustomModelDraft => ({
  name: draft.name.trim(),
  provider: draft.provider,
  model: trimOptional(draft.model),
  base_url: normalizeBaseUrl(draft.base_url),
  api_key: trimOptional(draft.api_key),
  capabilities: draft.capabilities || [],
});

export const validateCustomModelDraft = (draft: NewCustomModelDraft) => {
  const normalized = normalizeCustomModelDraft(draft);
  if (!normalized.name) return 'Name is required';
  if (
    normalized.base_url &&
    !normalized.base_url.startsWith('http://') &&
    !normalized.base_url.startsWith('https://')
  ) {
    return 'Base URL must start with http:// or https://';
  }
  return null;
};

export const buildCustomModelCreatePayload = (draft: NewCustomModelDraft) => ({
  name: normalizeCustomModelDraft(draft).name,
  provider: normalizeCustomModelDraft(draft).provider,
  base_url: normalizeCustomModelDraft(draft).base_url,
  api_key: normalizeCustomModelDraft(draft).api_key,
  model: normalizeCustomModelDraft(draft).model,
  capabilities: normalizeCustomModelDraft(draft).capabilities,
});

export const buildCustomModelTestPayload = (
  model: Pick<CustomModel, 'provider' | 'base_url' | 'api_key' | 'model'>
) => ({
  provider: model.provider,
  base_url: normalizeBaseUrl(model.base_url),
  api_key: trimOptional(model.api_key),
  model: trimOptional(model.model),
});
