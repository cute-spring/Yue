# YUE Jira MCP Onboarding

This guide prepares YUE for a company-internal Jira MCP server that authenticates with a base URL and personal token. It is intentionally `v1`, read-oriented, and safe by default.

## Runtime alignment

- Built-in agent contract: `builtin-jira` in [backend/data/builtin/agents/builtin-jira.yaml](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/builtin/agents/builtin-jira.yaml)
- Agent mode: `skill_mode: manual`
- Visible skill: `jira:1.0.0`
- Direct tools on the agent: none
- Safety posture: read, summarize, inspect, and draft only; no Jira mutation path is enabled in `v1`
- Import-gate note: this onboarding is config-first. It does not require enabling a live MCP package command yet, and it remains compatible with `YUE_SKILL_RUNTIME_MODE=import-gate` because the built-in agent contract stays stable while MCP server details remain externalized
- Forward policy note: future live Jira integration should treat reads as default-authorized, while any create/update/comment/transition/link or other non-read action must still require explicit user confirmation

## Operator setup flow

1. Confirm the company Jira base URL, for example `https://jira.company.internal`.
2. Confirm the company MCP server’s personal-token env key.
3. If the server also expects a username or email, capture that env key too. Treat it as optional for YUE onboarding.
4. Keep the MCP entry disabled until the real package or executable name is known.
5. Set the host token env var outside YUE, for example `JIRA_TOKEN`, before any future reload or live enablement.
6. Limit the first-day scope with read-oriented env hints such as allowed projects, default JQL, and read-only flags.

## Finalized MCP config template

Use this as the team baseline in [backend/data/mcp_configs.json.example](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/data/mcp_configs.json.example) or when rendering the `jira-company` template in Settings:

```json
{
  "name": "company-jira",
  "transport": "stdio",
  "command": "npx",
  "args": [
    "-y",
    "your-company-jira-mcp-package"
  ],
  "enabled": false,
  "env": {
    "JIRA_BASE_URL": "https://jira.company.internal",
    "JIRA_TOKEN": "${JIRA_TOKEN}",
    "JIRA_PROJECT": "YUE",
    "JIRA_ALLOWED_PROJECTS": "YUE",
    "JIRA_DEFAULT_JQL": "project = YUE ORDER BY updated DESC",
    "JIRA_READ_ONLY": "true"
  }
}
```

Notes:
- `enabled` stays `false` until the real company MCP package or executable is known.
- `args` uses a placeholder package name on purpose. Do not guess the final package identifier.
- `JIRA_TOKEN` is the host-side secret placeholder, not the literal token value.
- `JIRA_PROJECT`, `JIRA_ALLOWED_PROJECTS`, `JIRA_DEFAULT_JQL`, and `JIRA_READ_ONLY` are safe starter hints for a read-only first day.

## First-day read-only smoke test checklist

1. Verify the built-in Jira agent is visible in YUE and still resolves to `builtin-jira`.
2. Verify the agent remains read-oriented: no direct MCP tools on the agent, and no write promise in the prompt.
3. Confirm the rendered or example MCP config is still disabled by default.
4. Confirm the config contains a base URL entry and a token placeholder entry.
5. Confirm no username field is required for the baseline contract.
6. Confirm the package name is still a placeholder rather than an assumed production package.
7. If the company MCP server is available later, enable only read-style discovery calls first:
   - list accessible projects
   - fetch one known issue
   - run a bounded JQL query using the default project scope
8. Stop if the server asks for extra auth fields or non-read flags that are not documented by the company MCP contract.

When write support is enabled later:

- keep read flows default-open
- require a preview for every non-read Jira action
- require explicit user confirmation before every non-read Jira execution

## Contract note

Expected env key aliases:

- Base URL aliases commonly seen: `JIRA_BASE_URL`, `JIRA_URL`
- Personal token aliases commonly seen: `JIRA_TOKEN`, `JIRA_API_TOKEN`, `JIRA_PERSONAL_TOKEN`
- Optional username aliases: `JIRA_USERNAME`, `JIRA_EMAIL`

Implementation-dependent fields on the company MCP server:

- The actual package or executable in `args`
- Whether a username or email is required in addition to the token
- The exact env key names the server reads
- Whether project scoping uses `JIRA_PROJECT`, `JIRA_ALLOWED_PROJECTS`, another key, or no extra key
- Whether read-only mode is controlled by `JIRA_READ_ONLY`, another flag, or is implicit
- Whether default query seeding uses `JIRA_DEFAULT_JQL`, another key, or no key at all

## Company MCP adapter mapping table

Fill this in once the internal Jira MCP implementation is confirmed. The goal is to avoid rediscovering the contract during live enablement.

| Contract area | YUE baseline | Company actual value | Required before first live enablement? | Notes |
|---|---|---|---|---|
| MCP package / executable | `your-company-jira-mcp-package` | `TBD` | Yes | Replace the placeholder only when the owner confirms the real package or executable |
| Command | `npx` | `TBD` | Yes | Could also be `node`, `uvx`, a shell wrapper, or a local binary |
| Base URL env key | `JIRA_BASE_URL` | `TBD` | Yes | Common alias: `JIRA_URL` |
| Personal token env key | `JIRA_TOKEN` | `TBD` | Yes | Common aliases: `JIRA_API_TOKEN`, `JIRA_PERSONAL_TOKEN` |
| Host secret env var placeholder | `JIRA_TOKEN` | `TBD` | Yes | This is the `${ENV_NAME}` placeholder stored in the rendered config |
| Username required | `No` | `TBD` | Yes | Mark `Yes` only if the company MCP server rejects token-only auth |
| Username env key | `JIRA_USERNAME` | `TBD` | If username required | Common alias: `JIRA_EMAIL` |
| Project scope key | `JIRA_ALLOWED_PROJECTS` | `TBD` | Recommended | Keep first-day scope narrow |
| Default project key | `JIRA_PROJECT` | `TBD` | Optional | Useful for draft and query defaults |
| Default JQL key | `JIRA_DEFAULT_JQL` | `TBD` | Recommended | Helps constrain first-day read checks |
| Read-only flag key | `JIRA_READ_ONLY` | `TBD` | Recommended | Some MCP servers may make read-only implicit instead |
| Extra SSL / intranet flags | none | `TBD` | Environment-dependent | Record cert, proxy, or `NODE_TLS_REJECT_UNAUTHORIZED` style requirements separately |

## Verification seam

The narrow regression seam for this onboarding contract lives in [backend/tests/test_api_mcp_unit.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_api_mcp_unit.py), which now checks that the shipped Jira example config stays disabled, uses a placeholder package, and relies on base URL plus personal token without requiring username auth.
