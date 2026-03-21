import unittest
import asyncio
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.services.config_service import config_service
from app.services.model_factory import (
    ProviderInfo,
    list_providers_structured,
    SimpleProvider,
    register_provider,
    unregister_provider,
)


class DummyProvider2(SimpleProvider):
    name = "dummy2"
    async def list_models(self, refresh: bool = False):
        return ["x", "y"]
    def build(self, model_name: str = None):
        return {"model": model_name or "x"}
    def requirements(self):
        return ["DUMMY2_KEY"]
    def configured(self):
        return True


class TestModelFactoryStructured(unittest.TestCase):
    def setUp(self):
        llm = config_service._config.get("llm", {})
        self._prev_enabled_providers = llm.get("enabled_providers", None)
        llm.pop("enabled_providers", None)
        config_service._config["llm"] = llm
        self._prev_env_enabled_providers = os.environ.get("ENABLED_PROVIDERS")
        if "ENABLED_PROVIDERS" in os.environ:
            os.environ.pop("ENABLED_PROVIDERS")
            
        os.environ["ENABLED_PROVIDERS"] = "openai,deepseek,ollama,zhipu,azure_openai,dummy2"
        from app.core.settings import AppSettings
        import app.core.settings
        app.core.settings.settings = AppSettings()
        
        unregister_provider("dummy2")
        register_provider(DummyProvider2())

    def tearDown(self):
        unregister_provider("dummy2")
        llm = config_service._config.get("llm", {})
        if self._prev_enabled_providers is None:
            llm.pop("enabled_providers", None)
        else:
            llm["enabled_providers"] = self._prev_enabled_providers
        config_service._config["llm"] = llm
        if self._prev_env_enabled_providers is None:
            os.environ.pop("ENABLED_PROVIDERS", None)
        else:
            os.environ["ENABLED_PROVIDERS"] = self._prev_env_enabled_providers
            
        from app.core.settings import AppSettings
        import app.core.settings
        app.core.settings.settings = AppSettings()

    def test_structured_provider_info(self):
        infos = asyncio.run(list_providers_structured(refresh=True))
        self.assertTrue(all(isinstance(i, ProviderInfo) for i in infos))
        names = [i.name for i in infos]
        self.assertIn("dummy2", names)
        d = [i for i in infos if i.name == "dummy2"][0]
        self.assertEqual(d.requirements, ["DUMMY2_KEY"])
        self.assertTrue(d.configured)
        self.assertIn("x", d.models)
        self.assertIn("y", d.available_models)
        self.assertIsInstance(d.supports_model_refresh, bool)


if __name__ == "__main__":
    unittest.main()
