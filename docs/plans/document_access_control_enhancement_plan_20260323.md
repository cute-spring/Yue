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

### 2.4 Current system architecture (detailed)

**Configuration hierarchy** (priority high to low):

1. **Environment variables**: `DOC_ACCESS_ALLOW_ROOTS`, `DOC_ACCESS_DENY_ROOTS`
2. **Config file**: `global_config.json` → `doc_access` section
3. **Defaults**: 
   - `allow_roots`: `["."]` (project root, resolves to `docs/` via `get_docs_root()`)
   - `deny_roots`: OS-dependent system protection

**Default accessible directories**:
```
<project_root>/
├── docs/              # Primary document directory (via get_docs_root())
├── backend/           # Backend code (if in allow_roots)
├── frontend/          # Frontend code (if in allow_roots)
└── data/              # Data directory (if in allow_roots)
```

**Default denied directories** (system-level protection):

- **macOS**: `/System`, `/Library`
- **Linux**: `/etc`, `/proc`, `/sys`, `/dev`
- **User-configurable** (recommended): `.git`, `node_modules`, `.venv`, `__pycache__`, `dist`, `build`

**Access control flow**:
```
User Request (docs_list/search/read)
    ↓
Get Configuration (allow_roots, deny_roots)
    ↓
Path Resolution & Validation
    - resolve_docs_root()
    - resolve_docs_roots_for_search()
    - resolve_docs_root_for_read()
    ↓
Security Checks
    - realpath normalization
    - _is_under() allow check
    - _is_under() deny check
    - Extension filtering (.md, .pdf, .xlsx, etc.)
    ↓
┌──────┴──────┐
↓             ↓
Allow        Deny
Execute      Throw DocAccessError
```

**Existing safeguards**:
- ✅ `realpath` prevents symlink escape
- ✅ System-level denylist auto-protects sensitive directories
- ✅ `commonpath` prevents `../` traversal attacks
- ✅ Fallback mechanism (tries default root if requested root is denied)
- ✅ Test coverage in `test_doc_retrieval.py` for edge cases

### 2.5 Design strengths

1. **Defensive design**:
   - Path normalization with `realpath`
   - Multiple validation layers
   - System-level protection out of the box

2. **Flexibility**:
   - Multiple root support
   - Relative and absolute path support
   - Agent-level `doc_roots` override capability

3. **Error handling**:
   - Fallback to default root on denial
   - User-friendly error messages with suggestions
   - Structured error responses in MCP tools

4. **Test coverage**:
   - Dedicated tests in `test_doc_retrieval.py`
   - Security tests for path traversal and permission denial
   - Edge case validation

### 2.6 Critical gaps requiring immediate attention

1. **Overly permissive default configuration**:
   - Current: `allow_roots: ["."]` allows entire project root
   - Risk: May expose `.env` files (API keys), `global_config.json` (config details), source code files
   - **Recommendation**: Default to `["docs"]` only

2. **No file-level granular control**:
   - Cannot block specific file types (`.env`, `.key`, `.pem`)
   - Cannot block specific files while allowing others in same directory
   - **Recommendation**: Add filename/extension denylist

3. **No audit logging**:
   - No record of which paths were accessed
   - No record of denied attempts
   - No categorization of denial reasons
   - **Recommendation**: Add structured audit logs

4. **Environment variable priority risk**:
   - Setting `DOC_ACCESS_ALLOW_ROOTS=/tmp` overrides safe config file settings
   - **Recommendation**: Document this behavior clearly, consider validation

5. **Missing sensitive file protection**:
   - No explicit blocking of `.env`, `.gitconfig`, private keys, certificates
   - **Recommendation**: Add `DENIED_FILENAMES` and `DENIED_EXTENSIONS` lists

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

### 3.3 Immediate security hardening (Phase 0)

Before the full refactor, implement these critical security improvements:

**1. File-level denylist** (add to `doc_retrieval.py`):

