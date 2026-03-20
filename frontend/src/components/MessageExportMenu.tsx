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
        disabled={isExporting()}
        class="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-primary/10 hover:text-primary text-text-primary text-sm font-medium transition-colors text-left disabled:opacity-50"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
        Markdown (MD)
      </button>
      
      <button 
        onClick={() => handleServerExport('pdf')}
        disabled={isExporting()}
        class="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-primary/10 hover:text-primary text-text-primary text-sm font-medium transition-colors text-left disabled:opacity-50"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>
        PDF Document
      </button>

      <button 
        onClick={() => handleServerExport('docx')}
        disabled={isExporting()}
        class="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-primary/10 hover:text-primary text-text-primary text-sm font-medium transition-colors text-left disabled:opacity-50"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
        Word (DOCX)
      </button>

      <button 
        onClick={() => handleServerExport('txt')}
        disabled={isExporting()}
        class="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-primary/10 hover:text-primary text-text-primary text-sm font-medium transition-colors text-left disabled:opacity-50"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
        Text (TXT)
      </button>
    </div>
  );
}
