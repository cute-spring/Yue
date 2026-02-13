import { describe, it, expect } from 'vitest';
import { renderMath, normalizeMermaidCode, renderMarkdown } from './markdown';

describe('Markdown Utils', () => {
  describe('normalizeMermaidCode', () => {
    it('should remove backticks and mermaid tag', () => {
      const input = '```mermaid\ngraph TD;\nA-->B;\n```';
      expect(normalizeMermaidCode(input)).toBe('graph TD;\nA-->B;');
    });
  });

  describe('renderMath', () => {
    it('should render block math', () => {
      const input = '$$x^2$$';
      expect(renderMath(input)).toContain('katex-display');
    });

    it('should protect code blocks', () => {
      const input = '```\n$$x^2$$\n```';
      expect(renderMath(input)).toBe(input);
    });
  });

  describe('renderMarkdown', () => {
    it('should render basic markdown', () => {
      const input = '# Hello';
      expect(renderMarkdown(input)).toContain('<h1>Hello</h1>');
    });

    it('should render code blocks with highlight.js', () => {
      const input = '```javascript\nconst x = 1;\n```';
      const output = renderMarkdown(input);
      expect(output).toContain('hljs');
      expect(output).toContain('language-javascript');
    });
  });
});
