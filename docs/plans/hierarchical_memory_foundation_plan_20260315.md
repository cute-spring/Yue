# Hierarchical Memory Foundation (Short-Term + Long-Term) Execution Plan

## 1. Background & Goals (P0-5)

### 1.1 Background
Currently, the chat system relies on fixed-window history or basic token-aware truncation. As sessions grow, context loss occurs, leading to "reasoning drift" and repetitive user corrections. Cross-session continuity is also missing, as the agent forgets user preferences and project-specific facts between chats.

### 1.2 Goals
Establish a production-safe memory foundation that combines immediate context awareness with durable fact retention:
1. **Short-Term Memory (STM)**: Maintain a rolling summary and key facts for the active session to protect the token budget and maintain reasoning quality.
2. **Long-Term Memory (LTM)**: Persist durable facts, preferences, and project context across sessions.
3. **Memory Governance**: Implement strict write/read policies to prevent hallucinated facts from polluting the memory store.

### 1.3 Success Criteria
1. **Lower Context-Loss Rate**: Measured by reduced "I don't remember" responses in long sessions.
2. **Cross-Session Continuity**: Agent recalls core user preferences from previous sessions.
3. **Auditable Writes**: Every memory write has a provenance (source message/session) and confidence score.
4. **Stable Performance**: Retrieval latency for LTM remains < 100ms for P95.

---

## 2. Memory Architecture

### 2.1 Short-Term Memory (STM)
- **Mechanism**: Rolling summary + Turn-level Key Facts.
- **Trigger**: When session context exceeds 20k tokens.
- **Output**: A structured summary block injected into the system prompt.

### 2.2 Long-Term Memory (LTM)
- **Mechanism**: SQLite-based fact store with Vector Search (optional/future) or Keyword-based retrieval.
- **Schema**:
  - `memory_id`: UUID
  - `category`: Fact, Preference, ProjectContext
  - `content`: Text content
  - `confidence`: 0.0 - 1.0
  - `provenance`: message_id or session_id
  - `decay_score`: Importance factor (decays over time if not referenced)
  - `last_referenced_at`: Timestamp

---

## 3. Phased Implementation

### Phase 1: Short-Term Rolling Summary (MVP)
- Implement `backend/app/services/memory/stm_service.py`.
- Add summarization logic using the current provider's "fast" model (e.g., GPT-4o-mini or DeepSeek-V3).
- Wire STM into the `chat_service.py` context assembly.

### Phase 2: Long-Term Memory Schema & Persistence
- Create `backend/app/models/memory.py` (SQLAlchemy).
- Implement `backend/app/services/memory/ltm_service.py` for CRUD operations.
- Add manual memory management UI in Settings (view/delete memories).

### Phase 3: Retrieval & Decay Policy
- Implement relevance-based retrieval (Scoring = Semantic Similarity * Importance * Decay).
- Add "forgetting" logic: automatically archive or delete low-confidence, low-relevance memories.

### Phase 4: Memory Governance (Write/Read Policy)
- **Write Policy**: Only store facts with confidence > 0.8. Require citation for every stored fact.
- **Read Policy**: Limit retrieval to Top-3 most relevant memories per turn to save context tokens.

---

## 4. Governance & Safety

- **Privacy**: No PII (Personally Identifiable Information) in LTM without explicit user consent.
- **Reversibility**: Users can clear STM or LTM at any time.
- **Bias Mitigation**: Regularly audit memory for biased or hallucinated patterns.

---

## 6. Comparison with Mem0 Open Source Framework

To ensure the technical path chosen for Yue is optimal, we compared this hierarchical memory plan with the leading open-source memory framework **Mem0**.

### 6.1 Feature Comparison Table

| Feature | Mem0 (Open Source) | Yue Hierarchical Memory (Local Plan) |
| :--- | :--- | :--- |
| **Complexity** | High (Full framework, multi-component) | Low to Medium (Service-based, integrated) |
| **Architecture** | Client-Server / SDK, Hybrid (Vector + SQL) | Integrated Service, SQLite-centric |
| **Memory Extraction** | LLM-based, built-in conflict resolution | LLM-based, confidence & citation-driven |
| **Short-Term Memory** | Basic rolling context | Rolling summary + key facts (token-aware trigger) |
| **Long-Term Memory** | Semantic/Vector + Graph (Mem0-G) | Keyword/Vector (future) + SQLite Fact Store |
| **Governance** | Metadata, multi-user scoping | Confidence scores, provenance, decay, PII rules |
| **Infrastructure** | Requires Vector DB (Qdrant/LanceDB) | Zero extra infra (re-uses project SQLite) |
| **Performance** | Scalable, async-by-default | Integrated, target < 100ms P95 latency |

