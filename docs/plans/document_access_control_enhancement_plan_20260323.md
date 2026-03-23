# Document Access Control Enhancement Plan (2026-03-23)

## 1. Purpose

This document reviews the current document access-control design in the backend and proposes a safer, more maintainable enhancement plan.

The goal is not to redesign document tooling from scratch. The goal is to make access decisions consistent, centralized, and testable across document search, document read, PDF helpers, Excel helpers, and prompt-time scope disclosure.

Primary code areas reviewed:

1. [`backend/app/services/doc_retrieval.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/doc_retrieval.py)
2. [`backend/app/mcp/builtin/docs.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/builtin/docs.py)
3. [`backend/app/services/config_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/config_service.py)
4. [`backend/app/services/agent_store.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/agent_store.py)
5. [`backend/app/services/chat_prompting.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_prompting.py)
6. [`backend/app/services/excel_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/excel_service.py)

## 2. Current Design Review

### 2.1 What is working well

1. Path traversal is already constrained by realpath and root checks in [`doc_retrieval.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/doc_retrieval.py).
2. Allow and deny roots exist at the config layer in [`config_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/config_service.py).
3. The MCP document tools already route through shared helpers in [`backend/app/mcp/builtin/docs.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/builtin/docs.py), which is a good seam for central enforcement.
4. Excel tools reuse the same path-resolution logic instead of inventing a separate security model in [`excel_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/excel_service.py).
5. Prompt-time scope disclosure is already aware of effective roots in [`chat_prompting.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_prompting.py).

### 2.2 Main design gaps

1. Access control is distributed across several layers instead of being represented by one policy object.
2. `config_service` stores document access settings, but does not express policy decisions or validation rules beyond simple list normalization.
3. `doc_retrieval.py` performs the actual enforcement, but only when callers remember to pass the right allow/deny and agent-root inputs.
4. `doc_file_patterns` are used as file filters, but they are not a complete security boundary on their own.
5. Prompt assembly exposes effective roots, but the disclosure path is separate from the actual authorization path.
6. Different tool families document the same concept in slightly different ways, which raises the risk of inconsistent behavior over time.

### 2.3 Practical risk

The biggest risk is not a single obvious bug. The risk is policy drift:

1. one tool path may remember to apply allow/deny roots
2. another may rely only on agent roots
3. a third may filter by file patterns but not by the same root policy
4. prompt text may show a scope that differs from what the tool layer actually permits

That kind of drift is hard to spot in code review and tends to show up as either accidental overexposure or confusing false denials.

## 3. Proposed Target Design

I recommend introducing a small access-control service with one source of truth for document scope decisions.

### 3.1 New conceptual model

Create a dedicated policy layer that can answer three questions:

1. What roots are effective for this agent and request?
2. Is this path allowed for search/list/read?
3. If not, why was it denied?

Suggested shape:

1. `DocumentAccessPolicy`
2. `DocumentAccessContext`
3. `DocumentAccessDecision`

This policy should own:

1. allow root normalization
2. deny root normalization
3. agent root merging
4. file pattern filtering
5. operation-specific checks for list/search/read/PDF/Excel
6. denial reasons that can be surfaced in tool responses and logs

### 3.2 Recommended file boundaries

I recommend a new module family such as:

```text
backend/app/services/document_access/
├── __init__.py
├── policy.py
├── resolver.py
├── errors.py
└── types.py
```

Suggested responsibilities:

1. `types.py` defines policy input/output models.
2. `errors.py` defines access denial exceptions with stable error codes.
3. `policy.py` performs root, path, and pattern authorization.
4. `resolver.py` computes effective roots for an agent/request.
5. `__init__.py` re-exports the public surface for easy adoption.

`doc_retrieval.py` would remain the execution engine for file walking, reading, and PDF parsing, but it would call the new policy layer instead of reimplementing policy logic inline.

## 4. Enhancement Plan

### Phase 1: Centralize policy logic

1. Add a dedicated document access policy module.
2. Move root normalization, allow/deny resolution, and pattern matching into that module.
3. Keep `doc_retrieval.py` behavior stable by adapting it to the new policy helpers rather than changing tool semantics.
4. Preserve current defaults so callers that do not pass explicit roots still behave as they do today.

Outcome:

1. One source of truth for allowed roots and denied roots.
2. One place to reason about root-versus-path authorization.
3. Easier unit tests for security behavior.

### Phase 2: Make tool entrypoints policy-aware

1. Update [`backend/app/mcp/builtin/docs.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/builtin/docs.py) to consume the new policy layer directly.
2. Make root fallback behavior explicit and consistent across list/search/read/PDF tools.
3. Standardize denied-response payloads so users see the same shape regardless of tool.
4. Ensure citations and audit metadata still work after the refactor.

