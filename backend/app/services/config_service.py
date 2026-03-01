import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List

class ConfigService:
    """
    配置服务类
    
    负责管理整个应用的全局配置，主要包括：
    1. LLM 配置（API Key、Base URL 等）
    2. 用户偏好设置（主题、语言等）
    3. 自定义模型配置
    
    设计原则：
    - Single Source of Truth：作为配置的唯一可信来源。
    - 优先级策略：环境变量 > JSON 文件配置。
      如果环境变量中存在配置，则优先使用；
      如果不存在，则回退读取 global_config.json 中的配置。
    """
    def __init__(self, config_path: str = None):
        """
        初始化配置服务
        :param config_path: 配置文件存储路径，默认为 backend/data/global_config.json
        """
        if config_path is None:
            # 默认使用 backend/data/global_config.json，相对于本项目结构
            base_dir = Path(__file__).parent.parent.parent
            config_path = base_dir / "data" / "global_config.json"
        
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """从磁盘加载 JSON 配置文件"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Loading global config from: %s", self.config_path.absolute())
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    logger.info("Loaded config: %s", json.dumps(config, indent=2))
                    return config
            except Exception as e:
                logger.error("Error loading config: %s", e)
                return {}
        logger.warning("Config file not found: %s", self.config_path.absolute())
        return {}

    def get_config(self) -> Dict[str, Any]:
        """获取完整配置字典"""
        return self._config

    def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """更新完整配置并持久化到磁盘"""
        self._config.update(new_config)
        with open(self.config_path, 'w') as f:
            json.dump(self._config, f, indent=2)
        return self._config

    def get_llm_config(self) -> Dict[str, Any]:
        """
        获取 LLM 相关配置 (向后兼容的扁平化结构)
        """
        from app.services.llm.config_strategies import STRATEGIES
        
        llm_section = self._config.get("llm", {})
        config = {}
        
        # 1. 基础字段
        config["provider"] = os.getenv("LLM_PROVIDER") or llm_section.get("provider")
        config["enabled_providers"] = os.getenv("ENABLED_PROVIDERS") or llm_section.get("enabled_providers")
        
        # 2. 通用设置 (settings 子树)
        settings = llm_section.get("settings", {})
        config["llm_request_timeout"] = os.getenv("LLM_REQUEST_TIMEOUT") or settings.get("request_timeout")

        # 3. 各 Provider 策略化加载 (providers 子树)
        for provider_name, strategy in STRATEGIES.items():
            provider_cfg = strategy.get_config(llm_section)
            # 扁平化回旧格式，例如 openai -> openai_api_key
            for k, v in provider_cfg.items():
                flat_key = f"{provider_name}_{k}" if k != "model" else f"{provider_name}_model"
                # 特殊处理，有些 key 在旧格式中不带下划线
                if provider_name == "azure_openai" and k == "token":
                    flat_key = "azure_openai_token"
                config[flat_key] = v

        # 4. 列表字段兼容性补全
        config["custom_models" ] = llm_section.get("custom_models", [])
        for k, v in llm_section.items():
            if not isinstance(k, str):
                continue
            if k.endswith("_enabled_models") or k.endswith("_enabled_models_mode"):
                if k not in config:
                    config[k] = v

        # 默认配置增强
        if not config.get('llm_request_timeout'):
            config['llm_request_timeout'] = 300
        else:
            try:
                config['llm_request_timeout'] = int(config['llm_request_timeout'])
            except (ValueError, TypeError):
                config['llm_request_timeout'] = 300
                
        return config

    def get_model_settings(self, provider: str, model_name: str) -> Dict[str, Any]:
        """
        获取特定模型的设置 (如 max_tokens)
        """
        llm_section = self._config.get("llm", {})
        models_cfg = llm_section.get("models", {})
        
        # Try exact match: provider/model_name
        model_key = f"{provider}/{model_name}"
        model_cfg = models_cfg.get(model_key)
        
        if not model_cfg:
            # Try finding by model_name in provider's settings
            provider_cfg = llm_section.get("providers", {}).get(provider, {})
            model_cfg = provider_cfg # Fallback to provider defaults
            
        settings = {}
        if model_cfg:
            if "max_output_tokens" in model_cfg:
                settings["max_tokens"] = int(model_cfg["max_output_tokens"])
            elif "max_tokens" in model_cfg:
                settings["max_tokens"] = int(model_cfg["max_tokens"])
                
        return settings

    def get_model_capabilities(self, provider: str, model_name: str) -> List[str]:
        """
        获取模型的特殊能力 (如 reasoning, vision)
        """
        llm_section = self._config.get("llm", {})
        models_cfg = llm_section.get("models", {})
        
        model_key = f"{provider}/{model_name}"
        model_cfg = models_cfg.get(model_key, {})
        
        return model_cfg.get("capabilities", [])

    def get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """按策略模式获取特定 Provider 的配置"""
        from app.services.llm.config_strategies import STRATEGIES
        
        llm_section = self._config.get("llm", {})
        strategy = STRATEGIES.get(provider_name)
        if not strategy:
            return llm_section.get("providers", {}).get(provider_name, {})
        return strategy.get_config(llm_section)

    def get_available_models(self, provider: Optional[str] = None, enabled_only: bool = True) -> list[Dict[str, Any]]:
        """
        获取可用模型列表
        
        :param provider: 可选，指定 Provider 名称（如 "openai"、"zhipu"），不传则返回所有
        :param enabled_only: 是否只返回启用的模型，默认 True
        :return: 模型信息列表，每个包含 id、display_name、context_window 等字段
        """
        llm_section = self._config.get("llm", {})
        models_config = llm_section.get("models", {})
        
        results = []
        for model_id, model_info in models_config.items():
            # 如果指定了 provider，只返回该 provider 的模型
            if provider and not model_id.startswith(f"{provider}/"):
                continue
            
            # 如果要求 enabled_only，过滤未启用的
            if enabled_only and not model_info.get("enabled", True):
                continue
            
            # 构建返回对象
            result = {
                "id": model_id,
                **model_info
            }
            results.append(result)
        
        # 按 display_name 排序
        results.sort(key=lambda x: x.get("display_name", ""))
        return results

    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定模型的详细信息
        
        :param model_id: 模型 ID（格式："provider/model_name"，如 "openai/gpt-4o"）
        :return: 模型信息字典，包含 display_name、context_window、capabilities 等
        """
        llm_section = self._config.get("llm", {})
        models_config = llm_section.get("models", {})
        return models_config.get(model_id)

    def get_provider_default_model(self, provider: str) -> Optional[str]:
        """
        获取指定 Provider 的默认模型
        
        :param provider: Provider 名称
        :return: 默认模型 ID（如 "openai/gpt-4o"），如果未配置则返回 None
        """
        llm_section = self._config.get("llm", {})
        providers_config = llm_section.get("providers", {})
        provider_config = providers_config.get(provider, {})
        
        # 优先使用 default_model
        default_model = provider_config.get("default_model")
        if default_model:
            # 补全为完整 ID 格式
            if not default_model.startswith(f"{provider}/"):
                return f"{provider}/{default_model}"
            return default_model
        
        # 回退到 model 字段（向后兼容）
        model = provider_config.get("model")
        if model and not model.startswith(f"{provider}/"):
            return f"{provider}/{model}"
        return model

    def update_llm_config(self, llm_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新 LLM 配置 (处理扁平化输入并存入结构化 JSON)
        """
        from app.services.llm.config_strategies import STRATEGIES
        
        llm = self._config.get("llm", {})
        if "providers" not in llm: llm["providers"] = {}
        if "settings" not in llm: llm["settings"] = {}

        for k, v in llm_config.items():
            # 脱敏保护逻辑
            is_secret = k.endswith("_api_key") or k in ["azure_client_secret", "azure_openai_token"]
            if is_secret:
                if v is None or (isinstance(v, str) and (v.strip() == "" or v.startswith("****"))):
                    continue

            # 路由到正确位置
            if k == "provider":
                llm["provider"] = v
            elif k == "enabled_providers":
                llm["enabled_providers"] = v
            elif k == "llm_request_timeout":
                llm["settings"]["request_timeout"] = v
            elif k.endswith("_enabled_models_mode"):
                llm["settings"][k] = v
            elif k == "custom_models":
                llm["custom_models"] = v
            else:
                # 尝试匹配 provider_key 格式
                matched = False
                for p_name in STRATEGIES:
                    if k.startswith(f"{p_name}_"):
                        p_key = k[len(p_name)+1:]
                        if p_name not in llm["providers"]: llm["providers"][p_name] = {}
                        
                        # 特殊映射处理
                        if p_name == "azure_openai" and p_key == "token":
                            llm["providers"][p_name]["token"] = v
                        elif p_key == "model":
                            llm["providers"][p_name]["model"] = v
                        else:
                            llm["providers"][p_name][p_key] = v
                        matched = True
                        break
                
                # 如果没匹配到 provider，且是旧格式中的 model 结尾
                if not matched and k.endswith("_model"):
                    p_name = k.rsplit("_", 1)[0]
                    if p_name in STRATEGIES:
                        if p_name not in llm["providers"]: llm["providers"][p_name] = {}
                        llm["providers"][p_name]["model"] = v

        self._config["llm"] = llm
        self.update_config(self._config)
        return self.get_llm_config()


    # Custom models helpers
    def list_custom_models(self) -> list[Dict[str, Any]]:
        llm = self._config.get("llm", {})
        return llm.get("custom_models", [])

    def upsert_custom_model(self, model: Dict[str, Any]) -> list[Dict[str, Any]]:
        llm = self._config.get("llm", {})
        models = llm.get("custom_models", [])
        name = model.get("name")
        if not name:
            raise ValueError("name is required")
        # Protect api_key from empty/masked overwrite
        if "api_key" in model and isinstance(model["api_key"], str):
            masked = model["api_key"].strip()
            if masked == "" or masked.startswith("****"):
                model.pop("api_key")
        found = False
        for i, m in enumerate(models):
            if m.get("name") == name:
                m.update(model)
                models[i] = m
                found = True
                break
        if not found:
            models.append(model)
        llm["custom_models"] = models
        self._config["llm"] = llm
        self.update_config(self._config)
        return models

    def delete_custom_model(self, name: str) -> list[Dict[str, Any]]:
        llm = self._config.get("llm", {})
        models = llm.get("custom_models", [])
        models = [m for m in models if m.get("name") != name]
        llm["custom_models"] = models
        self._config["llm"] = llm
        self.update_config(self._config)
        return models

    def get_preferences(self) -> Dict[str, Any]:
        return self._config.get("preferences", {
            "theme": "light",
            "language": "en",
            "default_agent": "default"
        })

    def get_doc_access(self) -> Dict[str, Any]:
        doc_access = self._config.get("doc_access", {})
        allow_roots = doc_access.get("allow_roots") if isinstance(doc_access, dict) else []
        deny_roots = doc_access.get("deny_roots") if isinstance(doc_access, dict) else []
        allow = [r for r in allow_roots if isinstance(r, str) and r.strip()] if isinstance(allow_roots, list) else []
        deny = [r for r in deny_roots if isinstance(r, str) and r.strip()] if isinstance(deny_roots, list) else []
        return {"allow_roots": allow, "deny_roots": deny}

    def get_exec_tool_config(self) -> Dict[str, Any]:
        exec_cfg = self._config.get("exec_tool", {})
        if not isinstance(exec_cfg, dict):
            return {}
        return exec_cfg

    def update_doc_access(self, doc_access: Dict[str, Any]) -> Dict[str, Any]:
        incoming_allow = doc_access.get("allow_roots") if isinstance(doc_access, dict) else []
        incoming_deny = doc_access.get("deny_roots") if isinstance(doc_access, dict) else []
        allow = [r for r in incoming_allow if isinstance(r, str) and r.strip()] if isinstance(incoming_allow, list) else []
        deny = [r for r in incoming_deny if isinstance(r, str) and r.strip()] if isinstance(incoming_deny, list) else []

        self._config["doc_access"] = {"allow_roots": allow, "deny_roots": deny}
        self.update_config(self._config)
        return self._config["doc_access"]

    def update_preferences(self, prefs: Dict[str, Any]) -> Dict[str, Any]:
        if "preferences" not in self._config:
            self._config["preferences"] = {}
        self._config["preferences"].update(prefs)
        self.update_config(self._config)
        return self._config["preferences"]

config_service = ConfigService()