### 6.2 Why Yue Chose the Local Plan over Mem0

1. **Infrastructure Simplicity**: Mem0 typically requires a separate vector database (like Qdrant or LanceDB) to be fully functional. Yue's local plan leverages the existing SQLite infrastructure, reducing operational overhead for self-hosted users.
2. **Governance & Safety**: The local plan prioritizes "Auditable Writes" with explicit confidence scores (>0.8) and mandatory citations for every stored fact. This level of strict governance is easier to enforce within a custom-built service than by wrapping a generic framework.
3. **Token Efficiency**: Yue's STM (Short-Term Memory) specifically includes a token-aware rolling summary (triggering at 20k tokens), which is highly optimized for the project's specific chat context management needs.
4. **Integration Depth**: By building the `stm_service.py` and `ltm_service.py` directly into the `backend/app/services/memory/` package, we ensure seamless integration with the existing `chat_service.py` and `model_factory.py` without introducing external API dependencies.

### 6.3 Potential Future Integration
While the MVP will follow the local plan, we remain open to integrating Mem0's **Graph Memory (Mem0-G)** concepts in Phase 4 if complex relational reasoning between memories becomes a core requirement.

### 6.4 Typical Scenarios for Using Mem0
- **Long-Lived Personal Assistants**: Assistants that interact with users across days or weeks and must remember stable preferences, recurring goals, and historical decisions.
- **Customer Support Agents**: Service bots that benefit from recalling prior tickets, troubleshooting steps, and account-specific context to reduce repeated questioning.
- **Sales and Success Copilots**: Agents that maintain customer profiles, communication preferences, and follow-up milestones to improve continuity and conversion outcomes.
- **Enterprise Knowledge Assistants**: Internal copilots that persist team terminology, project conventions, and workflow patterns across sessions.
- **Multi-Agent Collaboration Systems**: Architectures where multiple agents need shared long-term memory to coordinate tasks without repeatedly rebuilding context from scratch.

### 6.5 Benefits Mem0 Typically Delivers in Those Scenarios
- **Cross-Session Continuity**: Preserves important user and project context beyond a single chat window.
- **Lower Token Cost**: Replaces full-history prompt stuffing with memory retrieval, improving token efficiency for long conversations.
- **Higher Personalization Quality**: Improves recommendations and response style alignment by retaining durable preferences.
- **Better Response Consistency**: Reduces contradictory answers by grounding responses in persisted memory.
- **Scalable Memory Layering**: Supports gradual upgrades (rerank, graph memory, advanced retrieval) as product requirements evolve.

### 6.6 Yue Rollout Recommendation: What to Adopt First vs Keep Local
- **Adopt Mem0 First (High ROI Modules)**:
  - Cross-session user preference memory (tone/style, recurring preferences, durable personal settings).
  - Customer/project profile memory shared across sessions and agents.
  - Multi-agent shared memory retrieval where coordination value is high and repeated context rebuild is costly.
- **Keep Local Strategy First (Current Yue Strengths)**:
  - In-session STM rolling summary pipeline already integrated with `chat_service.py` and token budget controls.
  - Governance-critical writes requiring strict confidence threshold and citation gating before persistence.
  - Local-only or compliance-sensitive deployments that prioritize minimal infrastructure and SQLite-first operations.
- **Recommended Hybrid Path for Current Stage**:
  - Phase A: Keep STM local, pilot Mem0 only for non-sensitive preference memory in one bounded workflow.
  - Phase B: Add retrieval quality monitoring (precision/recall on memory hits, contradiction rate, latency P95) and compare against local baseline.
  - Phase C: Expand Mem0 scope to shared project memory if quality and latency targets are consistently met.
  - Phase D: Keep an explicit fallback switch to local retrieval for fail-open behavior during incidents.

---

## 7. Immediate Next Actions
1. Initialize `backend/app/services/memory/` package.
2. Define the SQLite schema for LTM.
3. Implement the first version of the rolling summary trigger in `chat_service.py`.