```python
DENIED_FILENAMES = {
    ".env", ".env.local", ".env.production",
    ".gitconfig", ".git-credentials",
    "id_rsa", "id_ed25519", "id_ecdsa",
    ".pem", ".key", ".p12", ".pfx", ".crt"
}

DENIED_EXTENSIONS = {
    ".env", ".key", ".pem", ".p12", ".pfx",
    ".der", ".csr", ".pkcs12", ".gnupg"
}

def _is_filename_allowed(path: str) -> bool:
    """Check if filename and extension are allowed."""
    basename = os.path.basename(path)
    ext = os.path.splitext(path)[1].lower()
    return (basename not in DENIED_FILENAMES 
            and ext not in DENIED_EXTENSIONS)
```

**2. Tighten default configuration** (update `global_config.json.example`):

```json
{
  "doc_access": {
    "allow_roots": ["docs"],
    "deny_roots": [
      "backend/.venv",
      "backend/data",
      "node_modules",
      ".git",
      "__pycache__",
      "dist",
      "build"
    ]
  }
}
```

**3. Add audit logging** (add to policy checks):

```python
logger.info(
    "doc_access_check",
    extra={
        "operation": "read",  # or "list", "search"
        "path": requested_path,
        "allowed": True/False,
        "reason": "under_denied_root",  # or "outside_allow_root", "filename_denied"
        "agent_id": agent_id,
        "timestamp": time.time(),
    }
)
```

**4. Add security mode configuration**:

```json
{
  "doc_access": {
    "security_mode": "strict",  // "strict" | "permissive"
    "allow_roots": ["docs"],
    "deny_file_patterns": ["**/.env", "**/*.key", "**/*.pem"],
    "enable_audit_logging": true
  }
}
```

**Rationale**: These changes provide immediate security improvements while the larger architectural refactor is in progress. They can be implemented incrementally without breaking existing functionality.

## 4. Enhancement Plan

### Phase 0: Immediate security hardening (1-2 days)

**Priority**: CRITICAL - Implement before full refactor

**Deliverables**:

1. **File-level denylist** in `doc_retrieval.py`:
   - Add `DENIED_FILENAMES` and `DENIED_EXTENSIONS` constants
   - Add `_is_filename_allowed()` helper function
   - Integrate checks into `resolve_docs_path()` and related functions
   - Add unit tests for sensitive file blocking

2. **Tighten default configuration**:
   - Update `global_config.json.example` to use `["docs"]` instead of `["."]`
   - Add recommended `deny_roots` for common directories
   - Update `CONFIGURATION.md` documentation with security best practices

3. **Audit logging foundation**:
   - Add structured logging for access checks
   - Log operation type, path, decision, and reason
   - Use JSON logging format for easy parsing

4. **Documentation update**:
   - Document environment variable priority risks
   - Provide security hardening checklist for production deployments
   - Add examples of secure configurations

**Tests**:
- Unit tests for filename/extension blocking
- Integration tests verifying `.env` files cannot be accessed
- Regression tests ensuring existing functionality still works

**Success criteria**:
- `.env` files blocked by default
- Audit logs show access attempts
- Default config follows least-privilege principle

### Phase 1: Centralize policy logic (2-3 days)

1. Add a dedicated document access policy module.
2. Move root normalization, allow/deny resolution, and pattern matching into that module.
3. Keep `doc_retrieval.py` behavior stable by adapting it to the new policy helpers rather than changing tool semantics.
4. Preserve current defaults so callers that do not pass explicit roots still behave as they do today.

Outcome:

1. One source of truth for allowed roots and denied roots.
2. One place to reason about root-versus-path authorization.
3. Easier unit tests for security behavior.

### Phase 2: Make tool entrypoints policy-aware (2-3 days)

1. Update [`backend/app/mcp/builtin/docs.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/builtin/docs.py) to consume the new policy layer directly.
2. Make root fallback behavior explicit and consistent across list/search/read/PDF tools.
3. Standardize denied-response payloads so users see the same shape regardless of tool.
4. Ensure citations and audit metadata still work after the refactor.

Outcome:

1. Search and read flows use the same authorization path.
2. Root fallback and denial handling stop being duplicated per tool.
3. Tool responses become easier to test and support.

### Phase 3: Align non-doc tool consumers (1-2 days)

1. Update [`backend/app/services/excel_service.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/excel_service.py) to use the same policy object for Excel path checks.
2. Review any future file-based tool families and route them through the same policy boundary.
3. Keep prompt-scope disclosure in [`chat_prompting.py`](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/chat_prompting.py) aligned with the same effective-root computation.

