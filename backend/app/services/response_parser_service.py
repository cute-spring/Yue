import json
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List

class ResponseParser(ABC):
    """
    LLM 响应解析器基类 (Adapter Pattern Interface)
    负责将不同模型的流式输出统一解析为前端需要的格式。
    """
    def __init__(self):
        self.last_length = 0
        self.thought_start_time = None
        self.thought_end_time = None
        self.is_thinking = False

    @abstractmethod
    def parse_chunk(self, full_message: str) -> List[Dict[str, Any]]:
        """
        解析当前的流式 Chunk，返回一组需要发送给前端的消息。
        """
        pass

    def _get_new_content(self, full_message: str) -> str:
        new_content = full_message[self.last_length:]
        self.last_length = len(full_message)
        return new_content

class TagBasedParser(ResponseParser):
    """
    基于标签的解析器 (如 <thought> 或 <think> 标签)
    适用于在正文中嵌入思维过程的模型。
    """
    def __init__(self, start_tags: List[str] = ["<thought>", "<think>"], 
                 end_tags: List[str] = ["</thought>", "</think>"]):
        super().__init__()
        self.start_tags = start_tags
        self.end_tags = end_tags
        self.full_content_received = ""

    def parse_chunk(self, full_message: str) -> List[Dict[str, Any]]:
        new_text = self._get_new_content(full_message)
        if not new_text:
            return []

        results = []
        self.full_content_received += new_text

        # 检测思维开始
        if not self.is_thinking:
            for tag in self.start_tags:
                if tag in self.full_content_received and self.thought_start_time is None:
                    self.is_thinking = True
                    self.thought_start_time = time.time()
                    break

        # 检测思维结束
        if self.is_thinking:
            for tag in self.end_tags:
                if tag in self.full_content_received and self.thought_end_time is None:
                    self.is_thinking = False
                    self.thought_end_time = time.time()
                    break

        # 对于标签模式，目前前端通常直接接收全量文本，由前端解析标签
        # 或者我们可以在这里做剥离，但为了保持兼容性，先只返回 content
        results.append({"content": new_text})
        return results

class FieldBasedParser(ResponseParser):
    """
    基于字段的解析器
    适用于原生支持 reasoning_content 字段的模型（如 DeepSeek Reasoner API）。
    注：Pydantic AI 目前将流式文本合并，如果底层 Provider 支持字段，
    我们需要确保在 Pydantic AI 的流中能正确识别。
    """
    def parse_chunk(self, full_message: str) -> List[Dict[str, Any]]:
        # 这种模式下，通常 Pydantic AI 会将 reasoning 部分先流出来
        # 这里简化处理：如果配置标识了是原生推理模型，我们将前一部分视为 thought
        new_text = self._get_new_content(full_message)
        if not new_text:
            return []
        
        # 实际上 Pydantic AI 的 stream_text() 已经把内容合并了
        # 如果要处理原生字段，可能需要 hook 更底层的流，
        # 这里我们通过配置标记来实现逻辑适配
        return [{"content": new_text}]

def get_parser(provider: str, model_name: str, capabilities: List[str]) -> ResponseParser:
    """
    解析器工厂 (Factory Pattern)
    根据模型能力选择最优解析策略。
    """
    if "reasoning" in capabilities:
        # 如果是原生推理模型，可能使用字段或特定标签
        # DeepSeek R1/Reasoner 通常在 API 层有特殊处理
        return TagBasedParser() # 默认使用标签解析，因为大多数模型仍通过文本流返回标签
    
    return TagBasedParser() # 默认解析器

