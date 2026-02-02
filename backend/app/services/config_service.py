import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

class ConfigService:
    def __init__(self, config_path: str = "data/global_config.json"):
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def get_config(self) -> Dict[str, Any]:
        return self._config

    def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        self._config.update(new_config)
        with open(self.config_path, 'w') as f:
            json.dump(self._config, f, indent=2)
        return self._config

    def get_llm_config(self) -> Dict[str, Any]:
        return self._config.get("llm", {})

    def update_llm_config(self, llm_config: Dict[str, Any]) -> Dict[str, Any]:
        existing = self._config.get("llm", {})
        # Merge updates while protecting secrets from being cleared unintentionally
        for k, v in llm_config.items():
            if k.endswith("_api_key"):
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

    def update_preferences(self, prefs: Dict[str, Any]) -> Dict[str, Any]:
        if "preferences" not in self._config:
            self._config["preferences"] = {}
        self._config["preferences"].update(prefs)
        self.update_config(self._config)
        return self._config["preferences"]

config_service = ConfigService()