Outcome:

1. The same document access rules apply across Markdown, PDF, and Excel workflows.
2. The prompt no longer needs to guess at scope semantics.

### Phase 4: Add auditability and admin clarity (2-3 days)

1. Emit structured denial reasons for invalid roots, denied paths, and unsupported extensions.
2. Add a simple access-policy inspection view in the config layer if operators need it.
3. Consider a documented "effective scope" payload for debugging and support.
4. Implement security mode configuration (`strict` vs `permissive`)
5. Add denial reason categorization for better troubleshooting

Outcome:

1. Easier incident triage.
2. Better operator visibility into why a path was denied.
3. Configurable security levels for different deployment scenarios.

## 5. Risk Assessment

### 5.1 Technical risks

1. Root-resolution behavior may change subtly if normalization is moved carelessly.
2. Tool fallback logic may become more opinionated if defaults are centralized without preserving current behavior.
3. PDF and Excel paths may need separate extension rules, even if they share the same root policy.
4. Any change to deny-root precedence could create a security regression.
5. **Phase 0 specific**: File-level denylist may block legitimate use cases (e.g., `.pem` files for documentation)
6. **Phase 0 specific**: Tighter defaults may break existing workflows that rely on broader access

### 5.2 Behavioral risks

1. Existing agents may rely on current implicit root fallback behavior.
2. Prompt text may change if effective scope disclosure is updated.
3. Users may see more informative errors, which is good, but still a visible behavior change.
4. **Phase 0 specific**: Users may be confused when `.env` files suddenly become inaccessible
5. **Phase 0 specific**: Audit logging may introduce slight performance overhead

### 5.3 Mitigation

1. Preserve the current root fallback order in the first phase.
2. Add regression tests before changing any call sites.
3. Keep compatibility wrappers where necessary during migration.
4. Roll out one tool family at a time.
5. **For Phase 0**:
   - Document breaking changes prominently in release notes
   - Provide migration guide for users who need to access sensitive files
   - Make audit logging configurable (enable/disable via config)
   - Add clear error messages explaining why files are blocked
   - Consider a grace period with warnings before enforcement

### 5.4 Risk matrix

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Policy drift during refactor | Medium | High | Phase 0 hardening, comprehensive tests |
| Breaking existing workflows | Medium | Medium | Clear documentation, migration guide |
| Performance regression | Low | Low | Benchmark before/after, optimize hot paths |
| False sense of security | Low | Medium | Document limitations, defense-in-depth |
| Audit log volume | Medium | Low | Configurable logging, log rotation |

## 6. Test Strategy

Start with narrow unit coverage, then expand to integration checks.

### 6.1 Phase 0 tests (immediate security hardening)

**File-level denylist**:
1. `.env` files are blocked regardless of location
2. Private key files (`.key`, `.pem`, `id_rsa`) are blocked
3. Certificate files are blocked
4. Legitimate files with similar names but different extensions are allowed
5. Error messages clearly explain why file is blocked

**Default configuration**:
1. Default `allow_roots: ["docs"]` prevents access to project root
2. Accessing `../backend/.env` is denied
3. Accessing `../data/global_config.json` is denied
4. Multiple allow roots work correctly

**Audit logging**:
1. Access attempts are logged with correct operation type
2. Denial reasons are categorized correctly
3. Log format is parseable (JSON)
4. Logging can be disabled via configuration

### 6.2 Unit tests (Phase 1-4)

1. Allow root resolution with absolute and relative paths.
2. Deny root precedence over allow roots.
3. Agent root selection when multiple roots are configured.
4. File pattern include and exclude behavior.
5. Search versus read versus list authorization differences.
6. Symlink and path traversal attempts.
7. Extension-specific enforcement for Markdown, PDF, and Excel.
8. Filename denylist enforcement
9. Security mode behavior (strict vs permissive)
10. Audit log generation and categorization

### 6.3 Integration tests

