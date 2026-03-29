import re
from typing import Any, Dict, List, Optional

from app.services.skills.models import RuntimeSkillActionDescriptor, RuntimeSkillActionInvocationResult


class SkillPolicyGate:
    """
    Authorization checks for selection and runtime binding.
    """

    @staticmethod
    def check_tool_intersection(agent_tools: List[str], skill_allowed_tools: Optional[List[str]]) -> List[str]:
        if skill_allowed_tools is None:
            return agent_tools

        agent_set = set(agent_tools)
        skill_set = set(skill_allowed_tools)
        return list(agent_set.intersection(skill_set))

    @staticmethod
    def map_action_to_tool(action: RuntimeSkillActionDescriptor) -> Optional[str]:
        explicit_tool = (action.tool or "").strip()
        if explicit_tool:
            return explicit_tool
        policy = (action.approval_policy or "").strip().lower()
        if not policy:
            return None
        if policy.startswith("tool:"):
            return policy.split(":", 1)[1] or None
        return None

    @staticmethod
    def requires_approval(action: RuntimeSkillActionDescriptor) -> bool:
        safety = (action.safety or "").strip().lower()
        approval_policy = (action.approval_policy or "").strip().lower()
        return safety in {"workspace_write", "destructive"} or approval_policy == "manual"

    @staticmethod
    def _matches_schema_type(value: Any, schema_type: str) -> bool:
        if schema_type == "null":
            return value is None
        if schema_type == "string":
            return isinstance(value, str)
        if schema_type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if schema_type == "number":
            return (isinstance(value, int) and not isinstance(value, bool)) or isinstance(value, float)
        if schema_type == "boolean":
            return isinstance(value, bool)
        if schema_type == "array":
            return isinstance(value, list)
        if schema_type == "object":
            return isinstance(value, dict)
        return True

    @staticmethod
    def _resolve_schema_types(schema: Dict[str, Any]) -> List[str]:
        schema_type = schema.get("type")
        if isinstance(schema_type, str):
            return [schema_type]
        if isinstance(schema_type, list):
            return [item for item in schema_type if isinstance(item, str)]
        return []

    @staticmethod
    def _schema_allows_null(schema: Dict[str, Any]) -> bool:
        if schema.get("nullable") is True:
            return True
        return "null" in SkillPolicyGate._resolve_schema_types(schema)

    @staticmethod
    def _format_schema_path(path: str) -> str:
        return path or "arguments"

    @staticmethod
    def _validate_schema_node(
        *,
        schema: Dict[str, Any],
        value: Any,
        path: str,
    ) -> tuple[List[str], Any]:
        errors: List[str] = []
        schema_types = SkillPolicyGate._resolve_schema_types(schema)
        current_path = SkillPolicyGate._format_schema_path(path)
        primary_schema_type = next((item for item in schema_types if item != "null"), schema_types[0] if schema_types else None)

        if value is None:
            if SkillPolicyGate._schema_allows_null(schema):
                return errors, value
            if schema_types:
                expected = " or ".join(schema_types)
                return [f"Invalid type for action argument `{current_path}`: expected {expected}"], value

        if schema_types and not any(SkillPolicyGate._matches_schema_type(value, schema_type) for schema_type in schema_types):
            expected = " or ".join(schema_types)
            return [f"Invalid type for action argument `{current_path}`: expected {expected}"], value

        enum_values = schema.get("enum")
        if isinstance(enum_values, list) and value not in enum_values:
            errors.append(f"Invalid value for action argument `{current_path}`: expected one of {enum_values}")

        if primary_schema_type == "string" and isinstance(value, str):
            min_length = schema.get("minLength")
            max_length = schema.get("maxLength")
            pattern = schema.get("pattern")
            if isinstance(min_length, int) and len(value) < min_length:
                errors.append(
                    f"String action argument `{current_path}` must have length >= {min_length}"
                )
            if isinstance(max_length, int) and len(value) > max_length:
                errors.append(
                    f"String action argument `{current_path}` must have length <= {max_length}"
                )
            if isinstance(pattern, str):
                try:
                    if re.search(pattern, value) is None:
                        errors.append(
                            f"String action argument `{current_path}` must match pattern `{pattern}`"
                        )
                except re.error:
                    errors.append(
                        f"Invalid schema pattern for action argument `{current_path}`: `{pattern}`"
                    )

        if primary_schema_type in {"integer", "number"} and (
            (isinstance(value, int) and not isinstance(value, bool)) or isinstance(value, float)
        ):
            minimum = schema.get("minimum")
            maximum = schema.get("maximum")
            if isinstance(minimum, (int, float)) and value < minimum:
                errors.append(f"Numeric action argument `{current_path}` must be >= {minimum}")
            if isinstance(maximum, (int, float)) and value > maximum:
                errors.append(f"Numeric action argument `{current_path}` must be <= {maximum}")

        if primary_schema_type == "object" and isinstance(value, dict):
            properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
            required = schema.get("required") if isinstance(schema.get("required"), list) else []
            allow_additional = schema.get("additionalProperties", True)
            normalized = dict(value)

            for key in required:
                child_path = f"{current_path}.{key}" if current_path != "arguments" else key
                if key not in normalized:
                    prop_schema = properties.get(key)
                    if isinstance(prop_schema, dict) and "default" in prop_schema:
                        normalized[key] = prop_schema["default"]
                    else:
                        errors.append(f"Missing required action argument: {child_path}")

            for key, prop_schema in properties.items():
                if key not in normalized and isinstance(prop_schema, dict) and "default" in prop_schema:
                    normalized[key] = prop_schema["default"]

            if allow_additional is False:
                for key in list(normalized.keys()):
                    if key not in properties:
                        child_path = f"{current_path}.{key}" if current_path != "arguments" else key
                        errors.append(f"Unexpected action argument: {child_path}")

            for key, child_value in list(normalized.items()):
                prop_schema = properties.get(key)
                if not isinstance(prop_schema, dict):
                    continue
                child_path = f"{current_path}.{key}" if current_path != "arguments" else key
                child_errors, normalized_child = SkillPolicyGate._validate_schema_node(
                    schema=prop_schema,
                    value=child_value,
                    path=child_path,
                )
                errors.extend(child_errors)
                normalized[key] = normalized_child

            return errors, normalized

        if primary_schema_type == "array" and isinstance(value, list):
            min_items = schema.get("minItems")
            max_items = schema.get("maxItems")
            if isinstance(min_items, int) and len(value) < min_items:
                errors.append(f"Array action argument `{current_path}` must have at least {min_items} item(s)")
            if isinstance(max_items, int) and len(value) > max_items:
                errors.append(f"Array action argument `{current_path}` must have at most {max_items} item(s)")
            item_schema = schema.get("items") if isinstance(schema.get("items"), dict) else None
            if not item_schema:
                return errors, value
            normalized_items = []
            for index, item in enumerate(value):
                child_errors, normalized_item = SkillPolicyGate._validate_schema_node(
                    schema=item_schema,
                    value=item,
                    path=f"{current_path}[{index}]",
                )
                errors.extend(child_errors)
                normalized_items.append(normalized_item)
            return errors, normalized_items

        return errors, value

    @staticmethod
    def validate_action_arguments(
        action: RuntimeSkillActionDescriptor,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> tuple[List[str], Dict[str, Any]]:
        schema = dict(action.input_schema or {})
        incoming = dict(arguments or {})
        if not schema:
            return [], incoming

        errors, normalized = SkillPolicyGate._validate_schema_node(
            schema=schema,
            value=incoming,
            path="arguments",
        )
        return errors, normalized if isinstance(normalized, dict) else {}

    @staticmethod
    def validate_action_invocation(
        action: RuntimeSkillActionDescriptor,
        *,
        enabled_tools: Optional[List[str]] = None,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> RuntimeSkillActionInvocationResult:
        enabled_tools = enabled_tools or []
        mapped_tool = SkillPolicyGate.map_action_to_tool(action)
        missing_requirements: List[str] = []
        validation_errors: List[str] = []

        if not mapped_tool:
            validation_errors.append("Action tool binding is missing")
        if mapped_tool and mapped_tool not in enabled_tools:
            missing_requirements.append(f"tool:{mapped_tool}")
        argument_errors, validated_arguments = SkillPolicyGate.validate_action_arguments(action, arguments)
        validation_errors.extend(argument_errors)

        accepted = len(validation_errors) == 0 and len(missing_requirements) == 0
        return RuntimeSkillActionInvocationResult(
            accepted=accepted,
            skill_name=action.name,
            skill_version=action.version,
            action_id=action.id,
            descriptor=action,
            approval_required=SkillPolicyGate.requires_approval(action),
            approval_policy=action.approval_policy,
            mapped_tool=mapped_tool,
            missing_requirements=missing_requirements,
            validation_errors=validation_errors,
            execution_mode="tool_only",
            metadata={
                "safety": action.safety,
                "load_tier": action.load_tier,
                "validated_arguments": validated_arguments,
            },
        )
