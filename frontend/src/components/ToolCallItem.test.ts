import { describe, expect, it } from 'vitest';
import { getArgumentEntries, getDownloadArtifact, getScreenshotPreview, isBrowserSnapshotTool, parseToolCallResultPayload } from './ToolCallItem';

describe('ToolCallItem helpers', () => {
  it('parses structured JSON result payloads', () => {
    const payload = parseToolCallResultPayload('{"download_url":"/exports/demo.png"}');
    expect(payload).toEqual({ download_url: '/exports/demo.png' });
  });

  it('extracts screenshot preview metadata for browser_screenshot results', () => {
    const preview = getScreenshotPreview(
      'browser_screenshot',
      JSON.stringify({
        filename: 'demo-shot.png',
        download_url: '/exports/demo-shot.png',
        artifact: { kind: 'screenshot' },
      }),
    );

    expect(preview).toEqual({
      url: '/exports/demo-shot.png',
      alt: 'demo-shot.png',
    });
  });

  it('does not treat non-screenshot results as previewable images', () => {
    const preview = getScreenshotPreview(
      'browser_snapshot',
      JSON.stringify({
        filename: 'page.txt',
        download_url: '/exports/page.txt',
        artifact: { kind: 'document' },
      }),
    );

    expect(preview).toBeNull();
  });

  it('recognizes browser snapshot tools as content-forward artifacts', () => {
    expect(isBrowserSnapshotTool('browser_snapshot')).toBe(true);
    expect(isBrowserSnapshotTool('builtin:browser_snapshot')).toBe(true);
    expect(isBrowserSnapshotTool('generate_pptx')).toBe(false);
  });

  it('extracts downloadable artifacts for non-image exports', () => {
    const artifact = getDownloadArtifact(
      'generate_pptx',
      JSON.stringify({
        filename: 'quarterly-review.pptx',
        download_url: '/exports/quarterly-review.pptx',
      }),
    );

    expect(artifact).toEqual({
      url: '/exports/quarterly-review.pptx',
      filename: 'quarterly-review.pptx',
      kindLabel: 'PPTX',
    });
  });

  it('formats simple tool arguments as key-value entries', () => {
    const entries = getArgumentEntries({
      url: 'https://example.com',
      full_page: true,
      timeout_ms: 3000,
      label: null,
    });

    expect(entries).toEqual([
      { key: 'url', value: 'https://example.com' },
      { key: 'full_page', value: 'true' },
      { key: 'timeout_ms', value: '3000' },
      { key: 'label', value: 'null' },
    ]);
  });

  it('falls back when arguments contain nested structures', () => {
    const entries = getArgumentEntries({
      url: 'https://example.com',
      headers: { accept: 'application/json' },
    });

    expect(entries).toBeNull();
  });
});
