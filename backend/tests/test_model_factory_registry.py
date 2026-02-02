import unittest
import asyncio
import os
import sys

# Ensure backend path on sys.path for implicit namespace import
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

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

    def test_get_model_dynamic_provider(self):
        m = get_model("dummy", "d2")
        self.assertIsInstance(m, dict)
        self.assertEqual(m.get("model"), "d2")


if __name__ == "__main__":
    unittest.main()
