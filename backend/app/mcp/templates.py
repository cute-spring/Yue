from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


PLACEHOLDER_ENV_RE = re.compile(r"^\$\{[A-Z0-9_]+\}$")


class McpTemplateField(BaseModel):
    key: str
    label: str
    type: str = "text"
    required: bool = False
    secret: bool = False
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    default_value: Any = None
    options: List[str] = Field(default_factory=list)


class McpTemplate(BaseModel):
    id: str
    name: str
    description: str
    provider: str
    deployment: str
    fields: List[McpTemplateField]


class TemplateRenderResult(BaseModel):
    rendered_config: Dict[str, Any]
    warnings: List[str] = Field(default_factory=list)


def _field(
    key: str,
    label: str,
    *,
    type: str = "text",
    required: bool = False,
    secret: bool = False,
    placeholder: Optional[str] = None,
    help_text: Optional[str] = None,
    default_value: Any = None,
    options: Optional[List[str]] = None,
) -> McpTemplateField:
    return McpTemplateField(
        key=key,
        label=label,
        type=type,
        required=required,
        secret=secret,
        placeholder=placeholder,
        help_text=help_text,
        default_value=default_value,
        options=options or [],
    )


DEFAULT_TEMPLATES: List[McpTemplate] = [
    McpTemplate(
        id="jira-company",
        name="Jira MCP",
        description=(
            "Template for Jira Cloud or internal Jira Server/Data Center. "
            "Use this when your company has its own Jira host or MCP wrapper."
        ),
        provider="jira",
        deployment="mixed",
        fields=[
            _field("serverName", "Server Name", required=True, default_value="company-jira"),
            _field(
                "deployment",
                "Deployment",
                type="select",
                required=True,
                default_value="self_hosted",
                options=["cloud", "self_hosted"],
                help_text="Choose the style that best matches your Jira environment.",
            ),
            _field("command", "Command", required=True, default_value="npx", placeholder="npx"),
            _field(
                "argsJson",
                "Args (JSON Array)",
                type="json",
                required=True,
                default_value='["-y", "your-jira-mcp-package"]',
                help_text="Replace the package or executable with the real Jira MCP implementation your company uses.",
            ),
            _field(
                "baseUrl",
                "Jira Base URL",
                required=True,
                default_value="https://jira.company.internal",
                placeholder="https://jira.example.com",
            ),
            _field(
                "baseUrlEnvKey",
                "Base URL Env Key",
                required=True,
                default_value="JIRA_BASE_URL",
                help_text="Use the exact env var name expected by your Jira MCP server.",
            ),
            _field(
                "username",
                "Username / Email",
                default_value="",
                placeholder="alice@example.com",
            ),
            _field(
                "usernameEnvKey",
                "Username Env Key",
                default_value="JIRA_USERNAME",
                help_text="Leave a username blank if your MCP server authenticates only with a token.",
            ),
            _field(
                "secretEnvVar",
                "Host Secret Env Var",
                required=True,
                default_value="JIRA_TOKEN",
                placeholder="JIRA_TOKEN",
                help_text="The rendered config stores ${ENV_NAME} so the actual secret can stay outside Yue.",
            ),
            _field(
                "tokenEnvKey",
                "Token Env Key For MCP Server",
                required=True,
                default_value="JIRA_TOKEN",
                help_text="Use the token env var name expected by your Jira MCP server.",
            ),
            _field(
                "extraEnvJson",
                "Extra Env (JSON Object)",
                type="json",
                default_value="{}",
                help_text="Optional extra env vars such as project scopes, PAT mode, or SSL flags.",
            ),
        ],
    ),
    McpTemplate(
        id="confluence-company",
        name="Confluence MCP",
        description=(
            "Template for Confluence Cloud or internal Confluence Server/Data Center. "
            "Use this when your company has its own Confluence host or MCP wrapper."
        ),
        provider="confluence",
        deployment="mixed",
        fields=[
            _field("serverName", "Server Name", required=True, default_value="company-confluence"),
            _field(
                "deployment",
                "Deployment",
                type="select",
                required=True,
                default_value="self_hosted",
                options=["cloud", "self_hosted"],
            ),
            _field("command", "Command", required=True, default_value="npx", placeholder="npx"),
            _field(
                "argsJson",
                "Args (JSON Array)",
                type="json",
                required=True,
                default_value='["-y", "your-confluence-mcp-package"]',
                help_text="Replace the package or executable with the real Confluence MCP implementation your company uses.",
            ),
            _field(
                "baseUrl",
                "Confluence Base URL",
                required=True,
                default_value="https://confluence.company.internal",
                placeholder="https://confluence.example.com",
            ),
            _field(
                "baseUrlEnvKey",
                "Base URL Env Key",
                required=True,
                default_value="CONFLUENCE_BASE_URL",
                help_text="Use the exact env var name expected by your Confluence MCP server.",
            ),
            _field(
                "username",
                "Username / Email",
                default_value="",
                placeholder="alice@example.com",
            ),
            _field(
                "usernameEnvKey",
                "Username Env Key",
                default_value="CONFLUENCE_USERNAME",
            ),
            _field(
                "secretEnvVar",
                "Host Secret Env Var",
                required=True,
                default_value="CONFLUENCE_TOKEN",
                placeholder="CONFLUENCE_TOKEN",
            ),
            _field(
                "tokenEnvKey",
                "Token Env Key For MCP Server",
                required=True,
                default_value="CONFLUENCE_TOKEN",
            ),
            _field(
                "extraEnvJson",
                "Extra Env (JSON Object)",
                type="json",
                default_value="{}",
                help_text="Optional extra env vars such as space filters or SSL flags.",
            ),
        ],
    ),
    McpTemplate(
        id="custom-company-mcp",
        name="Custom Company MCP",
        description=(
            "Generic template for an internal MCP wrapper maintained by your company. "
            "Use this when you already have a bespoke Jira/Confluence or unified knowledge MCP."
        ),
        provider="custom",
        deployment="custom_mcp",
        fields=[
            _field("serverName", "Server Name", required=True, default_value="company-internal-mcp"),
            _field("command", "Command", required=True, default_value="npx"),
            _field(
                "argsJson",
                "Args (JSON Array)",
                type="json",
                required=True,
                default_value='["-y", "your-company-mcp-package"]',
            ),
            _field(
                "envJson",
                "Env (JSON Object)",
                type="json",
                default_value='{"INTERNAL_API_TOKEN":"${INTERNAL_API_TOKEN}"}',
                help_text="Use ${ENV_NAME} placeholders so secrets come from the host environment.",
            ),
        ],
    ),
]


