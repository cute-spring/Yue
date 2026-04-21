from typing import List, Optional, Set
import re

# Capability constants
CAP_VISION = "vision"
CAP_REASONING = "reasoning"
CAP_FUNCTION_CALLING = "function_calling"
CAP_WEB_SEARCH = "web_search"

# Vision patterns (model name regexes or tokens)
VISION_TOKENS = [
    "vision", "vl", "multimodal", "gpt-4o", "gpt-4.5", "claude-3", "gemini", 
    "qwen-vl", "internvl", "llava", "cogvlm", "pixtral"
]

# Text-only explicit exclusions (to prevent false positives)
TEXT_ONLY_TOKENS = [
    "instruct", "text-only", "gpt-4-0613", "gpt-4-0314", "gpt-4-32k"
]

# Reasoning patterns
REASONING_TOKENS = [
    "reasoner", "thought", "thinking", "r1", "o1", "o3", "deepseek-v3"
]

# Function calling patterns
FUNCTION_CALLING_TOKENS = [
    "gpt-4", "gpt-3.5", "claude-3", "gemini", "mistral-large", "mixtral-8x7b",
    "deepseek-v3", "qwen-max", "llama-3"
]

def infer_capabilities(provider: str, model_name: str, explicit_caps: Optional[List[str]] = None) -> List[str]:
    """
    Centralized capability inference logic.
    Priority:
    1. Explicitly configured capabilities (if not empty)
    2. Heuristic inference based on provider and model name
    """
    if explicit_caps:
        return explicit_caps

    caps: Set[str] = set()
    name_lower = (model_name or "").lower()

    # --- Vision Inference ---
    if not any(t in name_lower for t in TEXT_ONLY_TOKENS):
        if any(t in name_lower for t in VISION_TOKENS):
            caps.add(CAP_VISION)
        
        # Provider-specific vision overrides (careful with base gpt-4)
        if provider == "openai" and name_lower.startswith("gpt-4") and "gpt-4-" not in name_lower:
            # Matches gpt-4, but actually gpt-4 base is text-only. 
            # We already match gpt-4o, gpt-4.5 in VISION_TOKENS.
            # If it's literally 'gpt-4' or 'gpt-4-32k', it's text-only.
            pass 
        elif provider == "anthropic" and "claude-3" in name_lower:
            caps.add(CAP_VISION)
        elif provider == "google" or "gemini" in name_lower:
            caps.add(CAP_VISION)

    # --- Reasoning Inference ---
    if any(t in name_lower for t in REASONING_TOKENS):
        caps.add(CAP_REASONING)
    
    # --- Function Calling Inference ---
    if any(t in name_lower for t in FUNCTION_CALLING_TOKENS):
        # Most modern models support function calling
        caps.add(CAP_FUNCTION_CALLING)
    elif provider in ["openai", "anthropic", "google"]:
        caps.add(CAP_FUNCTION_CALLING)

    return sorted(list(caps))

def has_capability(provider: str, model_name: str, capability: str, explicit_caps: Optional[List[str]] = None) -> bool:
    """Check if a model has a specific capability."""
    resolved_caps = infer_capabilities(provider, model_name, explicit_caps)
    return capability in resolved_caps
