import json
import os
import shutil
import tempfile
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.chat_tool_events import ToolEventTracker
from app.mcp.builtin.chart_artifacts import ChartArtifactCreateTool
from app.mcp.builtin.excel import ExcelQueryTool
from app.services.contract_gate import validate_sse_payload
from app.services.chat_service import ChatService
from app.services.chat_postprocess import persist_assistant_message
from app.services.chart_artifacts import normalize_chart_artifact_event, validate_chart_artifact_payload
from app.services.chat_streaming import StreamEventEmitter, StreamState
from app.services.workspace_service import workspace_service


FIXTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures/excel"))


@pytest.fixture
def chart_temp_db():
    temp_dir = tempfile.mkdtemp()
    db_file = os.path.join(temp_dir, "test_yue_chart.db")
    test_engine = create_engine(f"sqlite:///{db_file}")
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    with patch("app.services.chat_service_schema.engine", test_engine), \
         patch("app.services.chat_service_schema.SessionLocal", testing_session_local), \
         patch("app.services.chat_service_sessions.SessionLocal", testing_session_local), \
         patch("app.services.chat_service_actions.SessionLocal", testing_session_local), \
         patch("app.services.workspace_service.engine", test_engine), \
         patch("app.services.workspace_service.SessionLocal", testing_session_local):
        service = ChatService()
        yield service
    test_engine.dispose()
    shutil.rmtree(temp_dir)


def _serialize(payload):
    return f"data: {json.dumps(payload)}\n\n"


def test_stream_emitter_collects_valid_chart_artifact():
    collected = []
    emitter = StreamEventEmitter(
        event_v2_enabled=True,
        run_id="run_chart",
        assistant_turn_id="turn_chart",
        serialize_payload=_serialize,
        iso_utc_now=lambda: "2026-07-24T00:00:00Z",
        chart_artifact_sink=collected,
    )

    payload = emitter.event_payload(
        {
            "event": "artifact.chart.created",
            "payload": {
                "artifact_id": "chart_demo",
                "artifact_type": "chart",
                "display_mode": "inline",
                "chart": {
                    "version": 1,
                    "kind": "chart",
                    "chartType": "bar",
                    "data": [{"region": "APAC", "revenue": 120}],
                    "encoding": {
                        "x": {"field": "region", "type": "category"},
                        "y": {"field": "revenue", "type": "number"},
                    },
                },
            },
        }
    )

    assert payload["event"] == "artifact.chart.created"
    assert collected[0]["artifact_id"] == "chart_demo"
    assert collected[0]["assistant_turn_id"] == "turn_chart"
    assert collected[0]["sequence"] == 1
    assert validate_sse_payload(payload) == "chart_artifact"


def test_stream_emitter_drops_invalid_chart_artifact_event():
    collected = []
    emitter = StreamEventEmitter(
        event_v2_enabled=True,
        run_id="run_chart",
        assistant_turn_id="turn_chart",
        serialize_payload=_serialize,
        iso_utc_now=lambda: "2026-07-24T00:00:00Z",
        chart_artifact_sink=collected,
    )

    payload = emitter.event_payload(
        {
            "event": "artifact.chart.created",
            "payload": {
                "artifact_id": "chart_bad",
                "artifact_type": "chart",
                "display_mode": "inline",
                "chart": {
                    "version": 1,
                    "kind": "chart",
                    "chartType": "bar",
                    "data": [],
                    "encoding": {},
                    "rawOption": {"tooltip": {"formatter": "function () {}"}},
                },
            },
        }
    )

    assert payload["event"] == "trace.event"
    assert payload["reason"] == "invalid_chart_artifact"
    assert collected == []


def test_normalize_chart_artifact_event_rejects_raw_echarts_option():
    event = {
        "event": "artifact.chart.created",
        "run_id": "run_chart",
        "assistant_turn_id": "turn_chart",
        "sequence": 5,
        "payload": {
            "artifact_id": "chart_bad",
            "artifact_type": "chart",
            "display_mode": "inline",
            "chart": {
                "version": 1,
                "kind": "chart",
                "chartType": "bar",
                "data": [],
                "encoding": {},
                "echartsOption": {"tooltip": {"formatter": "function () {}"}},
            },
        },
    }

    with pytest.raises(ValueError):
        normalize_chart_artifact_event(event)


