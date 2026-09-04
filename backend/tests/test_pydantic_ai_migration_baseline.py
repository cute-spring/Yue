from importlib.metadata import version
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.models.test import TestModel

from app.mcp.base import BuiltinTool
from app.services.usage_service import calculate_usage


def test_pydantic_ai_v2_target_is_installed():
    """Keep the production migration target pinned rather than floating."""
    assert version("pydantic-ai-slim") == "2.37.0"


def test_usage_contract_translates_v2_fields_to_yue_field_names():
    raw_usage = SimpleNamespace(
        input_tokens=11,
        output_tokens=7,
        total_tokens=18,
    )

    usage = calculate_usage("openai", raw_usage, duration=0.5, finish_reason="stop")

    assert usage.prompt_tokens == 11
    assert usage.completion_tokens == 7
    assert usage.total_tokens == 18
    assert usage.tps == 14.0
    assert usage.finish_reason == "stop"


def test_usage_contract_retains_v1_fields_as_a_compatibility_fallback():
    raw_usage = SimpleNamespace(
        request_tokens=11,
        response_tokens=7,
        total_tokens=18,
    )

    usage = calculate_usage("openai", raw_usage, duration=0.5, finish_reason="stop")

    assert usage.prompt_tokens == 11
    assert usage.completion_tokens == 7


@pytest.mark.asyncio
async def test_structured_output_with_side_effecting_yue_tool_finishes_early():
    class Completion(BaseModel):
        answer: str

    side_effects = []

    async def record_side_effect(_ctx, value: str) -> str:
        side_effects.append(value)
        return "recorded"

    side_effecting_tool = BuiltinTool(
        name="record_side_effect",
        description="Record a controlled test side effect.",
        parameters={
            "type": "object",
            "properties": {"value": {"type": "string"}},
            "required": ["value"],
        },
        handler=record_side_effect,
    ).to_pydantic_ai_tool()

    def model_response(_messages, info):
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name=info.output_tools[0].name,
                    args={"answer": "complete"},
                    tool_call_id="output-1",
                ),
                ToolCallPart(
                    tool_name=info.function_tools[0].name,
                    args={"value": "must-not-run"},
                    tool_call_id="side-effect-1",
                ),
            ]
        )

    agent = Agent(
        FunctionModel(model_response),
        output_type=Completion,
        tools=[side_effecting_tool],
        end_strategy="early",
    )

    result = await agent.run("Return the result without performing later side effects.")

    assert result.output == Completion(answer="complete")
    assert side_effects == []


def test_chat_execution_emits_v5_aggregated_usage_separately_from_yue_metrics():
    from app.main import app
    from app.observability import configure_pydantic_ai_instrumentation

    exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
    previous_instrumentation = Agent._instrument_default
    chat_service = MagicMock()
    chat_service.create_chat.return_value = MagicMock(id="instrumented-chat")
    chat_service.get_chat.return_value = None
    tool_registry = MagicMock()
    tool_registry.get_pydantic_ai_tools_for_agent = AsyncMock(return_value=[])

    try:
        configure_pydantic_ai_instrumentation(tracer_provider=tracer_provider)
        with (
            patch("app.api.chat.chat_service", chat_service),
            patch("app.api.chat_stream_deps.chat_service", chat_service),
            patch("app.api.chat_stream_deps.agent_store") as agent_store,
            patch("app.api.chat_stream_deps.tool_registry", tool_registry),
            patch("app.api.chat_stream_deps.get_model", return_value=TestModel()),
        ):
            agent_store.get_agent.return_value = None
            response = TestClient(app).post("/api/chat/stream", json={"message": "instrument this run"})
    finally:
        Agent._instrument_default = previous_instrumentation
        tracer_provider.shutdown()

    assert response.status_code == 200
    assert '"prompt_tokens"' in response.text
    assert '"completion_tokens"' in response.text
    assert "gen_ai.aggregated_usage" not in response.text

    spans = exporter.get_finished_spans()
    run_span = next(span for span in spans if span.attributes.get("gen_ai.operation.name") == "invoke_agent")
    assert run_span.attributes["gen_ai.aggregated_usage.input_tokens"] > 0
    assert run_span.attributes["gen_ai.aggregated_usage.output_tokens"] > 0
    assert "prompt_tokens" not in run_span.attributes
    assert "completion_tokens" not in run_span.attributes
