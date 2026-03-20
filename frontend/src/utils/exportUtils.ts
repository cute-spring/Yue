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
