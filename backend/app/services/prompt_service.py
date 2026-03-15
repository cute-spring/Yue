from typing import List, Optional
from app.services.config_service import config_service

class PromptBuilder:
    """
    系统提示词构建器 (Builder Pattern)
    负责根据模型能力、用户请求意图和 Agent 配置动态生成系统提示词。
    """
    def __init__(self, base_prompt: str = ""):
        self._prompt = base_prompt
        self._reasoning_injected = False
        self._viz_injected = False

    def inject_reasoning_protocol(self, provider: str, model_name: str, deep_thinking_enabled: bool) -> "PromptBuilder":
        """
        为非推理模型注入思维链协议
        """
        capabilities = config_service.get_model_capabilities(provider, model_name)
        supports_reasoning = "reasoning" in capabilities
        if not deep_thinking_enabled or not supports_reasoning:
            return self
        if "<thought>" not in self._prompt:
            self._prompt += (
                "\n\n### Reasoning Protocol\n"
                "You must ALWAYS start your response by thinking step-by-step about the user's request. "
                "Enclose your thinking process within <thought>...</thought> tags. "
                "Structure your thinking as follows:\n"
                "1. **[目标]**: Define the objective of the request.\n"
                "2. **[已知条件]**: List the available information and constraints.\n"
                "3. **[计划]**: Outline the steps to solve the problem.\n"
                "4. **[反思]**: (Optional) Self-correct or refine the plan if needed.\n\n"
                "After your thinking process is complete, provide your final answer."
            )
            self._reasoning_injected = True
        return self

    def inject_visualization_guidelines(self, user_message: str) -> "PromptBuilder":
        """
        根据用户消息意图注入可视化（Mermaid）指南
        """
        viz_keywords = ["diagram", "uml", "mermaid", "flowchart", "sequence", "architecture", "流程图", "架构图", "时序图"]
        needs_viz = any(kw in user_message.lower() for kw in viz_keywords)
        
        if needs_viz and "mermaid" not in self._prompt.lower():
            self._prompt += (
                "\n\nVISUALIZATION GUIDELINES - UML Diagram Generation:\n"
                "You are an expert system architect. When requested, visualize complex concepts using Mermaid UML.\n"
                "1. **Mermaid Syntax**: Always use ```mermaid code blocks.\n"
                "2. **Diagram Types**: Use Sequence Diagrams for interactions, Flowcharts for logic, and ER Diagrams for data models.\n"
                "3. **Proactive Visualization**: Since the user asked for a diagram/architecture, ensure you provide at least one clear Mermaid chart."
            )
            self._viz_injected = True
        return self

    def inject_continuation_guidelines(self, user_message: str) -> "PromptBuilder":
        """
        处理“继续”请求，注入续传指南
        """
        continuation_keywords = ["继续", "continue", "go on", "keep going"]
        is_continuation = user_message.strip().lower() in continuation_keywords
        
        if is_continuation:
            self._prompt += (
                "\n\n### Continuation Protocol\n"
                "The previous response was truncated due to length limits. "
                "Please continue exactly where you left off. "
                "DO NOT repeat the previous content or re-introduce the topic. "
                "Just provide the remaining part of the response. "
                "If you were in the middle of a code block, please continue the code logic. "
                "Ensure your output seamlessly appends to the previous message."
            )
        return self

    def build(self) -> str:
        return self._prompt

def build_system_prompt(
    base_prompt: str,
    provider: str,
    model_name: str,
    user_message: str,
    deep_thinking_enabled: bool = False
) -> str:
    """
    便捷函数：构建最终系统提示词
    """
    return (
        PromptBuilder(base_prompt)
        .inject_reasoning_protocol(provider, model_name, deep_thinking_enabled)
        .inject_visualization_guidelines(user_message)
        .inject_continuation_guidelines(user_message)
        .build()
    )