1. MCP `docs_list` with permitted and denied roots.
2. MCP `docs_search` and `docs_read` with mixed root inputs.
3. PDF helpers using the same policy context.
4. Excel helpers reading only allowed files.
5. Prompt scope summary reflecting the same effective roots as tool execution.
6. **Security tests**: Attempting to read `.env` files returns clear error
7. **Security tests**: Path traversal attacks are blocked
8. **Audit tests**: Access logs are generated correctly

### 6.4 Regression focus

1. No accidental widening of accessible roots.
2. No accidental blocking of the built-in docs and local-docs agents.
3. No regression in citation capture.
4. No regression in existing chat runtime dependency injection.
5. **Phase 0**: Existing workflows using `docs/` directory continue to work
6. **Phase 0**: Performance overhead from audit logging is acceptable (<5%)

### 6.5 Security test scenarios

**Attack vectors to test**:
1. Path traversal: `../../../etc/passwd`
2. Symlink attacks: symlink to `/etc/passwd`
3. Null byte injection: `file.md%00.env`
4. Unicode normalization attacks: `file..env`
5. Case sensitivity: `.ENV`, `.Env`
6. Double extensions: `file.txt.env`, `file.env.txt`
7. Absolute path injection: `/etc/passwd`
8. Environment variable override: `DOC_ACCESS_ALLOW_ROOTS=/`

**Expected outcomes**:
- All attack vectors are blocked
- Clear, non-revealing error messages
- Audit logs capture attempt details

## 7. Rollout Recommendation

### 7.1 Phase 0 rollout (immediate - 1-2 days)

**Recommended sequence**:

1. **Day 1 Morning**: Implement file-level denylist
   - Add `DENIED_FILENAMES` and `DENIED_EXTENSIONS` to `doc_retrieval.py`
   - Write unit tests
   - Run existing tests to ensure no regression

2. **Day 1 Afternoon**: Update default configuration
   - Modify `global_config.json.example`
   - Update `CONFIGURATION.md` documentation
   - Test with fresh installation

3. **Day 2 Morning**: Add audit logging
   - Implement structured logging
   - Test log output format
   - Verify performance impact is acceptable

4. **Day 2 Afternoon**: Final testing and documentation
   - Run full test suite
   - Write migration guide
   - Prepare release notes

**Rollout strategy**:
- Merge to main branch
- Update example config in documentation
- Existing installations not affected unless they update config
- Highlight breaking changes in release notes

### 7.2 Phase 1-4 rollout (2-3 weeks)

I recommend a two-step rollout:

1. **First PR** (Phase 1): Introduce the policy module and add tests, but keep current public behavior through adapters.
2. **Second PR** (Phase 2): Migrate MCP and Excel callers to the new policy helpers, then simplify `doc_retrieval.py` once the tests are green.
3. **Third PR** (Phase 3-4): Align remaining consumers and add auditability features.

This keeps the security-sensitive behavior isolated and reviewable.

**Key milestones**:
- Week 1: Phase 0 + Phase 1 complete
- Week 2: Phase 2 complete, all MCP tools migrated
- Week 3: Phase 3-4 complete, full rollout

## 8. Recommendation

My recommendation is to treat document access control as a dedicated subsystem, not as a collection of path checks spread across services.

The current design is workable, but it is one refactor away from becoming difficult to reason about. The highest-value next move is to create a shared document policy boundary and migrate all document-facing tools to it incrementally.

### 8.1 Priority assessment

**Current design rating**: 7/10

**Strengths**:
- ✅ Solid foundation with `realpath` and path traversal protection
- ✅ System-level denylist provides good default security
- ✅ Flexible configuration with environment variable support
- ✅ Good test coverage for core functionality

**Critical gaps**:
- ⚠️ Default configuration too permissive (`allow_roots: ["."]`)
- ⚠️ No file-level protection for sensitive files (`.env`, keys, certs)
- ⚠️ No audit trail for security incidents
- ⚠️ Policy logic distributed across multiple layers

**Recommended actions** (in priority order):

1. **IMMEDIATE (This week)**: Phase 0 - Security hardening
   - File-level denylist
   - Tighter default config
   - Audit logging foundation
   - **Impact**: High security improvement, low risk

