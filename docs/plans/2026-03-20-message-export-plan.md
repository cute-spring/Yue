# Message Export Feature Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a Doubao-style message export feature allowing users to download AI answers as a styled Long Image (PNG) or raw Markdown (TXT/MD) via client-side processing, and eventually expand to Server-Side PDF/Word.

**Architecture:** 
A hybrid approach where fast, visual exports (Image/Markdown) are handled entirely on the client side to avoid server overhead and ensure immediate response. We will use `html-to-image` for capturing the SolidJS `MessageItem` DOM node with our custom Emerald theme styling, and standard Blob downloads for Markdown. The frontend will include an Export Modal triggered from the existing message toolbar.

**Tech Stack:** 
- Frontend: SolidJS, TailwindCSS, `html-to-image` (needs to be installed)
- Utilities: Browser Blob API for Markdown export

---

## Chunk 1: Frontend Dependencies and Utilities Setup

### Task 1: Install `html-to-image` dependency

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install html-to-image**

Run: `cd frontend && npm install html-to-image`
Expected: Success, `package.json` updated with `html-to-image` dependency.

- [ ] **Step 2: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore(frontend): add html-to-image for message export"
```

### Task 2: Create Export Utilities

**Files:**
- Create: `frontend/src/utils/exportUtils.ts`

- [ ] **Step 1: Write export utilities for Markdown and Image**

```typescript
import { toPng } from 'html-to-image';

