import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

class ConfigService:
    """
    配置服务类
    
    负责管理整个应用的全局配置，主要包括：
    1. LLM 配置（API Key、Base URL 等）
    2. 用户偏好设置（主题、语言等）
    3. 自定义模型配置
    
    设计原则：
    - Single Source of Truth：作为配置的唯一可信来源。
    - 优先级策略：JSON 文件配置 > 环境变量。
      如果 global_config.json 中存在配置，则优先使用；
      如果不存在，则回退读取对应的环境变量（如 OPENAI_API_KEY）。
    """
    def __init__(self, config_path: str = "data/global_config.json"):
        """
        初始化配置服务
        :param config_path: 配置文件存储路径，默认为 backend/data/global_config.json
        """
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """从磁盘加载 JSON 配置文件"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
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
        获取 LLM 相关配置
        
        核心逻辑：
        1. 读取 global_config.json 中的 'llm' 字段。
        2. 针对关键字段（API Key、Base URL），如果 JSON 中为空，
           则尝试从环境变量中读取默认值。
           
        这样做的好处：
        - 统一了配置入口，业务代码（如 ModelFactory）无需关心配置来自文件还是环境变量。
        - 既支持通过 UI 修改配置（持久化到文件），也支持通过 .env 快速部署（无文件时生效）。
        """
        config = self._config.get("llm", {}).copy()
        
        # 环境变量映射表：Config Key -> Env Var Name
        # 仅当 config 中对应 key 为空值时，才会回退读取环境变量
        env_mapping = {
            'openai_api_key': 'OPENAI_API_KEY',
            'deepseek_api_key': 'DEEPSEEK_API_KEY',
            'ollama_base_url': 'OLLAMA_BASE_URL',
            'gemini_api_key': 'GEMINI_API_KEY',
            'gemini_base_url': 'GEMINI_BASE_URL',
            'zhipu_api_key': 'ZHIPU_API_KEY',
            'zhipu_base_url': 'ZHIPU_BASE_URL',
            'proxy_url': 'LLM_PROXY_URL',
            'no_proxy': 'NO_PROXY',
            'llm_request_timeout': 'LLM_REQUEST_TIMEOUT',
            'ssl_cert_file': 'SSL_CERT_FILE',
            'azure_openai_endpoint': 'AZURE_OPENAI_ENDPOINT',
            'azure_openai_base_url': 'AZURE_OPENAI_BASE_URL',
            'azure_openai_deployment': 'AZURE_OPENAI_DEPLOYMENT',
            'azure_openai_embedding_deployment': 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT',
            'azure_openai_api_version': 'AZURE_OPENAI_API_VERSION',
            'azure_tenant_id': 'AZURE_TENANT_ID',
            'azure_client_id': 'AZURE_CLIENT_ID',
            'azure_client_secret': 'AZURE_CLIENT_SECRET',
            'azure_openai_token': 'AZURE_OPENAI_TOKEN',
            'litellm_base_url': 'LITELLM_BASE_URL',
            'litellm_api_key': 'LITELLM_API_KEY',
            'litellm_model': 'LITELLM_MODEL',
            'openai_model': 'OPENAI_MODEL',
            'deepseek_model': 'DEEPSEEK_MODEL',
            'ollama_model': 'OLLAMA_MODEL',
            'gemini_model': 'GEMINI_MODEL',
            'zhipu_model': 'ZHIPU_MODEL',
            'provider': 'LLM_PROVIDER',
            'llm_base_url': 'LLM_BASE_URL',
            'llm_api_key': 'LLM_API_KEY',
            'llm_model_name': 'LLM_MODEL_NAME',
            'enabled_providers': 'ENABLED_PROVIDERS'
        }
        
        for key, env_var in env_mapping.items():
            if not config.get(key) and os.getenv(env_var):
                config[key] = os.getenv(env_var)
        
        # 默认配置增强：内网环境超时处理
        if not config.get('llm_request_timeout'):
            config['llm_request_timeout'] = 300
        else:
            try:
                config['llm_request_timeout'] = int(config['llm_request_timeout'])
                # 如果用户设置的超时时间过短，也建议至少 60s
                if config['llm_request_timeout'] < 60:
                    config['llm_request_timeout'] = 60
            except (ValueError, TypeError):
                config['llm_request_timeout'] = 300
                
        return config

    def update_llm_config(self, llm_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新 LLM 配置
        
        包含安全逻辑：
        - 自动过滤掩码值（如 '****'），防止前端回传的脱敏数据覆盖真实 Key。
        - 仅更新传入的字段，保留未涉及的字段。
        """
        existing = self._config.get("llm", {})
        # Merge updates while protecting secrets from being cleared unintentionally
        for k, v in llm_config.items():
            is_secret = k.endswith("_api_key") or k in ["azure_client_secret", "azure_openai_token"]
            if is_secret:
                # Ignore empty or masked values to avoid overwriting existing secrets
                if v is None:
                    continue
                if isinstance(v, str):
                    masked = v.strip()
                    if masked == "" or masked.startswith("****"):
                        continue
                existing[k] = v
            else:
                existing[k] = v
        self._config["llm"] = existing
        self.update_config(self._config)
        return self._config["llm"]

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
