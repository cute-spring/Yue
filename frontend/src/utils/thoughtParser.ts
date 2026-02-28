
export interface ParsedResult {
  thought: string | null;
  content: string;
  isThinking: boolean;
}

/**
 * A robust state-machine based parser for reasoning chains.
 * Supports <thought>, <think>, [thought], [thinking] tags, including streaming (incomplete tags).
 */
export function parseThoughtAndContent(text: string, isStreaming: boolean = true): ParsedResult {
  if (!text) return { thought: null, content: "", isThinking: false };

  let thought = "";
  let content = "";
  let i = 0;
  let isThinking = false;
  let hasFoundAnyThought = false;
  const n = text.length;

  // Potential reasoning tag prefixes to avoid flickering in content
  // Added support for [thought] and [thinking]
  const allowedTags = [
    "<think>", "<thought>", "</think>", "</thought>",
    "[thought]", "[thinking]", "[/thought]", "[/thinking]"
  ];

  while (i < n) {
    if (text[i] === '<' || text[i] === '[') {
      const remaining = text.slice(i);
      
      // Check for complete opening tags (supports <think>, <thought>, [thought], [thinking])
      const openMatch = remaining.match(/^<(think|thought)>|^\[(thought|thinking)\]/i);
      if (openMatch) {
        hasFoundAnyThought = true;
        const fullTag = openMatch[0];
        const tagName = openMatch[1] || openMatch[2];
        const isBracket = fullTag.startsWith('[');
        const closeTag = isBracket ? `[/${tagName}]` : `</${tagName}>`;
        const closeIndex = text.indexOf(closeTag, i + fullTag.length);
        
        if (closeIndex !== -1) {
          // Found complete block
          thought += (thought ? "\n" : "") + text.slice(i + fullTag.length, closeIndex);
          i = closeIndex + closeTag.length;
          continue;
        } else if (isStreaming) {
          // Streaming: tag opened but not closed
          thought += (thought ? "\n" : "") + text.slice(i + fullTag.length);
          isThinking = true;
          i = n;
          continue;
        }
      }

      // Check for potential incomplete tag at the very end of the string
      // ONLY if we are still streaming. If not streaming, treat as regular text.
      if (isStreaming) {
        const isPotentialTag = allowedTags.some(tag => tag.startsWith(remaining.toLowerCase()));
        if (isPotentialTag && i + remaining.length === n) {
          // It's a prefix at the end of the string, don't add to content yet
          isThinking = true;
          hasFoundAnyThought = true;
          break;
        }
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

/**
 * Adapter Pattern: Standardizes thought data from various sources (structured or embedded).
 */
export function getAdaptedThought(msg: { content: string; thought?: string }, isTyping: boolean) {
  // 1. If structured thought exists, it takes precedence
  if (msg.thought !== undefined && msg.thought !== null) {
    return {
      thought: msg.thought,
      content: msg.content,
      isThinking: isTyping && !msg.content, // Usually structured means it's still thinking if content hasn't started
      source: 'structured' as const
    };
  }

  // 2. Fallback to parsing content
  const parsed = parseThoughtAndContent(msg.content, isTyping);
  return {
    ...parsed,
    source: 'embedded' as const
  };
}
