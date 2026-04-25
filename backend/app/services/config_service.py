import json
import os
from pathlib import Path
from copy import deepcopy
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
        :param config_path: 配置文件存储路径，默认为 ~/.yue/data/global_config.json
        """
        if config_path is None:
            data_dir = os.getenv("YUE_DATA_DIR", "~/.yue/data")
            config_path = Path(os.path.expanduser(data_dir)) / "global_config.json"
        
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config = self._load_config()

    _ROUTING_DEFAULT_MODE = "legacy"
    _ROUTING_DEFAULT_FALLBACK_POLICY = "use_legacy_agent_model"
    _MODEL_TIERS = ("light", "balanced", "heavy")

    def _legacy_runtime_provider_model(self) -> tuple[str, str]:
        llm_section = self._config.get("llm", {})
        provider = llm_section.get("provider")
        if not isinstance(provider, str) or not provider.strip():
            provider = "openai"
        provider = provider.strip()

        providers_cfg = llm_section.get("providers", {})
        provider_cfg = providers_cfg.get(provider, {}) if isinstance(providers_cfg, dict) else {}
        if not isinstance(provider_cfg, dict):
            provider_cfg = {}

        model = provider_cfg.get("model") or provider_cfg.get("default_model")
        if not isinstance(model, str) or not model.strip():
            model = "gpt-4o"
        return provider, model.strip()

    def _default_llm_routing_config(self) -> Dict[str, Any]:
        provider, model = self._legacy_runtime_provider_model()
        return {
            "default_mode": self._ROUTING_DEFAULT_MODE,
            "fallback_policy": self._ROUTING_DEFAULT_FALLBACK_POLICY,
            "auto_upgrade_enabled": True,
            "roles": {
                "general_chat": {"provider": provider, "model": model},
                "tool_use": {"inherit": "general_chat"},
                "reasoning": {"inherit": "general_chat"},
            },
            "rules": {
                "tool_call_requires_role": "tool_use",
                "multi_skill_requires_role": "reasoning",
            },
        }

    def _default_model_tiers(self) -> Dict[str, Any]:
        provider, model = self._legacy_runtime_provider_model()
        base = {"provider": provider, "model": model}
        return {
            "light": deepcopy(base),
            "balanced": deepcopy(base),
            "heavy": deepcopy(base),
        }

    def _normalize_model_tier_entry(self, tier_name: str, tier_value: Any) -> Dict[str, str]:
        defaults = self._default_model_tiers()
        default_entry = defaults.get(tier_name, defaults["balanced"])
        if not isinstance(tier_value, dict):
            return deepcopy(default_entry)

        provider = tier_value.get("provider")
        model = tier_value.get("model")

        if not isinstance(provider, str) or not provider.strip():
            provider = default_entry["provider"]
        if not isinstance(model, str) or not model.strip():
            model = default_entry["model"]

        return {
            "provider": str(provider).strip(),
            "model": str(model).strip(),
        }

    def _normalize_routing_role(self, role_name: str, role_value: Any) -> Dict[str, Any]:
        defaults = self._default_llm_routing_config()["roles"]
        default_role = defaults.get(role_name, defaults["general_chat"])

        if not isinstance(role_value, dict):
            return deepcopy(default_role)

        inherit = role_value.get("inherit")
        if isinstance(inherit, str) and inherit.strip():
            return {"inherit": inherit.strip()}

        provider = role_value.get("provider")
        model = role_value.get("model")

        default_provider = default_role.get("provider", defaults["general_chat"].get("provider", "openai"))
        default_model = default_role.get("model", defaults["general_chat"].get("model", "gpt-4o"))

        if not isinstance(provider, str) or not provider.strip():
            provider = default_provider
        if not isinstance(model, str) or not model.strip():
            model = default_model

        return {"provider": str(provider).strip(), "model": str(model).strip()}

    def get_llm_routing_config(self) -> Dict[str, Any]:
        llm_section = self._config.get("llm", {})
        raw = llm_section.get("routing", {})
        if not isinstance(raw, dict):
            raw = {}

        merged = self._default_llm_routing_config()

        default_mode = raw.get("default_mode")
        if isinstance(default_mode, str) and default_mode.strip() in {"legacy", "role_based"}:
            merged["default_mode"] = default_mode.strip()

        fallback_policy = raw.get("fallback_policy")
        allowed_fallbacks = {"use_general_chat", "use_legacy_agent_model", "fail_closed"}
        if isinstance(fallback_policy, str) and fallback_policy.strip() in allowed_fallbacks:
            merged["fallback_policy"] = fallback_policy.strip()

        auto_upgrade_enabled = raw.get("auto_upgrade_enabled")
        if isinstance(auto_upgrade_enabled, bool):
            merged["auto_upgrade_enabled"] = auto_upgrade_enabled
        elif auto_upgrade_enabled is not None:
            merged["auto_upgrade_enabled"] = bool(auto_upgrade_enabled)

        raw_roles = raw.get("roles")
        if isinstance(raw_roles, dict):
            for role_name in ["general_chat", "tool_use", "reasoning", "translation", "writing", "meta"]:
                if role_name in raw_roles:
                    merged["roles"][role_name] = self._normalize_routing_role(role_name, raw_roles.get(role_name))

        raw_rules = raw.get("rules")
        if isinstance(raw_rules, dict):
            for key in [
                "tool_call_requires_role",
                "multi_skill_requires_role",
                "translation_prefers_role",
                "vision_prefers_capability",
            ]:
                value = raw_rules.get(key)
                if isinstance(value, str) and value.strip():
                    merged["rules"][key] = value.strip()

        return merged

    def resolve_model_role(self, role_name: str) -> Optional[Dict[str, Any]]:
        from app.services.llm.routing import resolve_role_config

        if not isinstance(role_name, str) or not role_name.strip():
            return None
        return resolve_role_config(self.get_llm_routing_config(), role_name.strip())

    def get_model_tiers(self) -> Dict[str, Any]:
        llm_section = self._config.get("llm", {})
        raw = llm_section.get("model_tiers", {})
        if not isinstance(raw, dict):
            raw = {}

        merged = self._default_model_tiers()
        for tier_name in self._MODEL_TIERS:
            if tier_name in raw:
                merged[tier_name] = self._normalize_model_tier_entry(tier_name, raw.get(tier_name))
        return merged

    def resolve_model_tier(self, tier_name: str) -> Optional[Dict[str, Any]]:
        if not isinstance(tier_name, str) or not tier_name.strip():
            return None
        normalized = tier_name.strip().lower()
        if normalized not in self._MODEL_TIERS:
            return None
        resolved = self.get_model_tiers().get(normalized)
        if not isinstance(resolved, dict):
            return None
        return {
            "provider": resolved.get("provider"),
            "model": resolved.get("model"),
            "tier": normalized,
        }

    def _load_config(self) -> Dict[str, Any]:
        """从磁盘加载 JSON 配置文件"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Loading global config from: %s", self.config_path.absolute())
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    logger.info("Loaded config: %s", json.dumps(self._redact_secrets(config), indent=2))
                    return config
            except Exception as e:
                logger.error("Error loading config: %s", e)
                return {}
        logger.warning("Config file not found: %s", self.config_path.absolute())
        return {}

    def _redact_secrets(self, value: Any) -> Any:
        if isinstance(value, dict):
            redacted = {}
            for k, v in value.items():
                key = str(k).lower()
                if any(token in key for token in ("api_key", "token", "secret", "password")):
                    redacted[k] = "****"
                else:
                    redacted[k] = self._redact_secrets(v)
            return redacted
        if isinstance(value, list):
            return [self._redact_secrets(item) for item in value]
        return value

    def get_config(self) -> Dict[str, Any]:
        """获取完整配置字典"""
        return self._config

    def get_feature_flags(self) -> Dict[str, bool]:
        """获取功能开关配置"""
        flags = self._config.get("feature_flags", {})
        def _coerce_bool(value: Any, default: bool) -> bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"true", "1", "yes", "on"}:
                    return True
                if lowered in {"false", "0", "no", "off"}:
                    return False
            if value is None:
                return default
            return bool(value)
        return {
            "skill_runtime_enabled": _coerce_bool(flags.get("skill_runtime_enabled"), True),
            "skill_runtime_debug_contract_enabled": _coerce_bool(flags.get("skill_runtime_debug_contract_enabled"), False),
            "skill_import_auto_activate_enabled": _coerce_bool(flags.get("skill_import_auto_activate_enabled"), True),
            "transparency_event_v2_enabled": _coerce_bool(flags.get("transparency_event_v2_enabled"), True),
            "transparency_turn_binding_enabled": _coerce_bool(flags.get("transparency_turn_binding_enabled"), True),
            "chat_trace_ui_enabled": _coerce_bool(flags.get("chat_trace_ui_enabled"), False),
            "chat_trace_raw_enabled": _coerce_bool(flags.get("chat_trace_raw_enabled"), False),
            "reasoning_display_gated_enabled": _coerce_bool(flags.get("reasoning_display_gated_enabled"), True),
            "multimodal_enabled": _coerce_bool(flags.get("multimodal_enabled"), True),
            "multimodal_image_only_submit_enabled": _coerce_bool(flags.get("multimodal_image_only_submit_enabled"), True),
            "multimodal_vision_fallback_enabled": _coerce_bool(flags.get("multimodal_vision_fallback_enabled"), False),
        }

    def update_feature_flags(self, feature_flags: Dict[str, Any]) -> Dict[str, bool]:
        """更新功能开关配置并持久化到磁盘"""
        current = self.get_feature_flags()
        incoming = feature_flags if isinstance(feature_flags, dict) else {}

        for key in current.keys():
            if key not in incoming:
                continue
            value = incoming.get(key)
            if isinstance(value, bool):
                current[key] = value
            elif isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"true", "1", "yes", "on"}:
                    current[key] = True
                elif lowered in {"false", "0", "no", "off"}:
                    current[key] = False
                else:
                    current[key] = bool(value)
            elif value is not None:
                current[key] = bool(value)

        self._config["feature_flags"] = {
            **self._config.get("feature_flags", {}),
            **current,
        }
        self.update_config(self._config)
        return self.get_feature_flags()

    def get_multimodal_config(self) -> Dict[str, Any]:
        multimodal = self._config.get("multimodal", {})
        allowed_mime_types = multimodal.get(
            "allowed_mime_types",
            ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"],
        )
        return {
            "max_image_count": int(multimodal.get("max_image_count", 10)),
            "max_image_size_mb": int(multimodal.get("max_image_size_mb", 10)),
            "allowed_mime_types": list(allowed_mime_types),
        }

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
        from app.core.settings import AppSettings
        
        llm_section = self._config.get("llm", {})
        json_kwargs = {}
        
        # 1. 基础字段
        if "provider" in llm_section: json_kwargs["llm_provider"] = llm_section["provider"]
        if "enabled_providers" in llm_section: json_kwargs["enabled_providers"] = llm_section["enabled_providers"]
        
        # 2. 通用设置 (settings 子树)
        settings = llm_section.get("settings", {})
        if "request_timeout" in settings: json_kwargs["llm_request_timeout"] = settings["request_timeout"]
        if "meta_enabled" in settings: json_kwargs["meta_enabled"] = settings["meta_enabled"]
        if "meta_provider" in settings: json_kwargs["meta_provider"] = settings["meta_provider"]
        if "meta_model" in settings: json_kwargs["meta_model"] = settings["meta_model"]
        if "meta_timeout_ms" in settings: json_kwargs["meta_timeout_ms"] = settings["meta_timeout_ms"]
        if "meta_max_tokens" in settings: json_kwargs["meta_max_tokens"] = settings["meta_max_tokens"]
        if "meta_use_runtime_model_for_title" in settings: json_kwargs["meta_use_runtime_model_for_title"] = settings["meta_use_runtime_model_for_title"]

        # 3. 各 Provider 策略化加载 (providers 子树)
        for provider_name, strategy in STRATEGIES.items():
            provider_cfg = strategy.get_config(llm_section)
            for k, v in provider_cfg.items():
                flat_key = f"{provider_name}_{k}" if k != "model" else f"{provider_name}_model"
                json_kwargs[flat_key] = v

        # 实例化 AppSettings (Env > JSON)
        app_settings = AppSettings(**json_kwargs)
        
        config = {}
        config["provider"] = app_settings.llm_provider
        config["enabled_providers"] = app_settings.enabled_providers
        config["llm_request_timeout"] = app_settings.llm_request_timeout
        config["meta_enabled"] = app_settings.meta_enabled
        config["meta_provider"] = app_settings.meta_provider
        config["meta_model"] = app_settings.meta_model
        config["meta_timeout_ms"] = app_settings.meta_timeout_ms
        config["meta_max_tokens"] = app_settings.meta_max_tokens
        config["meta_use_runtime_model_for_title"] = app_settings.meta_use_runtime_model_for_title

        # 将额外字段 (Providers) 放回 config
        for k, v in app_settings.model_extra.items() if app_settings.model_extra else {}:
            config[k] = v

        # 4. 列表字段兼容性补全
        config["custom_models"] = llm_section.get("custom_models", [])
        config["models"] = llm_section.get("models", {})
        config["model_tiers"] = self.get_model_tiers()
        config["routing"] = self.get_llm_routing_config()
        for k, v in llm_section.items():
            if not isinstance(k, str):
                continue
            if k.endswith("_enabled_models") or k.endswith("_enabled_models_mode"):
                if k not in config:
                    config[k] = v

        # 默认配置增强
        if config.get("meta_provider") is None:
            config["meta_provider"] = config.get("provider")
        if config.get("meta_model") is None and isinstance(config.get("meta_provider"), str):
            config["meta_model"] = config.get(f"{config['meta_provider']}_model")
                
        return config

    def get_model_settings(self, provider: str, model_name: str) -> Dict[str, Any]:
        """
        获取特定模型的设置 (如 max_tokens)
        """
        llm_section = self._config.get("llm", {})
        
        # Handle custom models
        if provider == "custom":
            custom_models = llm_section.get("custom_models", [])
            for cm in custom_models:
                if cm.get("name") == model_name:
                    explicit_caps = cm.get("capabilities")
                    if explicit_caps is not None:
                        return infer_capabilities(provider, model_name, explicit_caps)
                    # Infer based on actual provider/model if possible
                    actual_provider = cm.get("provider", "openai")
                    actual_model = cm.get("model", model_name)
                    return infer_capabilities(actual_provider, actual_model, None)

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
        from app.services.llm.capabilities import infer_capabilities
        from app.services.llm.registry import get_registered_providers

        llm_section = self._config.get("llm", {})
        models_cfg = llm_section.get("models", {})
        
        model_key = f"{provider}/{model_name}"
        model_cfg = models_cfg.get(model_key, {})
        
        explicit_caps = model_cfg.get("capabilities")
        if explicit_caps is not None:
            return infer_capabilities(provider, model_name, explicit_caps)
            
        # Try to get native capabilities from the provider instance
        provider_instance = get_registered_providers().get(provider)
        if provider_instance:
            native_caps = provider_instance.get_model_capabilities(model_name)
            if native_caps is not None:
                return infer_capabilities(provider, model_name, native_caps)
                
        # Fallback to heuristic inference
        return infer_capabilities(provider, model_name, None)

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
        
        :param provider: 可选，指定 Provider 名称（如 "openai"），不传则返回所有
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
        
        if model_id.startswith("custom/"):
            model_name = model_id[len("custom/"):]
            for cm in llm_section.get("custom_models", []):
                if cm.get("name") == model_name:
                    return cm
                    
        models_config = llm_section.get("models", {})
        return models_config.get(model_id)

    def get_usage_limits(self, tier: str = "default") -> Dict[str, Any]:
        """
        获取使用限制策略 (Policy Matrix)
        """
        policies = {
            "default": {
                "tool_calls_limit": 32,
                "request_limit": 48,
                "total_tokens_limit": 120000
            },
            "strict": {
                "tool_calls_limit": 4,
                "request_limit": 8,
                "total_tokens_limit": 60000
            },
            "premium": {
                "tool_calls_limit": 64,
                "request_limit": 96,
                "total_tokens_limit": 480000
            }
        }
        
        # Allow override from global_config.json
        config_policies = self._config.get("usage_policies", {})
        if config_policies:
            for t, p in config_policies.items():
                if t in policies:
                    policies[t].update(p)
                else:
                    policies[t] = p
                    
        return policies.get(tier, policies["default"])

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
            is_secret = k.endswith("_api_key")
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
            elif k in {"meta_enabled", "meta_provider", "meta_model", "meta_timeout_ms", "meta_max_tokens", "meta_use_runtime_model_for_title"}:
                llm["settings"][k] = v
            elif k in {"routing", "llm_routing"} and isinstance(v, dict):
                llm["routing"] = v
            elif k == "model_tiers" and isinstance(v, dict):
                existing_tiers = llm.get("model_tiers", {})
                if not isinstance(existing_tiers, dict):
                    existing_tiers = {}
                merged_tiers = {
                    tier_name: self._normalize_model_tier_entry(tier_name, existing_tiers.get(tier_name))
                    for tier_name in self._MODEL_TIERS
                    if tier_name in existing_tiers
                }
                llm["model_tiers"] = {
                    **merged_tiers,
                    **{
                        tier_name: self._normalize_model_tier_entry(tier_name, v.get(tier_name))
                        for tier_name in self._MODEL_TIERS
                        if tier_name in v
                    },
                }
            elif k.endswith("_enabled_models_mode"):
                llm["settings"][k] = v
            elif k == "custom_models":
                llm["custom_models"] = v
            elif k == "models":
                if "models" not in llm:
                    llm["models"] = {}
                for model_id, model_data in v.items():
                    if model_id not in llm["models"]:
                        llm["models"][model_id] = {}
                    for field_key, field_val in model_data.items():
                        llm["models"][model_id][field_key] = field_val
            else:
                # 尝试匹配 provider_key 格式
                matched = False
                for p_name in STRATEGIES:
                    if k.startswith(f"{p_name}_"):
                        p_key = k[len(p_name)+1:]
                        if p_name not in llm["providers"]: llm["providers"][p_name] = {}
                        
                        # 特殊映射处理
                        if p_key == "model":
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
        defaults = {
            "theme": "light",
            "language": "en",
            "default_agent": "default",
            "advanced_mode": False,
            "voice_input_enabled": True,
            "voice_input_provider": "browser",
            "voice_input_language": "auto",
            "voice_input_show_interim": True,
            "auto_speech_enabled": False,
            "speech_voice": "",
            "speech_rate": 1.0,
            "speech_volume": 1.0,
            "speech_engine": "browser",
            "speech_openai_voice": "alloy",
            "speech_openai_model": "gpt-4o-mini-tts",
        }
        current = self._config.get("preferences", {})
        if not isinstance(current, dict):
            current = {}

        def _coerce_bool(value: Any, default: bool) -> bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"true", "1", "yes", "on"}:
                    return True
                if lowered in {"false", "0", "no", "off"}:
                    return False
            if value is None:
                return default
            return bool(value)

        normalized = {
            **defaults,
            **current,
            "advanced_mode": _coerce_bool(current.get("advanced_mode"), defaults["advanced_mode"]),
            "voice_input_enabled": _coerce_bool(current.get("voice_input_enabled"), defaults["voice_input_enabled"]),
            "voice_input_show_interim": _coerce_bool(current.get("voice_input_show_interim"), defaults["voice_input_show_interim"]),
            "auto_speech_enabled": _coerce_bool(current.get("auto_speech_enabled"), defaults["auto_speech_enabled"]),
        }
        return normalized

    def get_doc_access(self) -> Dict[str, Any]:
        from app.core.settings import AppSettings
        doc_access = self._config.get("doc_access", {})
        
        json_kwargs = {}
        if "allow_roots" in doc_access: json_kwargs["doc_access_allow_roots"] = doc_access["allow_roots"]
        if "deny_roots" in doc_access: json_kwargs["doc_access_deny_roots"] = doc_access["deny_roots"]
        
        app_settings = AppSettings(**json_kwargs)
        return {
            "allow_roots": app_settings.doc_access_allow_roots,
            "deny_roots": app_settings.doc_access_deny_roots
        }

    def get_doc_access_roots(self) -> tuple[list[str], list[str]]:
        doc_access = self.get_doc_access()
        allow_roots = doc_access.get("allow_roots") if isinstance(doc_access, dict) else None
        deny_roots = doc_access.get("deny_roots") if isinstance(doc_access, dict) else None
        return (allow_roots or [], deny_roots or [])

    def get_exec_tool_config(self) -> Dict[str, Any]:
        exec_cfg = self._config.get("exec_tool", {})
        if not isinstance(exec_cfg, dict):
            return {}
        return exec_cfg

    def get_tool_call_mismatch_config(self) -> Dict[str, Any]:
        from app.core.settings import AppSettings
        cfg = self._config.get("tool_call_mismatch", {})
        if not isinstance(cfg, dict):
            cfg = {}
            
        json_kwargs = {}
        if "auto_retry_enabled" in cfg: json_kwargs["tool_call_mismatch_auto_retry_enabled"] = cfg["auto_retry_enabled"]
        if "fallback_model" in cfg: json_kwargs["tool_call_mismatch_fallback_model"] = cfg["fallback_model"]
        if "fallback_models" in cfg: json_kwargs["tool_call_mismatch_fallback_models"] = cfg["fallback_models"]
        
        app_settings = AppSettings(**json_kwargs)
        
        return {
            "auto_retry_enabled": app_settings.tool_call_mismatch_auto_retry_enabled,
            "fallback_model": app_settings.tool_call_mismatch_fallback_model,
            "fallback_models": app_settings.tool_call_mismatch_fallback_models
        }

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
        if isinstance(prefs, dict):
            self._config["preferences"].update(prefs)
        self._config["preferences"] = self.get_preferences()
        self.update_config(self._config)
        return self._config["preferences"]

config_service = ConfigService()