def test_chart_artifact_validation_rejects_missing_referenced_field():
    with pytest.raises(ValueError, match="references missing data field"):
        validate_chart_artifact_payload(
            {
                "artifact_id": "chart_bad_ref",
                "artifact_type": "chart",
                "display_mode": "inline",
                "chart": {
                    "version": 1,
                    "kind": "chart",
                    "chartType": "bar",
                    "data": [{"region": "APAC", "revenue": 120}],
                    "encoding": {
                        "x": {"field": "region", "type": "category"},
                        "y": {"field": "profit", "type": "number"},
                    },
                },
            }
        )


def test_chart_artifact_validation_preserves_replace_marker_placement():
    payload = validate_chart_artifact_payload(
        {
            "artifact_id": "chart_inline",
            "artifact_type": "chart",
            "display_mode": "inline",
            "placement": {"type": "replace_marker", "marker": "{{chart:chart_inline}}"},
            "chart": {
                "version": 1,
                "kind": "chart",
                "chartType": "bar",
                "data": [{"region": "APAC", "revenue": 120}],
                "encoding": {
                    "x": {"field": "region", "type": "category"},
                    "y": {"field": "revenue", "type": "number"},
                },
            },
        }
    )

    assert payload["placement"] == {"type": "replace_marker", "marker": "{{chart:chart_inline}}"}


def test_add_assistant_message_persists_chart_artifacts_for_replay(chart_temp_db):
    service = chart_temp_db
    workspace = workspace_service.create_workspace(name="Chart Workspace")
    chat = service.create_chat(workspace_id=workspace.id)
    chart_artifacts = [
        {
            "artifact_id": "chart_demo",
            "artifact_type": "chart",
            "display_mode": "inline",
            "assistant_turn_id": "turn_chart",
            "run_id": "run_chart",
            "sequence": 12,
            "ts": "2026-07-24T00:00:00Z",
            "chart": {
                "version": 1,
                "kind": "chart",
                "chartType": "bar",
                "title": "Revenue by Region",
                "data": [{"region": "APAC", "revenue": 120}],
                "encoding": {
                    "x": {"field": "region", "type": "category"},
                    "y": {"field": "revenue", "type": "number"},
                },
            },
        }
    ]

    updated = service.add_message(
        chat.id,
        "assistant",
        "Here is the chart.",
        assistant_turn_id="turn_chart",
        run_id="run_chart",
        chart_artifacts=chart_artifacts,
    )

    assert updated is not None
    msg = updated.messages[0]
    assert msg.chart_artifacts is not None
    assert msg.chart_artifacts[0]["artifact_id"] == "chart_demo"
    assert msg.chart_artifacts[0]["message_id"] == msg.id

    loaded = service.get_chat(chat.id)
    assert loaded is not None
    assert loaded.messages[0].chart_artifacts[0]["chart"]["title"] == "Revenue by Region"
    assert workspace_service.list_artifacts(workspace.id) == []


def test_persist_assistant_message_keeps_chart_only_turn_for_replay(chart_temp_db):
    service = chart_temp_db
    chat = service.create_chat()
    stream_state = StreamState(
        full_response="",
        chart_artifacts=[
            {
                "artifact_id": "chart_only",
                "artifact_type": "chart",
                "display_mode": "inline",
                "assistant_turn_id": "turn_chart_only",
                "run_id": "run_chart_only",
                "sequence": 3,
                "ts": "2026-07-24T00:00:00Z",
                "chart": {
                    "version": 1,
                    "kind": "chart",
                    "chartType": "bar",
                    "title": "Chart Only",
                    "data": [{"region": "APAC", "revenue": 120}],
                    "encoding": {
                        "x": {"field": "region", "type": "category"},
                        "y": {"field": "revenue", "type": "number"},
                    },
                },
            }
        ],
    )

    persisted = persist_assistant_message(
        chat_service=service,
        chat_id=chat.id,
        stream_state=stream_state,
        thought_duration=None,
        ttft=None,
        total_duration=None,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        finish_reason=None,
        current_exception=None,
        assistant_turn_id="turn_chart_only",
        run_id="run_chart_only",
        turn_binding_enabled=True,
        supports_reasoning=False,
        deep_thinking_enabled=False,
        reasoning_enabled=False,
    )

    assert persisted is True
    loaded = service.get_chat(chat.id)
    assert loaded is not None
    assert loaded.messages[0].content == ""
    assert loaded.messages[0].chart_artifacts is not None
    assert loaded.messages[0].chart_artifacts[0]["artifact_id"] == "chart_only"
    assert loaded.messages[0].chart_artifacts[0]["message_id"] == loaded.messages[0].id


