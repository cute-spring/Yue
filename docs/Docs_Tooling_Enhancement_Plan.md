# Docs Tooling Enhancement Plan

This document analyzes the current design and implementation of [docs.py](file:///./backend/app/mcp/builtin/docs.py) and provides recommendations for further enhancement, including a comparison with the general-purpose [exec.py](file:///./backend/app/mcp/builtin/exec.py).

## **Analysis of Current Implementation**

The [docs.py](file:///./backend/app/mcp/builtin/docs.py) script implements a suite of MCP tools for listing, searching, and reading documents (Markdown and PDF). It leverages the `doc_retrieval` service for core logic and integrates with the project's configuration and citation systems.

### **Comparison with [exec.py](file:///./backend/app/mcp/builtin/exec.py)**

While [exec.py](file:///./backend/app/mcp/builtin/exec.py) provides a flexible way to run shell commands (like `ls`, `grep`, or `cat`), [docs.py](file:///./backend/app/mcp/builtin/docs.py) is a specialized "Document Agent" toolset that offers several advantages:

| Feature | `docs.py` (Specialized) | `exec.py` (General Shell) |
| :--- | :--- | :--- |
| **Citations** | Automatically appends sources to `ctx.deps["citations"]` for traceable AI responses. | Returns raw text only; no context-aware tracking. |
| **PDF Support** | Built-in PDF searching and page-based reading using `pypdf`. | Requires external CLI tools (e.g., `pdftotext`) and manual parsing. |
| **Smart Snippets** | Uses density-based clustering to extract the most relevant sections of text. | Returns raw lines (e.g., `grep` output), which may lack surrounding context. |
| **Security** | Restricted to specific `doc_roots` with strict path resolution. | Broad shell access, requiring complex regex guards for security. |
| **Structured Data** | Returns JSON for listing and metadata, optimized for LLM consumption. | Returns raw console output (stdout/stderr). |
| **Noise Filtering** | Automatically skips `node_modules`, `venv`, and hidden files. | Requires manual flags (e.g., `ls -A --exclude=...`) in every command. |

**Conclusion**: Retaining [docs.py](file:///./backend/app/mcp/builtin/docs.py) is **essential**. It provides a high-level, safe, and context-aware interface for RAG (Retrieval-Augmented Generation) tasks that [exec.py](file:///./backend/app/mcp/builtin/exec.py) cannot easily or safely replicate.

### **Strengths**
- **Modular Design**: Each tool is implemented as a separate class inheriting from `BaseTool`.
- **Rich Feature Set**: Covers file listing, keyword search (with Ripgrep support), content reading, metadata inspection, and specialized PDF handling.
- **Context Awareness**: Correctly uses `RunContext` to access dependencies like `doc_roots` and `citations`.
- **Security Baseline**: Integrates with `config_service` for allow/deny root path enforcement.

### **Identified Weaknesses & Opportunities**
1.  **Code Redundancy**: The logic to extract `doc_roots`, `file_patterns`, and `citations` from `ctx.deps` and setting up access control via `_get_doc_access()` is duplicated in almost every tool's `execute` method.
2.  **Implicit Error Handling**: Tools rely on `doc_retrieval` to raise exceptions (like `DocAccessError`). These aren't explicitly caught in the tool layer, which might lead to unhelpful error messages for the LLM or end-user.
3.  **Fragile Dependency Access**: Accessing `ctx.deps` via `getattr(ctx, "deps", None)` and manual dictionary lookups lacks type safety and is prone to runtime errors.
4.  **Low Observability**: There is minimal logging of tool entry points, input parameters, or access control rejections.
5.  **Schema Hardcoding**: Tool parameters are defined as raw dictionaries, which is harder to maintain and validate compared to structured models (like Pydantic).

---

## **Recommended Enhancement Suggestions**

### **1. Architectural Refactoring**
- **Introduce `DocsBaseTool`**: Create a specialized base class for documentation tools. This base class should handle:
    - Common dependency resolution (extracting `doc_roots`, `file_patterns`, `citations`).
    - Standardized access control setup.
    - Unified error handling and formatting.
- **Helper for Dependency Extraction**: Encapsulate the logic to parse `RunContext` into a dedicated helper function or property within the base class.

### **2. Robustness & Security**
- **Explicit Exception Handling**: Wrap the `execute` logic in try-except blocks. Catch specific exceptions like `DocAccessError`, `FileNotFoundError`, and `ValueError`, and return them as structured, descriptive strings to the LLM.
- **Input Sanitization**: Add lightweight validation for `root_dir` and `path` arguments before passing them to the service layer.

### **3. Observability & Maintainability**
- **Structured Logging**: Use the `logger` to record tool calls, including the `requested_root` or `path`, and any security-related denials.
- **Comprehensive Type Hinting**: Improve type annotations for `ctx.deps` and other internal variables to leverage IDE static analysis.
- **Enhanced Docstrings**: Add detailed class-level and method-level docstrings following a consistent standard (e.g., Google or NumPy style).

### **4. Functional Improvements**
- **Search Result Diversification**: In `DocsSearchTool`, if multiple roots are provided, ensure results are fairly distributed across them to avoid one root dominating the hits.
- **PDF Extraction Optimization**: Consider making `max_pages_per_file` and `timeout_s` more adaptive based on the total number of files being searched.

### **5. Additional High-Value Improvements**
### **5. Additional High-Value Improvements (Optional, Avoid Over-Design)**
- **Centralized Response Shaping (Incremental)**: Normalize outputs only where compatibility is guaranteed.
- **Typed Dependency Container (Lightweight)**: Start with Protocol or minimal type assertions rather than full refactors.
- **Budgeted Execution (Configurable)**: Add caps with defaults tuned to avoid false negatives in large repos.
- **Unified Path Policy (Targeted)**: Consolidate only the duplicated allow/deny and ignore logic.
- **Configurable Ignore Patterns (Small Scope)**: Add optional config-driven ignores; keep current defaults.
- **Pagination & Streaming (Optional)**: Provide pagination behind a flag or additional parameter.
- **Metrics Hooks (If Pipeline Exists)**: Emit metrics only if the system already collects them.
- **Cache Shortcuts (Short TTL)**: Cache only for stable inputs and ensure quick invalidation.

---

## **ROI Summary**
- **Higher Answer Quality**: Response shaping and diversified search reduce noise and improve relevance.
- **Lower Operational Risk**: Unified path policy, budgets, and typed deps reduce errors and unsafe access.
- **Better Performance**: Caching and pagination cut latency and memory pressure in large repos.
- **Improved Maintainability**: Centralized policies and typed deps reduce duplication and regression risk.
- **Operational Visibility**: Metrics hooks enable monitoring and faster incident response.

---

## **Review & Adjustments (Avoid Over-Design)**
- **Compatibility First**: Any output format changes must be backward-compatible and staged.
- **Prefer Minimal Type Safety**: Use Protocol or small typed helpers before heavy refactors.
- **Config Before Code**: Limits, ignores, and tuning knobs should be configurable, not hardcoded.
- **Optional Capabilities**: Pagination, metrics, and caching should be opt-in unless proven necessary.
- **Scope Control**: Do not introduce new layers unless they remove existing duplication.

---

## **Detailed Improvement Steps**

### **Step 1: DocsBaseTool and dependency resolution**
1. Create `DocsBaseTool` to host common dependency extraction and access control setup.
2. Implement `_resolve_deps(ctx)` returning `doc_roots`, `file_patterns`, `citations`, and `doc_access`.
3. Refactor existing tools to inherit from `DocsBaseTool` with no behavior changes.

### **Step 2: Unified error handling**
1. Add a shared `execute` wrapper or helper to catch `DocAccessError`, `FileNotFoundError`, and `ValueError`.
2. Map exceptions to consistent, user-readable error strings without changing success payloads.

### **Step 3: Targeted validation**
1. Validate `root_dir` and `path` are strings and not empty.
2. Validate provided root exists in `doc_roots` before passing to retrieval.

### **Step 4: Logging improvements**
1. Log tool entry with tool name and sanitized inputs.
2. Log access denials and exceptions with reason codes.

### **Step 5: Optional improvements (only if needed)**
1. Add configurable ignore patterns from config.
2. Add search result diversification across roots.
3. Add optional pagination parameters for list/search.

---

## **Test Plan**

### **Unit Tests**
1. `_resolve_deps` returns expected defaults when `ctx.deps` is empty.
2. `_resolve_deps` honors `doc_roots`, `file_patterns`, and `citations` from deps.
3. Validation rejects empty or unknown `root_dir` and returns a clear error message.
4. Error mapping converts `DocAccessError` into the standardized access-denied response.

### **Integration Tests**
1. `DocsListTool` lists only files under allowed roots.
2. `DocsSearchTool` returns results for a known keyword and includes citations.
3. `DocsReadTool` returns a snippet from a known file and rejects disallowed paths.
4. PDF search/read succeeds on a sample PDF and respects page limits.

### **Regression Checks**
1. Existing API schemas unchanged for successful responses.
2. Citations appended exactly once per successful call.
3. No new logs emitted for empty/no-op calls unless errors occur.

---

## **Implementation Plan**

### **Phase 1: Foundation (Structural)**
1.  Define `DocsBaseTool(BaseTool)` in [docs.py](file:///./backend/app/mcp/builtin/docs.py).
2.  Implement a `_resolve_deps(self, ctx: RunContext)` method in the base class to handle all dependency extraction.
3.  Refactor existing tools (`DocsListTool`, `DocsSearchTool`, etc.) to inherit from `DocsBaseTool`.

### **Phase 2: Reliability (Error Handling & Logging)**
1.  Implement a standardized `execute` wrapper in the base class (or a common helper) that provides consistent try-except-logging logic.
2.  Ensure `DocAccessError` is caught and translated into a user-friendly "Access Denied" message.

### **Phase 3: Refinement (Validation & Docs)**
1.  Add input validation for all tool arguments.
2.  Update all docstrings for clarity and completeness.
3.  Verify that citation appending remains robust after refactoring.

---

*Analysis performed on 2026-03-02 by AI Assistant.*
