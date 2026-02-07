import unittest
import asyncio
import os
import sys

# Ensure backend path on sys.path for implicit namespace import
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.services.config_service import config_service
from app.services.model_factory import (
    SimpleProvider,
    register_provider,
    unregister_provider,
    list_providers,
    get_model,
)


class DummyProvider(SimpleProvider):
    name = "dummy"

    async def list_models(self, refresh: bool = False):
        return ["d1", "d2"]

    def build(self, model_name: str = None):
        return {"model": model_name or "d1"}

    def requirements(self):
        return ["DUMMY_API_KEY (optional)"]

    def configured(self):
        return True


class TestModelFactoryRegistry(unittest.TestCase):
    def setUp(self):
        unregister_provider("dummy")
        register_provider(DummyProvider())

    def tearDown(self):
        unregister_provider("dummy")

    def test_dynamic_provider_listed(self):
        providers = asyncio.run(list_providers(refresh=True))
        names = [p["name"] for p in providers]
        self.assertIn("dummy", names)
        dummy = [p for p in providers if p["name"] == "dummy"][0]
        self.assertEqual(dummy["requirements"], ["DUMMY_API_KEY (optional)"])
        self.assertTrue(dummy["configured"])
        self.assertIn("d1", dummy["models"])
        self.assertIn("d2", dummy["available_models"])
        self.assertIn("supports_model_refresh", dummy)
        self.assertIsInstance(dummy["supports_model_refresh"], bool)

    def test_empty_enabled_models_does_not_filter(self):
        llm = config_service._config.get("llm", {})
        previous = llm.get("dummy_enabled_models", None)
        previous_mode = llm.get("dummy_enabled_models_mode", None)
        llm["dummy_enabled_models"] = []
        config_service._config["llm"] = llm
        try:
            providers = asyncio.run(list_providers(refresh=True))
            dummy = [p for p in providers if p["name"] == "dummy"][0]
            self.assertEqual(dummy["models"], ["d1", "d2"])
            self.assertEqual(dummy["available_models"], ["d1", "d2"])
        finally:
            llm = config_service._config.get("llm", {})
            if previous is None:
                llm.pop("dummy_enabled_models", None)
            else:
                llm["dummy_enabled_models"] = previous
            if previous_mode is None:
                llm.pop("dummy_enabled_models_mode", None)
            else:
                llm["dummy_enabled_models_mode"] = previous_mode
            config_service._config["llm"] = llm

    def test_empty_enabled_models_filters_when_allowlist_mode(self):
        llm = config_service._config.get("llm", {})
        previous = llm.get("dummy_enabled_models", None)
        previous_mode = llm.get("dummy_enabled_models_mode", None)
        llm["dummy_enabled_models"] = []
        llm["dummy_enabled_models_mode"] = "allowlist"
        config_service._config["llm"] = llm
        try:
            providers = asyncio.run(list_providers(refresh=True))
            dummy = [p for p in providers if p["name"] == "dummy"][0]
            self.assertEqual(dummy["models"], ["d1", "d2"])
            self.assertEqual(dummy["available_models"], [])
        finally:
            llm = config_service._config.get("llm", {})
            if previous is None:
                llm.pop("dummy_enabled_models", None)
            else:
                llm["dummy_enabled_models"] = previous
            if previous_mode is None:
                llm.pop("dummy_enabled_models_mode", None)
            else:
                llm["dummy_enabled_models_mode"] = previous_mode
            config_service._config["llm"] = llm

    def test_non_empty_enabled_models_filters(self):
        llm = config_service._config.get("llm", {})
        previous = llm.get("dummy_enabled_models", None)
        previous_mode = llm.get("dummy_enabled_models_mode", None)
        llm["dummy_enabled_models"] = ["d2"]
        config_service._config["llm"] = llm
        try:
            providers = asyncio.run(list_providers(refresh=True))
            dummy = [p for p in providers if p["name"] == "dummy"][0]
            self.assertEqual(dummy["models"], ["d1", "d2"])
            self.assertEqual(dummy["available_models"], ["d2"])
        finally:
            llm = config_service._config.get("llm", {})
            if previous is None:
                llm.pop("dummy_enabled_models", None)
            else:
                llm["dummy_enabled_models"] = previous
            if previous_mode is None:
                llm.pop("dummy_enabled_models_mode", None)
            else:
                llm["dummy_enabled_models_mode"] = previous_mode
            config_service._config["llm"] = llm

    def test_get_model_dynamic_provider(self):
        m = get_model("dummy", "d2")
        self.assertIsInstance(m, dict)
        self.assertEqual(m.get("model"), "d2")


if __name__ == "__main__":
    unittest.main()