export const downloadMarkdown = (content: string, filename: string = 'message.md') => {
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

export const downloadMessageAsImage = async (
  elementId: string, 
  filename: string = 'message.png'
): Promise<boolean> => {
  try {
    const node = document.getElementById(elementId);
    if (!node) throw new Error('Message element not found');

    // Add a temporary wrapper class or inline styles if needed for the export
    const originalBg = node.style.backgroundColor;
    node.style.backgroundColor = 'var(--surface)'; // Ensure background is solid

    const dataUrl = await toPng(node, {
      quality: 0.95,
      pixelRatio: 2, // High DPI
      style: {
        margin: '0',
        padding: '20px',
        borderRadius: '0px',
        boxShadow: 'none'
      }
    });

    node.style.backgroundColor = originalBg;

    const link = document.createElement('a');
    link.href = dataUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    return true;
  } catch (error) {
    console.error('Failed to export image:', error);
    return false;
  }
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/utils/exportUtils.ts
git commit -m "feat(frontend): add markdown and image export utilities"
```

---

## Chunk 2: UI Integration

### Task 3: Create Export Menu Component

**Files:**
- Create: `frontend/src/components/MessageExportMenu.tsx`

- [ ] **Step 1: Implement the Export Menu Popup**

```typescript
import { createSignal, Show, onCleanup, onMount } from 'solid-js';
import { downloadMarkdown, downloadMessageAsImage } from '../utils/exportUtils';
import { useToast } from '../context/ToastContext';

interface Props {
  content: string;
  messageId: string;
  onClose: () => void;
  position: { x: number, y: number };
}

export default function MessageExportMenu(props: Props) {
  const [isExporting, setIsExporting] = createSignal(false);
  const toast = useToast();

  let menuRef: HTMLDivElement | undefined;

  const handleClickOutside = (e: MouseEvent) => {
    if (menuRef && !menuRef.contains(e.target as Node)) {
      props.onClose();
    }
  };

  onMount(() => {
    document.addEventListener('mousedown', handleClickOutside);
  });

  onCleanup(() => {
    document.removeEventListener('mousedown', handleClickOutside);
  });

  const handleExportImage = async () => {
    setIsExporting(true);
    const success = await downloadMessageAsImage(props.messageId, `yue-answer-${Date.now()}.png`);
    setIsExporting(false);
    
    if (success) {
      toast.showToast('Message exported as Image', 'success');
    } else {
      toast.showToast('Failed to export image', 'error');
    }
    props.onClose();
  };

  const handleExportMarkdown = () => {
    downloadMarkdown(props.content, `yue-answer-${Date.now()}.md`);
    toast.showToast('Message exported as Markdown', 'success');
    props.onClose();
  };

  return (
    <div 
      ref={menuRef}
      class="fixed z-50 bg-surface-elevated border border-border shadow-xl rounded-xl p-2 w-48 flex flex-col gap-1"
      style={{ top: `${props.position.y}px`, left: `${props.position.x}px` }}
    >
      <div class="text-xs font-bold text-text-secondary px-2 py-1 uppercase tracking-wider">Export As</div>
      
      <button 
        onClick={handleExportImage}
        disabled={isExporting()}
        class="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-primary/10 hover:text-primary text-text-primary text-sm font-medium transition-colors text-left disabled:opacity-50"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
        {isExporting() ? 'Exporting...' : 'Long Image (PNG)'}
      </button>

      <button 
        onClick={handleExportMarkdown}
        class="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-primary/10 hover:text-primary text-text-primary text-sm font-medium transition-colors text-left"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
        Markdown (MD)
      </button>
      
      {/* Placeholders for future server-side exports */}
      <button disabled class="flex items-center gap-2 px-3 py-2 rounded-lg text-text-secondary/40 text-sm font-medium text-left cursor-not-allowed" title="Coming soon">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>
        PDF Document
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/MessageExportMenu.tsx
git commit -m "feat(frontend): create export menu component"
```

### Task 4: Hook up Export Menu to MessageItem

**Files:**
- Modify: `frontend/src/components/MessageItem.tsx`

- [ ] **Step 1: Add ID to message container and implement export button click handler**

Add a unique ID to the message container div:
```typescript
<div id={`message-container-${props.index}`} class={`group relative max-w-[85%] lg:max-w-[75%] ...`}>
```

Update the existing Download button:
```typescript
const [exportMenuPos, setExportMenuPos] = createSignal<{x: number, y: number} | null>(null);

const handleExportClick = (e: MouseEvent) => {
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
  setExportMenuPos({ x: rect.left, y: rect.bottom + 8 });
};

// Inside the button list:
<button 
  class="p-1.5 text-text-secondary/40 hover:text-primary hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition-all" 
  title="Download/Export"
  onClick={handleExportClick}
>
  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
  </svg>
</button>

<Show when={exportMenuPos()}>
  <MessageExportMenu 
    content={props.msg.content}
    messageId={`message-container-${props.index}`}
    position={exportMenuPos()!}
    onClose={() => setExportMenuPos(null)}
  />
</Show>
```
*(Remember to import `MessageExportMenu`)*

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/MessageItem.tsx
git commit -m "feat(frontend): hook up export menu to message toolbar"
```

---

## Future Enhancements (Not in this chunk)
- Server-side generation using `Playwright` or `weasyprint` mapped to a new `/api/export` endpoint.
- PDF and Word Document generation using `python-docx` and `fpdf2`/`reportlab`.

---

## Chunk 3: Backend Export Endpoints (PDF, DOCX, TXT)

### Task 5: Add Backend Dependencies

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: Add python-docx and Markdown/PDF libraries**

Add the following to dependencies:
```toml
    "python-docx",
    "markdown",
    "weasyprint",
```

- [ ] **Step 2: Install dependencies**

Run: `cd backend && uv sync`
Expected: Success

- [ ] **Step 3: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock
git commit -m "chore(backend): add python-docx and weasyprint for document export"
```

### Task 6: Create Export Service

**Files:**
- Create: `backend/app/services/export_service.py`
- Test: `backend/tests/test_export_service.py`

- [ ] **Step 1: Write export logic for PDF, DOCX, and TXT**

```python
import os
import tempfile
from docx import Document
import markdown
from weasyprint import HTML

class ExportService:
    @staticmethod
    def export_to_txt(content: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    @staticmethod
    def export_to_docx(content: str) -> str:
        doc = Document()
        doc.add_paragraph(content) # Note: For production, we'd want a markdown-to-docx converter
        
        fd, path = tempfile.mkstemp(suffix=".docx")
        os.close(fd)
        doc.save(path)
        return path

    @staticmethod
    def export_to_pdf(content: str) -> str:
        html_content = markdown.markdown(content)
        styled_html = f"<html><head><style>body {{ font-family: sans-serif; line-height: 1.6; padding: 2em; }} pre {{ background: #f4f4f4; padding: 1em; }}</style></head><body>{html_content}</body></html>"
        
        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        
        HTML(string=styled_html).write_pdf(path)
        return path
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/export_service.py
git commit -m "feat(backend): implement document export service"
```

### Task 7: Create Export API Endpoint

**Files:**
- Modify: `backend/app/main.py` or create `backend/app/api/export.py`

- [ ] **Step 1: Add the endpoint**

```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.services.export_service import ExportService
import os
import background_tasks # hypothetical

router = APIRouter()

class ExportRequest(BaseModel):
    content: str
    format: str # 'pdf', 'docx', 'txt'

@router.post("/api/export")
async def export_message(req: ExportRequest):
    if req.format == 'pdf':
        path = ExportService.export_to_pdf(req.content)
        media_type = 'application/pdf'
        filename = 'export.pdf'
    elif req.format == 'docx':
        path = ExportService.export_to_docx(req.content)
        media_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        filename = 'export.docx'
    elif req.format == 'txt':
        path = ExportService.export_to_txt(req.content)
        media_type = 'text/plain'
        filename = 'export.txt'
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")

    return FileResponse(
        path=path, 
        media_type=media_type, 
        filename=filename,
        # Background task to delete the temp file after sending
    )
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/export.py backend/app/main.py
git commit -m "feat(backend): add /api/export endpoint for documents"
```

---

## Chunk 4: Frontend Server-Side Export Integration

### Task 8: Update Frontend Export Menu

**Files:**
- Modify: `frontend/src/components/MessageExportMenu.tsx`

- [ ] **Step 1: Hook up PDF, DOCX, and TXT buttons**

Add logic to call `/api/export`:
```typescript
  const handleServerExport = async (format: 'pdf' | 'docx' | 'txt') => {
    setIsExporting(true);
    try {
      const res = await fetch('/api/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: props.content, format })
      });
      
      if (!res.ok) throw new Error('Export failed');
      
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `yue-answer-${Date.now()}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
      toast.showToast(`Message exported as ${format.toUpperCase()}`, 'success');
    } catch (e) {
      toast.showToast('Failed to export document', 'error');
    } finally {
      setIsExporting(false);
      props.onClose();
    }
  };
```
And replace the placeholders with active buttons.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/MessageExportMenu.tsx
git commit -m "feat(frontend): integrate server-side pdf/docx/txt export"
```