def list_templates() -> List[Dict[str, Any]]:
    return [template.model_dump() for template in DEFAULT_TEMPLATES]


def get_template(template_id: str) -> Optional[McpTemplate]:
    for template in DEFAULT_TEMPLATES:
        if template.id == template_id:
            return template
    return None


def _require_text(values: Dict[str, Any], key: str, label: str) -> str:
    value = values.get(key)
    if value is None:
        raise ValueError(f"{label} is required")
    text = str(value).strip()
    if not text:
        raise ValueError(f"{label} is required")
    return text


def _optional_text(values: Dict[str, Any], key: str) -> str:
    value = values.get(key)
    if value is None:
        return ""
    return str(value).strip()


def _parse_json_array(raw: str, label: str) -> List[str]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must be valid JSON") from exc
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise ValueError(f"{label} must be a JSON array of strings")
    return parsed


def _parse_json_object(raw: str, label: str) -> Dict[str, str]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} must be a JSON object")
    normalized: Dict[str, str] = {}
    for key, value in parsed.items():
        if not isinstance(key, str):
            raise ValueError(f"{label} keys must be strings")
        if not isinstance(value, str):
            raise ValueError(f"{label} values must be strings")
        normalized[key] = value
    return normalized


def _build_adapter_config(
    values: Dict[str, Any],
    *,
    name_label: str,
    base_url_label: str,
    default_base_env_key: str,
    default_user_env_key: str,
    default_token_env_key: str,
) -> TemplateRenderResult:
    server_name = _require_text(values, "serverName", "Server name")
    command = _require_text(values, "command", "Command")
    args = _parse_json_array(_require_text(values, "argsJson", "Args"), "Args")
    base_url = _require_text(values, "baseUrl", base_url_label)
    base_url_env_key = _require_text(values, "baseUrlEnvKey", f"{name_label} base URL env key")
    username = _optional_text(values, "username")
    username_env_key = _optional_text(values, "usernameEnvKey") or default_user_env_key
    token_env_key = _require_text(values, "tokenEnvKey", f"{name_label} token env key") or default_token_env_key
    secret_env_var = _require_text(values, "secretEnvVar", "Host secret env var")
    extra_env = _parse_json_object(values.get("extraEnvJson") or "{}", "Extra env")

    env = dict(extra_env)
    env[base_url_env_key] = base_url
    if username:
        env[username_env_key] = username
    env[token_env_key] = f"${{{secret_env_var}}}"

    warnings: List[str] = []
    if any("your-" in item for item in args):
        warnings.append("Replace the example MCP package or executable in Args before enabling this server in production.")
    if PLACEHOLDER_ENV_RE.match(env[token_env_key]):
        warnings.append(f"Set {secret_env_var} in the Yue host environment before reloading MCP.")
    if base_url_env_key == default_base_env_key and token_env_key == default_token_env_key:
        warnings.append("Confirm the env var names match the Jira/Confluence MCP implementation your company actually uses.")

    return TemplateRenderResult(
        rendered_config={
            "name": server_name,
            "transport": "stdio",
            "command": command,
            "args": args,
            "env": env,
            "enabled": True,
        },
        warnings=warnings,
    )


