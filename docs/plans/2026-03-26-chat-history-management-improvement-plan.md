# Chat History Management Improvement Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Address the issues of cluttered chat history interface and difficulty finding relevant conversations by implementing user isolation, search/filter capabilities, and UI optimizations for better organization and discoverability.

**Background:** Currently, all chat sessions are stored globally without user isolation, making it difficult for users to find their own conversations when multiple people share the same instance. Additionally, the chat sidebar shows all sessions without filtering, and long message lists can cause performance and usability issues.

**Architecture:** 
Implement lightweight user isolation through an `owner` field in the Session model, defaulting to a configurable user identifier (environment variable or local storage). Enhance the `/api/chat/history` endpoint with query parameters for filtering by owner, agent, date range, and keyword search. Frontend improvements include virtual scrolling, collapsible messages, session grouping by date, and a search/filter sidebar.

**Success Metrics:**
1. Users can easily find their own conversations among shared history
2. Search and filter functionality reduces time to locate specific sessions
3. UI performance remains smooth with hundreds of sessions/messages
4. User satisfaction with organization features (starring, grouping, etc.)

---

## Phase 1: User Isolation Foundation

### Task 1: Database Schema Migration

**Files:**
- Modify: `backend/app/models/chat.py` (add `owner` field to SessionModel)
- Create: Alembic migration script

- [ ] **Step 1: Add owner field to SessionModel**

Add nullable `owner` column with default value `'default'`:
```python
class SessionModel(Base):
    __tablename__ = "sessions"
    # existing fields...
    owner = Column(String, nullable=False, default='default', index=True)
```

- [ ] **Step 2: Generate Alembic migration**

```bash
cd backend
alembic revision --autogenerate -m "add_owner_to_sessions"
alembic upgrade head
```

- [ ] **Step 3: Update ChatSession Pydantic model**

In `backend/app/services/chat_service.py`, update `ChatSession` class:
```python
class ChatSession(BaseModel):
    # existing fields...
    owner: Optional[str] = 'default'
```

### Task 2: Backend API Filtering

**Files:**
- Modify: `backend/app/api/chat.py` (add query parameters to `/history` endpoint)
- Modify: `backend/app/services/chat_service.py` (update `list_chats` method)

- [ ] **Step 1: Extend list_chats method with filters**

Add parameters to `list_chats`: `owner`, `agent_id`, `from_date`, `to_date`, `search_query`.
Implement SQLAlchemy filtering based on parameters.

- [ ] **Step 2: Update API endpoint**

Modify `/history` endpoint to accept query parameters:
```python
@router.get("/history", response_model=list[ChatSession])
async def list_chats(
    owner: Optional[str] = Query(None, description="Filter by owner"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    from_date: Optional[datetime] = Query(None, description="Start date filter"),
    to_date: Optional[datetime] = Query(None, description="End date filter"),
    search_query: Optional[str] = Query(None, description="Search in message content"),
):
    return chat_service.list_chats(
        owner=owner,
        agent_id=agent_id,
        from_date=from_date,
        to_date=to_date,
        search_query=search_query
    )
```

- [ ] **Step 3: Add owner to new session creation**

When creating new sessions, set owner from request context (e.g., from `X-User-Id` header or default from environment).

### Task 3: Frontend User Identity Management

**Files:**
- Create: `frontend/src/utils/userIdentity.ts`
- Modify: `frontend/src/components/ChatSidebar.tsx` (add user selector)

- [ ] **Step 1: Create user identity utility**

Store current user in localStorage with fallback to environment variable `YUE_USER` or OS username.

- [ ] **Step 2: Add user selector UI**

Add dropdown in ChatSidebar to switch between users (or input field for custom user ID).

- [ ] **Step 3: Pass owner filter to API**

When fetching chat history, include current user as `owner` parameter (optional "Show all" toggle).

---

## Phase 2: Search and Filter Capabilities

### Task 1: Backend Search Implementation

**Files:**
- Modify: `backend/app/services/chat_service.py` (enhance search functionality)

- [ ] **Step 1: Implement message content search**

When `search_query` is provided, join with messages table and filter by content ILIKE.

- [ ] **Step 2: Add full-text search index (optional)**

For better performance, consider adding PostgreSQL full-text search or SQLite FTS5 extension.

### Task 2: Frontend Filter UI

**Files:**
- Modify: `frontend/src/components/ChatSidebar.tsx` (add filter controls)
- Create: `frontend/src/components/ChatFilters.tsx` (optional component)

- [ ] **Step 1: Add search input and filter controls**

Add search bar, agent dropdown, date range picker to ChatSidebar.

- [ ] **Step 2: Implement debounced search**

Use debouncing for search input to avoid excessive API calls.

- [ ] **Step 3: Update chat history fetching**

Modify API calls to include filter parameters from UI state.

---

## Phase 3: UI Optimizations

### Task 1: Virtual Scrolling for Message List

