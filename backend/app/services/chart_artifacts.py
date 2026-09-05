import json
import uuid
from typing import Any, Dict, List, Optional


MAX_CHART_ARTIFACT_BYTES = 256 * 1024
MAX_CHART_ROWS = 500
MAX_CHART_COLUMNS = 30
MAX_CHART_SERIES = 12
MAX_CHART_TITLE_LENGTH = 120
MAX_CHART_SUBTITLE_LENGTH = 200
MAX_CHART_LABEL_LENGTH = 80
MAX_CHART_FIELD_LENGTH = 80
MAX_CHART_CELL_STRING_LENGTH = 500
MAX_CHART_MARKER_LENGTH = 120

ALLOWED_CHART_TYPES = {"bar", "line", "area", "pie", "scatter", "stacked-bar", "multi-line"}
ALLOWED_FIELD_TYPES = {"category", "number", "time"}
ALLOWED_VALUE_FORMATS = {"plain", "currency", "percent", "compact"}

FORBIDDEN_CHART_KEYS = {
    "echartsoption",
    "rawoption",
    "option",
    "formatter",
    "tooltiphtml",
    "html",
    "unsafehtml",
    "dangerouslysetinnerhtml",
}


def _normalized_key(key: str) -> str:
    return "".join(ch for ch in key.lower() if ch not in {"-", "_", " "})


def _find_forbidden_key(value: Any, path: str = "$") -> Optional[str]:
    if isinstance(value, list):
        for index, child in enumerate(value):
            found = _find_forbidden_key(child, f"{path}[{index}]")
            if found:
                return found
        return None
    if not isinstance(value, dict):
        return None
    for key, child in value.items():
        child_path = f"{path}.{key}"
        if _normalized_key(str(key)) in FORBIDDEN_CHART_KEYS:
            return child_path
        found = _find_forbidden_key(child, child_path)
        if found:
            return found
    return None