def render_template(template_id: str, values: Dict[str, Any]) -> TemplateRenderResult:
    if template_id == "jira-company":
        return _build_adapter_config(
            values,
            name_label="Jira",
            base_url_label="Jira base URL",
            default_base_env_key="JIRA_BASE_URL",
            default_user_env_key="JIRA_USERNAME",
            default_token_env_key="JIRA_TOKEN",
        )
    if template_id == "confluence-company":
        return _build_adapter_config(
            values,
            name_label="Confluence",
            base_url_label="Confluence base URL",
            default_base_env_key="CONFLUENCE_BASE_URL",
            default_user_env_key="CONFLUENCE_USERNAME",
            default_token_env_key="CONFLUENCE_TOKEN",
        )
    if template_id == "custom-company-mcp":
        server_name = _require_text(values, "serverName", "Server name")
        command = _require_text(values, "command", "Command")
        args = _parse_json_array(_require_text(values, "argsJson", "Args"), "Args")
        env = _parse_json_object(values.get("envJson") or "{}", "Env")
        warnings: List[str] = []
        placeholder_keys = [key for key, value in env.items() if PLACEHOLDER_ENV_RE.match(value)]
        if any("your-company" in item for item in args):
            warnings.append("Replace the example MCP package or executable in Args before enabling this server in production.")
        if placeholder_keys:
            warnings.append(
                "This config uses host env placeholders for: "
                + ", ".join(sorted(placeholder_keys))
                + ". Make sure those env vars are set before reloading MCP."
            )
        return TemplateRenderResult(
            rendered_config={
                "name": server_name,
                "transport": "stdio",
                "command": command,
                "args": args,
                "env": env,
                "enabled": True,
            },
            warnings=warnings,
        )
    raise ValueError(f"Unknown MCP template: {template_id}")