@pytest.mark.asyncio
async def test_chart_artifact_create_tool_emits_structured_artifact():
    emit = AsyncMock()
    ctx = MagicMock()
    ctx.deps = {"emit_chart_artifact": emit}
    tool = ChartArtifactCreateTool()
    chart = {
        "version": 1,
        "kind": "chart",
        "chartType": "bar",
        "title": "Revenue by Region",
        "data": [{"region": "APAC", "revenue": 120}],
        "encoding": {
            "x": {"field": "region", "type": "category"},
            "y": {"field": "revenue", "type": "number"},
        },
    }

    result_raw = await tool.execute(ctx, {"artifact_id": "chart_tool", "chart": chart})
    result = json.loads(result_raw)

    assert result["ok"] is True
    assert result["artifact_id"] == "chart_tool"
    emit.assert_awaited_once()
    emitted_payload = emit.await_args.args[0]
    assert emitted_payload["artifact_id"] == "chart_tool"
    assert emitted_payload["chart"]["title"] == "Revenue by Region"


@pytest.mark.asyncio
async def test_chart_artifact_create_tool_accepts_replace_marker_placement():
    emit = AsyncMock()
    ctx = MagicMock()
    ctx.deps = {"emit_chart_artifact": emit}
    chart = {
        "version": 1,
        "kind": "chart",
        "chartType": "bar",
        "data": [{"region": "APAC", "revenue": 120}],
        "encoding": {
            "x": {"field": "region", "type": "category"},
            "y": {"field": "revenue", "type": "number"},
        },
    }

    result_raw = await ChartArtifactCreateTool().execute(
        ctx,
        {
            "artifact_id": "chart_inline",
            "chart": chart,
            "placement": {"type": "replace_marker", "marker": "{{chart:chart_inline}}"},
        },
    )
    result = json.loads(result_raw)

    assert result["ok"] is True
    assert emit.await_args.args[0]["placement"] == {"type": "replace_marker", "marker": "{{chart:chart_inline}}"}


@pytest.mark.asyncio
async def test_chart_artifact_create_tool_rejects_raw_echarts_option():
    emit = AsyncMock()
    ctx = MagicMock()
    ctx.deps = {"emit_chart_artifact": emit}
    tool = ChartArtifactCreateTool()

    result_raw = await tool.execute(
        ctx,
        {
            "chart": {
                "version": 1,
                "kind": "chart",
                "chartType": "bar",
                "data": [],
                "encoding": {},
                "rawOption": {},
            }
        },
    )
    result = json.loads(result_raw)

    assert result["ok"] is False
    assert result["error_code"] == "INVALID_CHART_ARTIFACT"
    emit.assert_not_awaited()