Outcome:

1. Search and read flows use the same authorization path.
2. Root fallback and denial handling stop being duplicated per tool.
3. Tool responses become easier to test and support.

### Phase 3: Align non-doc tool consumers

1. Update [`backend/app/services/excel_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/excel_service.py) to use the same policy object for Excel path checks.
2. Review any future file-based tool families and route them through the same policy boundary.
3. Keep prompt-scope disclosure in [`chat_prompting.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_prompting.py) aligned with the same effective-root computation.

Outcome:

1. The same document access rules apply across Markdown, PDF, and Excel workflows.
2. The prompt no longer needs to guess at scope semantics.

### Phase 4: Add auditability and admin clarity

1. Emit structured denial reasons for invalid roots, denied paths, and unsupported extensions.
2. Add a simple access-policy inspection view in the config layer if operators need it.
3. Consider a documented "effective scope" payload for debugging and support.

Outcome:

1. Easier incident triage.
2. Better operator visibility into why a path was denied.

## 5. Risk Assessment

### 5.1 Technical risks

1. Root-resolution behavior may change subtly if normalization is moved carelessly.
2. Tool fallback logic may become more opinionated if defaults are centralized without preserving current behavior.
3. PDF and Excel paths may need separate extension rules, even if they share the same root policy.
4. Any change to deny-root precedence could create a security regression.

### 5.2 Behavioral risks

1. Existing agents may rely on current implicit root fallback behavior.
2. Prompt text may change if effective scope disclosure is updated.
3. Users may see more informative errors, which is good, but still a visible behavior change.

### 5.3 Mitigation

1. Preserve the current root fallback order in the first phase.
2. Add regression tests before changing any call sites.
3. Keep compatibility wrappers where necessary during migration.
4. Roll out one tool family at a time.

## 6. Test Strategy

Start with narrow unit coverage, then expand to integration checks.

### 6.1 Unit tests

1. Allow root resolution with absolute and relative paths.
2. Deny root precedence over allow roots.
3. Agent root selection when multiple roots are configured.
4. File pattern include and exclude behavior.
5. Search versus read versus list authorization differences.
6. Symlink and path traversal attempts.
7. Extension-specific enforcement for Markdown, PDF, and Excel.

### 6.2 Integration tests

1. MCP `docs_list` with permitted and denied roots.
2. MCP `docs_search` and `docs_read` with mixed root inputs.
3. PDF helpers using the same policy context.
4. Excel helpers reading only allowed files.
5. Prompt scope summary reflecting the same effective roots as tool execution.

### 6.3 Regression focus

1. No accidental widening of accessible roots.
2. No accidental blocking of the built-in docs and local-docs agents.
3. No regression in citation capture.
4. No regression in existing chat runtime dependency injection.

## 7. Rollout Recommendation

I recommend a two-step rollout:

1. First PR: introduce the policy module and add tests, but keep current public behavior through adapters.
2. Second PR: migrate MCP and Excel callers to the new policy helpers, then simplify `doc_retrieval.py` once the tests are green.

This keeps the security-sensitive behavior isolated and reviewable.

## 8. Recommendation

My recommendation is to treat document access control as a dedicated subsystem, not as a collection of path checks spread across services.

The current design is workable, but it is one refactor away from becoming difficult to reason about. The highest-value next move is to create a shared document policy boundary and migrate all document-facing tools to it incrementally.

## 9. Approval Request

If you want, I can turn this plan into implementation work in phased changes:

1. build the new policy module and tests first
2. wire MCP document tools to it next
3. then align Excel and prompt-scope logic