def _serialized_size(value: Dict[str, Any]) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _is_primitive(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _validate_optional_text(value: Any, *, path: str, max_length: int) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{path} must be a string")
    if len(value) > max_length:
        raise ValueError(f"{path} exceeds {max_length} characters")
    return value


def _validate_data_rows(value: Any) -> tuple[List[Dict[str, Any]], set[str]]:
    if not isinstance(value, list) or not value:
        raise ValueError("chart data must be a non-empty array")
    if len(value) > MAX_CHART_ROWS:
        raise ValueError("chart data exceeds row limit")

    rows: List[Dict[str, Any]] = []
    fields: set[str] = set()
    for index, row in enumerate(value):
        if not isinstance(row, dict):
            raise ValueError(f"chart data[{index}] must be an object")
        normalized_row: Dict[str, Any] = {}
        for key, cell in row.items():
            if not isinstance(key, str) or not key or len(key) > MAX_CHART_FIELD_LENGTH:
                raise ValueError(f"chart data[{index}] contains an invalid field name")
            if not _is_primitive(cell):
                raise ValueError(f"chart data[{index}].{key} must be a primitive value")
            if isinstance(cell, str) and len(cell) > MAX_CHART_CELL_STRING_LENGTH:
                raise ValueError(f"chart data[{index}].{key} exceeds string length limit")
            normalized_row[key] = cell
            fields.add(key)
        rows.append(normalized_row)

    if len(fields) > MAX_CHART_COLUMNS:
        raise ValueError("chart data exceeds column limit")
    return rows, fields


def _validate_field_encoding(value: Any, *, path: str, allowed_types: set[str], fields: set[str]) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be an object")
    field = value.get("field")
    field_type = value.get("type")
    if not isinstance(field, str) or not field:
        raise ValueError(f"{path}.field is required")
    if len(field) > MAX_CHART_FIELD_LENGTH:
        raise ValueError(f"{path}.field exceeds length limit")
    if field not in fields:
        raise ValueError(f"{path}.field references missing data field")
    if not isinstance(field_type, str) or field_type not in ALLOWED_FIELD_TYPES:
        raise ValueError(f"{path}.type must be category, number, or time")
    if field_type not in allowed_types:
        raise ValueError(f"{path}.type is not supported for this chart type")

    parsed = {"field": field, "type": field_type}
    label = _validate_optional_text(value.get("label"), path=f"{path}.label", max_length=MAX_CHART_LABEL_LENGTH)
    unit = _validate_optional_text(value.get("unit"), path=f"{path}.unit", max_length=MAX_CHART_LABEL_LENGTH)
    if label is not None:
        parsed["label"] = label
    if unit is not None:
        parsed["unit"] = unit
    return parsed


def _validate_series(value: Any, *, fields: set[str]) -> List[Dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError("chart encoding.series must be a non-empty array")
    if len(value) > MAX_CHART_SERIES:
        raise ValueError("chart encoding.series exceeds series limit")
    parsed_series: List[Dict[str, Any]] = []
    for index, entry in enumerate(value):
        path = f"chart encoding.series[{index}]"
        if not isinstance(entry, dict):
            raise ValueError(f"{path} must be an object")
        field = entry.get("field")
        if not isinstance(field, str) or not field:
            raise ValueError(f"{path}.field is required")
        if len(field) > MAX_CHART_FIELD_LENGTH:
            raise ValueError(f"{path}.field exceeds length limit")
        if field not in fields:
            raise ValueError(f"{path}.field references missing data field")
        parsed = {"field": field}
        label = _validate_optional_text(entry.get("label"), path=f"{path}.label", max_length=MAX_CHART_LABEL_LENGTH)
        unit = _validate_optional_text(entry.get("unit"), path=f"{path}.unit", max_length=MAX_CHART_LABEL_LENGTH)
        if label is not None:
            parsed["label"] = label
        if unit is not None:
            parsed["unit"] = unit
        parsed_series.append(parsed)
    return parsed_series


def validate_yue_chart_spec(chart: Any) -> Dict[str, Any]:
    if not isinstance(chart, dict):
        raise ValueError("chart artifact chart must be an object")
    if chart.get("version") != 1:
        raise ValueError("chart version must be 1")
    if chart.get("kind") != "chart":
        raise ValueError("chart kind must be chart")
    chart_type = chart.get("chartType")
    if not isinstance(chart_type, str) or chart_type not in ALLOWED_CHART_TYPES:
        raise ValueError("chart chartType is unsupported")

    rows, fields = _validate_data_rows(chart.get("data"))
    encoding_raw = chart.get("encoding")
    if not isinstance(encoding_raw, dict):
        raise ValueError("chart encoding must be an object")

    encoding: Dict[str, Any] = {}
    if chart_type in {"bar", "line", "area"}:
        encoding["x"] = _validate_field_encoding(
            encoding_raw.get("x"),
            path="chart encoding.x",
            allowed_types={"category", "time"},
            fields=fields,
        )
        encoding["y"] = _validate_field_encoding(
            encoding_raw.get("y"),
            path="chart encoding.y",
            allowed_types={"number"},
            fields=fields,
        )
    elif chart_type == "scatter":
        encoding["x"] = _validate_field_encoding(
            encoding_raw.get("x"),
            path="chart encoding.x",
            allowed_types={"number"},
            fields=fields,
        )
        encoding["y"] = _validate_field_encoding(
            encoding_raw.get("y"),
            path="chart encoding.y",
            allowed_types={"number"},
            fields=fields,
        )
    elif chart_type == "pie":
        encoding["category"] = _validate_field_encoding(
            encoding_raw.get("category"),
            path="chart encoding.category",
            allowed_types={"category"},
            fields=fields,
        )
        encoding["value"] = _validate_field_encoding(
            encoding_raw.get("value"),
            path="chart encoding.value",
            allowed_types={"number"},
            fields=fields,
        )
    elif chart_type in {"stacked-bar", "multi-line"}:
        encoding["x"] = _validate_field_encoding(
            encoding_raw.get("x"),
            path="chart encoding.x",
            allowed_types={"category", "time"},
            fields=fields,
        )
        encoding["series"] = _validate_series(encoding_raw.get("series"), fields=fields)

    if encoding_raw.get("color") is not None:
        encoding["color"] = _validate_field_encoding(
            encoding_raw.get("color"),
            path="chart encoding.color",
            allowed_types={"category"},
            fields=fields,
        )

    title = _validate_optional_text(chart.get("title"), path="chart title", max_length=MAX_CHART_TITLE_LENGTH)
    subtitle = _validate_optional_text(chart.get("subtitle"), path="chart subtitle", max_length=MAX_CHART_SUBTITLE_LENGTH)

    result: Dict[str, Any] = {
        "version": 1,
        "kind": "chart",
        "chartType": chart_type,
        "data": rows,
        "encoding": encoding,
    }
    if title is not None:
        result["title"] = title
    if subtitle is not None:
        result["subtitle"] = subtitle

    presentation = chart.get("presentation")
    if presentation is not None:
        if not isinstance(presentation, dict):
            raise ValueError("chart presentation must be an object")
        parsed_presentation: Dict[str, Any] = {}
        sort = presentation.get("sort")
        if sort is not None:
            if not isinstance(sort, dict):
                raise ValueError("chart presentation.sort must be an object")
            sort_field = sort.get("field")
            sort_order = sort.get("order")
            if not isinstance(sort_field, str) or sort_field not in fields:
                raise ValueError("chart presentation.sort.field references missing data field")
            if sort_order not in {"asc", "desc"}:
                raise ValueError("chart presentation.sort.order must be asc or desc")
            parsed_presentation["sort"] = {"field": sort_field, "order": sort_order}
        for key in ("showLegend", "showDataZoom"):
            if key in presentation:
                if not isinstance(presentation.get(key), bool):
                    raise ValueError(f"chart presentation.{key} must be a boolean")
                parsed_presentation[key] = presentation[key]
        if "valueFormat" in presentation:
            if presentation.get("valueFormat") not in ALLOWED_VALUE_FORMATS:
                raise ValueError("chart presentation.valueFormat is unsupported")
            parsed_presentation["valueFormat"] = presentation["valueFormat"]
        if parsed_presentation:
            result["presentation"] = parsed_presentation

    return result


def validate_chart_placement(value: Any, *, artifact_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("chart placement must be an object")
    placement_type = value.get("type")
    if placement_type == "append":
        return {"type": "append"}
    if placement_type != "replace_marker":
        raise ValueError("chart placement.type must be append or replace_marker")
    marker = value.get("marker")
    default_marker = f"{{{{chart:{artifact_id}}}}}" if artifact_id else None
    if marker is None:
        marker = default_marker
    if not isinstance(marker, str) or not marker:
        raise ValueError("chart placement.marker is required for replace_marker")
    if len(marker) > MAX_CHART_MARKER_LENGTH:
        raise ValueError("chart placement.marker exceeds length limit")
    return {"type": "replace_marker", "marker": marker}


def validate_chart_artifact_payload(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("chart artifact payload must be an object")
    if _serialized_size(payload) > MAX_CHART_ARTIFACT_BYTES:
        raise ValueError("chart artifact payload exceeds size limit")
    forbidden_path = _find_forbidden_key(payload)
    if forbidden_path:
        raise ValueError(f"chart artifact contains forbidden field at {forbidden_path}")
    if payload.get("artifact_type") != "chart":
        raise ValueError("chart artifact_type must be chart")
    if payload.get("display_mode") != "inline":
        raise ValueError("chart display_mode must be inline")
    artifact_id = payload.get("artifact_id")
    if artifact_id is not None and not isinstance(artifact_id, str):
        raise ValueError("chart artifact_id must be a string")
    chart = validate_yue_chart_spec(payload.get("chart"))
    placement = validate_chart_placement(payload.get("placement"), artifact_id=artifact_id if isinstance(artifact_id, str) else None)
    validated = {**payload, "chart": chart}
    if placement is not None:
        validated["placement"] = placement
    elif "placement" in validated:
        validated.pop("placement")
    return validated


def build_chart_artifact_payload(
    *,
    chart: Dict[str, Any],
    artifact_id: Optional[str] = None,
    title: Optional[str] = None,
    display_mode: str = "inline",
    placement: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "artifact_id": artifact_id or f"chart_{uuid.uuid4().hex[:12]}",
        "artifact_type": "chart",
        "display_mode": display_mode,
        "chart": chart,
    }
    if title:
        payload["title"] = title
    if placement is not None:
        payload["placement"] = placement
    return validate_chart_artifact_payload(payload)


def normalize_chart_artifact_event(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if event.get("event") != "artifact.chart.created":
        return None
    payload = validate_chart_artifact_payload(event.get("payload"))
    artifact_id = payload.get("artifact_id")
    if not isinstance(artifact_id, str) or not artifact_id:
        artifact_id = f"chart_{uuid.uuid4().hex[:12]}"
    sequence = event.get("sequence")
    if not isinstance(sequence, int):
        raise ValueError("chart artifact event sequence is required")
    assistant_turn_id = event.get("assistant_turn_id") or payload.get("assistant_turn_id")
    if not isinstance(assistant_turn_id, str) or not assistant_turn_id:
        raise ValueError("chart artifact assistant_turn_id is required")
    return {
        "artifact_id": artifact_id,
        "artifact_type": "chart",
        "display_mode": "inline",
        "assistant_turn_id": assistant_turn_id,
        "message_id": payload.get("message_id"),
        "run_id": event.get("run_id") or payload.get("run_id"),
        "sequence": sequence,
        "ts": event.get("ts"),
        "placement": payload.get("placement"),
        "chart": payload["chart"],
        "validation_status": "unvalidated",
    }


def collect_chart_artifact_event(target: List[Dict[str, Any]], event: Dict[str, Any], logger: Any = None) -> None:
    try:
        artifact = normalize_chart_artifact_event(event)
    except Exception:
        if logger is not None:
            logger.exception("Invalid chart artifact event dropped")
        return
    if artifact is None:
        return
    key = artifact["artifact_id"] or f"{artifact['assistant_turn_id']}:{artifact['sequence']}"
    existing_index = next(
        (
            index
            for index, existing in enumerate(target)
            if (existing.get("artifact_id") or f"{existing.get('assistant_turn_id')}:{existing.get('sequence')}") == key
        ),
        None,
    )
    if existing_index is None:
        target.append(artifact)
    else:
        target[existing_index] = artifact


def bind_chart_artifacts_to_message(
    artifacts: Optional[List[Dict[str, Any]]],
    *,
    message_id: Optional[int],
) -> List[Dict[str, Any]]:
    bound: List[Dict[str, Any]] = []
    for artifact in artifacts or []:
        if not isinstance(artifact, dict):
            continue
        bound.append({**artifact, "message_id": message_id})
    return sorted(
        bound,
        key=lambda item: (
            item.get("sequence") if isinstance(item.get("sequence"), int) else 2**31 - 1,
            str(item.get("ts") or ""),
            str(item.get("artifact_id") or ""),
        ),
    )