@pytest.mark.asyncio
async def test_chart_artifact_create_tool_reaches_stream_queue_and_collector():
    collected = []
    queue: asyncio.Queue = asyncio.Queue()
    emitter = StreamEventEmitter(
        event_v2_enabled=True,
        run_id="run_chart",
        assistant_turn_id="turn_chart",
        serialize_payload=_serialize,
        iso_utc_now=lambda: "2026-07-24T00:00:00Z",
        chart_artifact_sink=collected,
    )
    tracker = ToolEventTracker(
        chat_id="chat_chart",
        assistant_turn_id="turn_chart",
        run_id="run_chart",
        turn_binding_enabled=True,
        emitter=emitter,
        tool_event_queue=queue,
        chat_service=MagicMock(),
        normalize_finished_ts=lambda value: value,
    )

    async def emit_chart_artifact(payload):
        await tracker.on_tool_event(
            {
                "event": "artifact.chart.created",
                "payload": payload,
                "run_id": "run_chart",
                "assistant_turn_id": "turn_chart",
            }
        )

    ctx = MagicMock()
    ctx.deps = {"emit_chart_artifact": emit_chart_artifact}
    chart = {
        "version": 1,
        "kind": "chart",
        "chartType": "bar",
        "data": [{"region": "APAC", "revenue": 120}],
        "encoding": {
            "x": {"field": "region", "type": "category"},
            "y": {"field": "revenue", "type": "number"},
        },
    }

    result_raw = await ChartArtifactCreateTool().execute(ctx, {"artifact_id": "chart_stream", "chart": chart})
    queued_event = await queue.get()

    assert json.loads(result_raw)["ok"] is True
    assert queued_event["event"] == "artifact.chart.created"
    assert queued_event["assistant_turn_id"] == "turn_chart"
    assert queued_event["payload"]["artifact_id"] == "chart_stream"
    assert collected[0]["artifact_id"] == "chart_stream"


@pytest.mark.asyncio
async def test_excel_query_result_can_emit_structured_chart_artifact():
    collected = []
    queue: asyncio.Queue = asyncio.Queue()
    emitter = StreamEventEmitter(
        event_v2_enabled=True,
        run_id="run_excel_chart",
        assistant_turn_id="turn_excel_chart",
        serialize_payload=_serialize,
        iso_utc_now=lambda: "2026-07-24T00:00:00Z",
        chart_artifact_sink=collected,
    )
    tracker = ToolEventTracker(
        chat_id="chat_excel_chart",
        assistant_turn_id="turn_excel_chart",
        run_id="run_excel_chart",
        turn_binding_enabled=True,
        emitter=emitter,
        tool_event_queue=queue,
        chat_service=MagicMock(),
        normalize_finished_ts=lambda value: value,
    )

    excel_ctx = MagicMock()
    with patch("app.mcp.builtin.excel._get_doc_access", return_value=([FIXTURES_DIR], [])):
        query_raw = await ExcelQueryTool().execute(
            excel_ctx,
            {
                "path": "basic.xlsx",
                "root_dir": FIXTURES_DIR,
                "query": "SELECT Product, SUM(Amount) AS Amount FROM excel_data GROUP BY Product ORDER BY Amount DESC",
            },
        )
    query_result = json.loads(query_raw)
    assert query_result["ok"] is True

    chart = {
        "version": 1,
        "kind": "chart",
        "chartType": "bar",
        "title": "Amount by Product",
        "data": query_result["data"],
        "encoding": {
            "x": {"field": "Product", "type": "category", "label": "Product"},
            "y": {"field": "Amount", "type": "number", "label": "Amount"},
        },
    }

    async def emit_chart_artifact(payload):
        await tracker.on_tool_event(
            {
                "event": "artifact.chart.created",
                "payload": payload,
                "run_id": "run_excel_chart",
                "assistant_turn_id": "turn_excel_chart",
            }
        )

    chart_ctx = MagicMock()
    chart_ctx.deps = {"emit_chart_artifact": emit_chart_artifact}
    result_raw = await ChartArtifactCreateTool().execute(
        chart_ctx,
        {"artifact_id": "chart_excel_amount_by_product", "chart": chart},
    )
    result = json.loads(result_raw)
    queued_event = await queue.get()

    assert result["ok"] is True
    assert queued_event["event"] == "artifact.chart.created"
    assert queued_event["payload"]["chart"]["data"][0]["Product"] == "Banana"
    assert collected[0]["artifact_id"] == "chart_excel_amount_by_product"
    assert collected[0]["chart"]["title"] == "Amount by Product"
