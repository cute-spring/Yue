
export interface ParsedResult {
  thought: string | null;
  content: string;
  isThinking: boolean;
}

/**
 * A robust state-machine based parser for reasoning chains.
 * Supports <thought> and <think> tags, including streaming (incomplete tags).
 */
export function parseThoughtAndContent(text: string): ParsedResult {
  if (!text) return { thought: null, content: "", isThinking: false };

  let thought = "";
  let content = "";
  let i = 0;
  let isThinking = false;
  let hasFoundAnyThought = false;
  const n = text.length;

  // Potential tag prefixes to avoid flickering in content
  const tagPrefixes = ["<t", "<th", "<thi", "<thin", "<think", "<thou", "<thoug", "<thought"];

  while (i < n) {
    if (text[i] === '<') {
      const remaining = text.slice(i);
      
      // Check for complete opening tags
      const openMatch = remaining.match(/^<(think|thought)>/i);
      if (openMatch) {
        hasFoundAnyThought = true;
        const fullTag = openMatch[0];
        const tagName = openMatch[1];
        const closeTag = `</${tagName}>`;
        const closeIndex = text.indexOf(closeTag, i + fullTag.length);
        
        if (closeIndex !== -1) {
          // Found complete block
          thought += (thought ? "\n" : "") + text.slice(i + fullTag.length, closeIndex);
          i = closeIndex + closeTag.length;
          continue;
        } else {
          // Streaming: tag opened but not closed
          thought += (thought ? "\n" : "") + text.slice(i + fullTag.length);
          isThinking = true;
          i = n;
          continue;
        }
      }

      // Check for potential incomplete tag at the very end of the string
      const isPotentialTag = tagPrefixes.some(p => p === remaining.toLowerCase() || remaining.toLowerCase().startsWith(p));
      if (isPotentialTag && i + remaining.length === n) {
        // It's a prefix at the end of the string, don't add to content yet
        // We consider this "thinking" as well since we are expecting a tag
        isThinking = true;
        hasFoundAnyThought = true; // Mark as having found thought to ensure thought is at least ""
        break;
      }
    }
    
    content += text[i];
    i++;
  }

  return {
    thought: thought.trim() || (hasFoundAnyThought ? "" : null),
    content: content.trim(),
    isThinking
  };
}