**Files:**
- Modify: `frontend/src/components/MessageList.tsx`
- Install: `solidjs/virtual` (or similar virtual scroll library)

- [ ] **Step 1: Install virtual scroll library**

```bash
cd frontend && npm install @tanstack/solid-virtual
```

- [ ] **Step 2: Implement virtual scrolling**

Replace simple `For` loop with virtual list component to render only visible messages.

### Task 2: Message Collapsing and Summarization

**Files:**
- Modify: `frontend/src/components/MessageItem.tsx`

- [ ] **Step 1: Add expand/collapse toggle for long messages**

For messages exceeding certain length (e.g., 1000 chars), show "Read more"/"Show less" toggle.

- [ ] **Step 2: Implement client-side summarization (optional)**

Use simple text truncation with ellipsis for collapsed state.

### Task 3: Session Grouping and Organization

**Files:**
- Modify: `frontend/src/components/ChatSidebar.tsx`

- [ ] **Step 1: Group sessions by date**

Categorize sessions as "Today", "Yesterday", "Last Week", "Older".

- [ ] **Step 2: Add starring/favoriting feature**

Add star icon to sessions, store favorites in localStorage or backend (requires new field).

- [ ] **Step 3: Add bulk operations**

Checkbox selection for multiple sessions with delete/archive actions.

### Task 4: Sidebar Improvements

**Files:**
- Modify: `frontend/src/components/ChatSidebar.tsx`

- [ ] **Step 1: Resizable sidebar**

Implement drag handle to adjust sidebar width.

- [ ] **Step 2: Collapsible sections**

Allow collapsing of filter section, user list, etc.

---

## Phase 4: Advanced Features (Optional)

### Task 1: Session Tagging

**Files:**
- Modify: `backend/app/models/chat.py` (add tags relationship)
- Create: migration for tags table

- [ ] **Step 1: Design tags schema**

Many-to-many relationship between sessions and tags.

- [ ] **Step 2: Add tag management UI**

Allow adding/removing tags from sessions.

### Task 2: Export Filtered History

**Files:**
- Extend existing export feature

- [ ] **Step 1: Add export option for filtered results**

Export current filtered view as JSON or Markdown.

### Task 3: Session Archival

**Files:**
- Modify: `backend/app/models/chat.py` (add archived flag)

- [ ] **Step 1: Add archival support**

`archived` boolean field to hide older sessions from default view.

---

## Testing Strategy

### Backend Tests
- Unit tests for filtered list_chats with various parameters
- Integration tests for API endpoints with owner filtering
- Migration test for owner field addition

### Frontend Tests
- Component tests for ChatSidebar with filters
- Virtual scrolling performance tests
- User identity persistence tests

### End-to-End Tests
- Playwright tests for search and filter workflows
- Cross-user session isolation verification

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Database migration conflicts | Medium | High | Test migration on backup first; provide rollback script |
| Performance degradation with search | Medium | Medium | Implement pagination; add query optimization indexes |
| Virtual scroll library compatibility | Low | Medium | Choose well-maintained library; have fallback to simple pagination |
| User identity confusion | High | Medium | Clear UI indicators; persistent user selection |

---

## Success Validation

1. **Functional Validation**: 
   - Users can filter sessions by owner, agent, date, and keyword
   - Search returns relevant sessions within acceptable time (< 500ms)
   - Virtual scrolling handles 1000+ messages smoothly

2. **User Experience Validation**:
   - User testing shows reduced time to find specific conversations
   - Positive feedback on organization features

3. **Performance Validation**:
   - Memory usage remains stable with large history
   - API response times within acceptable limits

---

## Appendix: Current Code References

### Backend Models
- Session model: [backend/app/models/chat.py](file:///backend/app/models/chat.py#L18-L45)
- Message model: [backend/app/models/chat.py](file:///backend/app/models/chat.py#L48-L85)
- ChatService: [backend/app/services/chat_service.py](file:///backend/app/services/chat_service.py#L84-L110)

### Frontend Components
- ChatSidebar: [frontend/src/components/ChatSidebar.tsx](file:///frontend/src/components/ChatSidebar.tsx#L1-L50)
- MessageList: [frontend/src/components/MessageList.tsx](file:///frontend/src/components/MessageList.tsx#L1-L50)

### API Endpoints
- GET /api/chat/history: [backend/app/api/chat.py](file:///backend/app/api/chat.py#L285-L289)

---

## Implementation Priority Order

1. Phase 1 (User Isolation Foundation) - **Highest priority**
2. Phase 2 (Search and Filter Capabilities) - **High priority**
3. Phase 3 (UI Optimizations) - **Medium priority**
4. Phase 4 (Advanced Features) - **Low priority**

**Estimated effort**: 2-3 weeks for core features (Phases 1-3) with one developer.

---

> **Note**: This plan assumes the project follows the existing architectural patterns. All file paths are relative to the project root. When implementing, ensure compatibility with existing authentication/authorization patterns if they emerge in the future.