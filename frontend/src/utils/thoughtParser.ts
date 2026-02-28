
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
  let hasContentStarted = false; // NEW: Track if we've started receiving actual content
  const n = text.length;

  const allowedTags = [
    "<think>", "<thought>", "</think>", "</thought>",
    "[thought]", "[thinking]", "[/thought]", "[/thinking]"
  ];

  while (i < n) {
    // Check for potential reasoning tags ONLY IF content hasn't started yet
    // This distinguishes between "Protocol Tags" and "Content Examples"
    if (!hasContentStarted && (text[i] === '<' || text[i] === '[')) {
      const remaining = text.slice(i);
      
      const openMatch = remaining.match(/^<(think|thought)>|^\[(thought|thinking)\]/i);
      if (openMatch) {
        hasFoundAnyThought = true;
        const fullTag = openMatch[0];
        const tagName = openMatch[1] || openMatch[2];
        const isBracket = fullTag.startsWith('[');
        const closeTag = isBracket ? `[/${tagName}]` : `</${tagName}>`;
        const closeIndex = text.indexOf(closeTag, i + fullTag.length);
        
        if (closeIndex !== -1) {
          thought += (thought ? "\n" : "") + text.slice(i + fullTag.length, closeIndex);
          i = closeIndex + closeTag.length;
          continue;
        } else if (isStreaming) {
          thought += (thought ? "\n" : "") + text.slice(i + fullTag.length);
          isThinking = true;
          i = n;
          continue;
        }
      }

      if (isStreaming) {
        const isPotentialTag = allowedTags.some(tag => tag.startsWith(remaining.toLowerCase()));
        if (isPotentialTag && i + remaining.length === n) {
          isThinking = true;
          hasFoundAnyThought = true;
          break;
        }
      }
    }
    
    // Once we hit a non-whitespace character that isn't part of a reasoning tag,
    // we consider the content started.
    const char = text[i];
    if (!hasContentStarted && char.trim().length > 0) {
      hasContentStarted = true;
    }
    
    content += char;
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
