import unittest
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.services.model_factory import get_model
from pydantic_ai.models.openai import OpenAIChatModel


class TestLiteLLMProvider(unittest.TestCase):
    def setUp(self):
        os.environ["LITELLM_BASE_URL"] = "http://localhost:8080/v1"
        os.environ["LITELLM_API_KEY"] = "test_key"
        os.environ["LITELLM_MODEL"] = "gpt-4o-mini"

    def tearDown(self):
        os.environ.pop("LITELLM_BASE_URL", None)
        os.environ.pop("LITELLM_API_KEY", None)
        os.environ.pop("LITELLM_MODEL", None)

    def test_get_model_litellm(self):
        m = get_model("litellm", "gpt-4o-mini")
        self.assertIsInstance(m, OpenAIChatModel)


if __name__ == "__main__":
    unittest.main()
