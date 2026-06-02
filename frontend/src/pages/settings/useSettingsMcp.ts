import type {
  McpStatus,
  McpTemplateValidationResult,
  ParsedMcpConfig,
  SmartPasteResponse,
} from './types';
import { parseMcpManualText } from './settingsUtils';

type Accessor<T> = () => T;
type Setter<T> = (value: T | ((prev: T) => T)) => unknown;

type ToastFn = (
  type: 'success' | 'error',
  message: string,
  actionLabel?: string,
  action?: () => void,
) => void;

type UseSettingsMcpOptions = {
  mcpConfig: Accessor<string>;
  setMcpConfig: Setter<string>;
  manualText: Accessor<string>;
  setManualText: Setter<string>;
  setMcpStatus: Setter<McpStatus[]>;
  setShowManual: Setter<boolean>;
  setShowSmartPaste: Setter<boolean>;
  fetchData: () => Promise<void>;
  showToast: ToastFn;
};

export function useSettingsMcp(options: UseSettingsMcpOptions) {
  const refreshMcpStatus = async () => {
    const response = await fetch('/api/mcp/status');
    options.setMcpStatus(await response.json());
  };

  const saveMcp = async () => {
    try {
      const parsed = JSON.parse(options.mcpConfig());
      await fetch('/api/mcp/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed),
      });
      options.showToast('success', 'MCP Configuration saved!');
      await fetch('/api/mcp/reload', { method: 'POST' });
      await refreshMcpStatus();
    } catch (error) {
      options.showToast('error', `Invalid JSON: ${error}`);
    }
  };

  const validateMcpTemplate = async (
    templateId: string,
    values: Record<string, string>,
  ): Promise<McpTemplateValidationResult> => {
    const res = await fetch('/api/mcp/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ template_id: templateId, values }),
    });
    return (await res.json()) as McpTemplateValidationResult;
  };

  const installMcpTemplate = async (
    templateId: string,
    values: Record<string, string>,
  ): Promise<McpTemplateValidationResult> => {
    const validation = await validateMcpTemplate(templateId, values);
    if (!validation.ok || !validation.rendered_config) {
      if (validation.error) options.showToast('error', validation.error);
      return validation;
    }

    const res = await fetch('/api/mcp/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify([validation.rendered_config]),
    });
    if (!res.ok) {
      const detail = await res.text();
      const failed = {
        ok: false,
        rendered_config: validation.rendered_config,
        warnings: validation.warnings || [],
        error: detail || 'Failed to save MCP config',
      } satisfies McpTemplateValidationResult;
      options.showToast('error', failed.error || 'Failed to save MCP config');
      return failed;
    }

    await fetch('/api/mcp/reload', { method: 'POST' });
    await options.fetchData();
    options.showToast('success', `Installed MCP server "${validation.rendered_config.name}"`);
    return validation;
  };

  const toggleMcpEnabled = async (serverName: string, enabled: boolean) => {
    try {
      const parsed = JSON.parse(options.mcpConfig());
      const updated = parsed.map((cfg: any) => cfg.name === serverName ? { ...cfg, enabled } : cfg);
      options.setMcpConfig(JSON.stringify(updated, null, 2));
      await fetch('/api/mcp/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated),
      });
      await fetch('/api/mcp/reload', { method: 'POST' });
      await refreshMcpStatus();
    } catch (error) {
      options.showToast('error', `Failed to toggle server: ${error}`);
    }
  };

  const reloadMcp = async () => {
    await fetch('/api/mcp/reload', { method: 'POST' });
    await options.fetchData();
  };

  const confirmManual = async () => {
    try {
      const parsed = parseMcpManualText(options.manualText());
      if (parsed.kind === 'empty') return;
      if (parsed.kind === 'invalid_json') {
        options.showToast('error', 'Invalid JSON format');
        return;
      }
      if (parsed.kind === 'no_valid_servers') {
        options.showToast('error', 'No valid MCP server configuration found in JSON');
        return;
      }

      const res = await fetch('/api/mcp/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed.servers),
      });
      if (res.ok) {
        options.showToast('success', `Successfully added ${parsed.servers.length} MCP server(s)`);
        await reloadMcp();
        options.setShowManual(false);
        options.setManualText('');
      } else {
        const err = await res.json();
        options.showToast('error', `Failed to save: ${JSON.stringify(err.detail || err)}`);
      }
    } catch (error) {
      console.error('Manual add error:', error);
      options.showToast('error', `An error occurred: ${error}`);
    }
  };

  const parseMcpSmartPaste = async (rawText: string, signal: AbortSignal): Promise<SmartPasteResponse> => {
    const res = await fetch('/api/mcp/parse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ raw_text: rawText }),
      signal,
    });
    return await res.json();
  };

  const saveMcpSmartPaste = async (configs: ParsedMcpConfig[]) => {
    const payload = configs.map(({ _selected, source_index, confidence, hints, warnings, missing_fields, ...rest }) => rest);
    const res = await fetch('/api/mcp/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Save failed' }));
      throw new Error(typeof err.detail === 'string' ? err.detail : '保存失败');
    }
    await fetch('/api/mcp/reload', { method: 'POST' });
    await options.fetchData();
    options.setShowSmartPaste(false);
  };

  const deleteMcpServer = async (serverName: string) => {
    try {
      const res = await fetch(`/api/mcp/${serverName}`, { method: 'DELETE' });
      if (res.ok) {
        options.showToast('success', `MCP server "${serverName}" deleted`);
        await options.fetchData();
      } else {
        const error = await res.json();
        options.showToast('error', `Failed to delete: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      options.showToast('error', `Error deleting server: ${error}`);
    }
  };

  return {
    saveMcp,
    validateMcpTemplate,
    installMcpTemplate,
    toggleMcpEnabled,
    reloadMcp,
    confirmManual,
    parseMcpSmartPaste,
    saveMcpSmartPaste,
    deleteMcpServer,
  };
}
