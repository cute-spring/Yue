import json
from typing import Any, Dict

from pydantic_ai import RunContext

from app.services.chart_artifacts import build_chart_artifact_payload
from ..base import BaseTool
from .registry import builtin_tool_registry


class ChartArtifactCreateTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="chart_artifact_create",
            description=(
                "Create an inline structured Yue chart artifact from an already chart-ready YueChartSpec. "
                "Use this only when the scenario owner has decided a chart materially improves a trend, "
                "comparison, proportion, or distribution explanation. Do not pass raw ECharts options."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "chart": {
                        "type": "object",
                        "description": "A YueChartSpec object with version=1, kind=chart, chartType, data, and encoding.",
                    },
                    "artifact_id": {
                        "type": "string",
                        "description": "Optional stable chart id. If omitted, Yue generates one.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Optional artifact-level label. Prefer chart.title for visible chart title.",
                    },
                    "placement": {
                        "type": "object",
                        "description": "Optional inline placement. Use {type: append} or {type: replace_marker, marker: '{{chart:<artifact_id>}}'} when assistant prose includes that exact marker.",
                    },
                },
                "required": ["chart"],
            },
        )

    async def execute(self, ctx: RunContext, args: Dict[str, Any]) -> str:
        chart = args.get("chart")
        if not isinstance(chart, dict):
            return json.dumps(
                {
                    "ok": False,
                    "error_code": "CHART_SPEC_REQUIRED",
                    "message": "chart must be a YueChartSpec object.",
                },
                ensure_ascii=False,
            )

        try:
            payload = build_chart_artifact_payload(
                chart=chart,
                artifact_id=args.get("artifact_id") if isinstance(args.get("artifact_id"), str) else None,
                title=args.get("title") if isinstance(args.get("title"), str) else None,
                placement=args.get("placement") if isinstance(args.get("placement"), dict) else None,
            )
        except Exception as exc:
            return json.dumps(
                {
                    "ok": False,
                    "error_code": "INVALID_CHART_ARTIFACT",
                    "message": str(exc),
                },
                ensure_ascii=False,
            )

        deps = ctx.deps if isinstance(getattr(ctx, "deps", None), dict) else {}
        emit = deps.get("emit_chart_artifact")
        if not callable(emit):
            return json.dumps(
                {
                    "ok": False,
                    "error_code": "CHART_ARTIFACT_EMITTER_UNAVAILABLE",
                    "message": "Structured chart artifact emitter is not available in this runtime.",
                },
                ensure_ascii=False,
            )

        await emit(payload)
        return json.dumps(
            {
                "ok": True,
                "artifact_id": payload["artifact_id"],
                "artifact_type": "chart",
                "display_mode": "inline",
                "message": "Structured chart artifact emitted. Refer to it in prose; do not repeat the full chart JSON.",
            },
            ensure_ascii=False,
        )


builtin_tool_registry.register(ChartArtifactCreateTool())