2. **SHORT-TERM (Next 2-3 weeks)**: Phase 1-2 - Centralize policy
   - Create `document_access` service module
   - Migrate MCP tools
   - **Impact**: Major maintainability improvement

3. **MEDIUM-TERM (Next month)**: Phase 3-4 - Full alignment
   - Excel service integration
   - Advanced audit features
   - Security mode configuration
   - **Impact**: Enterprise-ready security posture

### 8.2 Implementation approach

**If you have security concerns NOW**:
- Implement Phase 0 immediately (1-2 days)
- Can be done as emergency security patch
- Backward compatible except for config example

**If you prefer methodical approach**:
- Start with Phase 1 (policy module)
- Implement Phase 0 security features within new architecture
- More cohesive, but takes longer (2-3 weeks total)

**My recommendation**: **Do Phase 0 first**, then proceed with Phase 1-4. The security improvements are too important to wait, and they can be implemented safely without breaking the larger refactor.

## 9. Approval Request

If you want, I can turn this plan into implementation work in phased changes:

1. **Phase 0**: Build immediate security hardening (file denylist, tighter defaults, audit logging)
2. **Phase 1**: Build the new policy module and tests
3. **Phase 2**: Wire MCP document tools to it next
4. **Phase 3-4**: Then align Excel and prompt-scope logic, add advanced features

**Estimated total effort**: 3-4 weeks for full implementation
**Phase 0 only**: 1-2 days

Would you like me to:
- **Option A**: Start with Phase 0 (immediate security improvements)?
- **Option B**: Skip to full architectural refactor (Phase 1-4)?
- **Option C**: Create a more detailed implementation plan for a specific phase?

## 10. Appendix: Configuration examples

### 10.1 Development environment (permissive)

```json
{
  "doc_access": {
    "security_mode": "permissive",
    "allow_roots": [".", "docs", "../other-docs"],
    "deny_roots": [
      "node_modules",
      ".git",
      ".venv"
    ],
    "enable_audit_logging": false
  }
}
```

### 10.2 Production environment (strict)

```json
{
  "doc_access": {
    "security_mode": "strict",
    "allow_roots": ["/opt/yue/docs", "/opt/yue/data/documents"],
    "deny_roots": [
      "/opt/yue/backend/.venv",
      "/opt/yue/backend/data",
      "/opt/yue/.git"
    ],
    "deny_file_patterns": [
      "**/.env*",
      "**/*.key",
      "**/*.pem",
      "**/id_rsa*",
      "**/.git/**"
    ],
    "enable_audit_logging": true
  }
}
```

### 10.3 Multi-tenant deployment

```json
{
  "doc_access": {
    "security_mode": "strict",
    "allow_roots": [
      "/tenants/tenant-a/docs",
      "/tenants/tenant-b/docs"
    ],
    "deny_roots": [
      "/tenants/tenant-a/.git",
      "/tenants/tenant-b/.git",
      "/shared"
    ],
    "agent_overrides": {
      "tenant-a-agent": {
        "allow_roots": ["/tenants/tenant-a/docs"]
      },
      "tenant-b-agent": {
        "allow_roots": ["/tenants/tenant-b/docs"]
      }
    },
    "enable_audit_logging": true
  }
}
```

## 11. Appendix: Security checklist

### Before production deployment:

- [ ] `allow_roots` set to minimum necessary directories
- [ ] `deny_roots` includes `.git`, `.venv`, `node_modules`
- [ ] File-level denylist blocks `.env`, `*.key`, `*.pem`
- [ ] Audit logging enabled and logs are being collected
- [ ] Log rotation configured to prevent disk fill
- [ ] Environment variables documented and secured
- [ ] Default configuration updated (not using example file)
- [ ] Security mode set to `strict`
- [ ] Penetration testing performed (path traversal, symlink attacks)
- [ ] Incident response plan documented

### Ongoing maintenance:

- [ ] Review audit logs weekly for suspicious patterns
- [ ] Update denylist when new sensitive file types identified
- [ ] Quarterly security review of access policies
- [ ] Annual penetration testing of document access controls
- [ ] Keep documentation up to date with configuration changes

