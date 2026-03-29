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
        return safety in {"workspace_write", "destructive", "browser_write", "browser_mutation"} or approval_policy == "manual"

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
    def _validate_browser_target_binding(
        action: RuntimeSkillActionDescriptor,
        validated_arguments: Dict[str, Any],
    ) -> List[str]:
        action_metadata = action.metadata if isinstance(action.metadata, dict) else {}
        if action_metadata.get("tool_family") != "agent_browser":
            return []

        operation = action_metadata.get("operation")
        if operation not in {"click", "type"}:
            return []

        errors: List[str] = []

        session_id = validated_arguments.get("session_id")
        tab_id = validated_arguments.get("tab_id")
        element_ref = validated_arguments.get("element_ref")
        binding_source = validated_arguments.get("binding_source")
        binding_session_id = validated_arguments.get("binding_session_id")
        binding_tab_id = validated_arguments.get("binding_tab_id")
        binding_url = validated_arguments.get("binding_url")
        binding_dom_version = validated_arguments.get("binding_dom_version")
        active_dom_version = validated_arguments.get("active_dom_version")
        runtime_url = validated_arguments.get("url")

        if not isinstance(session_id, str) or not session_id.strip():
            errors.append("browser_session_required")
        if not isinstance(tab_id, str) or not tab_id.strip():
            errors.append("browser_tab_required")
        if not isinstance(element_ref, str) or not element_ref.strip():
            errors.append("browser_target_required")
        elif isinstance(binding_source, str) and binding_source.strip():
            expected_prefix = f"{binding_source}#node:"
            if not element_ref.startswith(expected_prefix):
                errors.append("browser_target_context_mismatch")

        if any(
            not isinstance(value, str) or not value.strip()
            for value in (binding_source, binding_session_id, binding_tab_id)
        ):
            errors.append("browser_target_required")

        if (
            isinstance(session_id, str)
            and session_id.strip()
            and isinstance(binding_session_id, str)
            and binding_session_id.strip()
            and session_id != binding_session_id
        ):
            errors.append("browser_target_context_mismatch")

        if (
            isinstance(tab_id, str)
            and tab_id.strip()
            and isinstance(binding_tab_id, str)
            and binding_tab_id.strip()
            and tab_id != binding_tab_id
        ):
            errors.append("browser_target_context_mismatch")

        if (
            isinstance(runtime_url, str)
            and runtime_url.strip()
            and isinstance(binding_url, str)
            and binding_url.strip()
            and runtime_url != binding_url
        ):
            errors.append("browser_target_context_mismatch")

        if (
            isinstance(binding_dom_version, str)
            and binding_dom_version.strip()
            and isinstance(active_dom_version, str)
            and active_dom_version.strip()
            and binding_dom_version != active_dom_version
        ):
            errors.append("browser_target_stale")

        return list(dict.fromkeys(errors))

    @staticmethod
    def _derive_browser_continuity_metadata(
        action: RuntimeSkillActionDescriptor,
        validated_arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        action_metadata = action.metadata if isinstance(action.metadata, dict) else {}
        if action_metadata.get("tool_family") != "agent_browser":
            return {}

        operation = action_metadata.get("operation")
        url = validated_arguments.get("url")
        has_url = isinstance(url, str) and bool(url.strip())

        if operation in {"open", "snapshot", "screenshot"}:
            return {
                "contract_mode": "single_use_url_scoped",
                "current_execution_mode": "single_use_url_scoped" if has_url else "platform_session_candidate",
                "authoritative_target_required": False,
                "resumable_continuity": "not_required" if operation != "snapshot" else "target_minting_only",
            }

        if operation == "press":
            return {
                "contract_mode": "single_use_url_scoped_mutation",
                "current_execution_mode": "single_use_url_scoped" if has_url else "platform_session_candidate",
                "authoritative_target_required": False,
                "resumable_continuity": "not_required",
            }

        if operation in {"click", "type"}:
            return {
                "contract_mode": "authoritative_target_mutation",
                "current_execution_mode": "single_use_url_scoped" if has_url else "resumable_session_required",
                "authoritative_target_required": True,
                "resumable_continuity": "deferred",
            }

        return {}

    @staticmethod
    def _derive_browser_continuity_resolution(
        action: RuntimeSkillActionDescriptor,
        validated_arguments: Dict[str, Any],
        browser_continuity: Dict[str, Any],
    ) -> Dict[str, Any]:
        action_metadata = action.metadata if isinstance(action.metadata, dict) else {}
        if action_metadata.get("tool_family") != "agent_browser":
            return {}

        operation = action_metadata.get("operation")
        url = validated_arguments.get("url")
        session_id = validated_arguments.get("session_id")
        tab_id = validated_arguments.get("tab_id")
        element_ref = validated_arguments.get("element_ref")

        has_url = isinstance(url, str) and bool(url.strip())
        has_session = isinstance(session_id, str) and bool(session_id.strip())
        has_tab = isinstance(tab_id, str) and bool(tab_id.strip())
        has_target = isinstance(element_ref, str) and bool(element_ref.strip())

        if operation not in {"open", "snapshot", "screenshot", "press", "click", "type"}:
            return {}

        if operation in {"open", "snapshot", "screenshot"}:
            return {
                "resolver_contract_version": 1,
                "resolution_mode": "single_use_url" if has_url else "no_resolution_required",
                "continuity_status": "single_use_ready" if has_url else "not_required",
                "session_lookup_required": False,
                "tab_lookup_required": False,
                "target_lookup_required": False,
                "provided_context": {
                    "has_url": has_url,
                    "has_session_id": has_session,
                    "has_tab_id": has_tab,
                    "has_element_ref": has_target,
                },
                "missing_context": [],
            }

        if operation == "press":
            return {
                "resolver_contract_version": 1,
                "resolution_mode": "single_use_url" if has_url else "session_tab_lookup_candidate",
                "continuity_status": "single_use_ready" if has_url else "resolver_deferred",
                "session_lookup_required": False if has_url else True,
                "tab_lookup_required": False if has_url else True,
                "target_lookup_required": False,
                "provided_context": {
                    "has_url": has_url,
                    "has_session_id": has_session,
                    "has_tab_id": has_tab,
                    "has_element_ref": has_target,
                },
                "missing_context": ([] if has_url else [
                    *([] if has_session else ["session_id"]),
                    *([] if has_tab else ["tab_id"]),
                ]),
            }

        missing_context = [
            *([] if has_session else ["session_id"]),
            *([] if has_tab else ["tab_id"]),
            *([] if has_target else ["element_ref"]),
        ]
        return {
            "resolver_contract_version": 1,
            "resolution_mode": "single_use_url_with_authoritative_target" if has_url else "session_tab_target_lookup",
            "continuity_status": "single_use_ready" if has_url else "resolver_deferred",
            "session_lookup_required": False if has_url else True,
            "tab_lookup_required": False if has_url else True,
            "target_lookup_required": True,
            "provided_context": {
                "has_url": has_url,
                "has_session_id": has_session,
                "has_tab_id": has_tab,
                "has_element_ref": has_target,
            },
            "missing_context": [] if has_url else missing_context,
            "contract_mode": browser_continuity.get("contract_mode"),
        }

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
        validation_errors.extend(SkillPolicyGate._validate_browser_target_binding(action, validated_arguments))

        action_metadata = action.metadata if isinstance(action.metadata, dict) else {}
        runtime_metadata_expectations = (
            action_metadata.get("runtime_metadata_expectations")
            if isinstance(action_metadata.get("runtime_metadata_expectations"), dict)
            else {}
        )
        runtime_metadata = {
            "operation": action_metadata.get("operation"),
            "tool_family": action_metadata.get("tool_family"),
            "mapped_tool": mapped_tool,
        }
        for key in runtime_metadata_expectations.get("required", []):
            if key == "operation":
                continue
            runtime_metadata[key] = validated_arguments.get(key)
        for key in runtime_metadata_expectations.get("optional", []):
            if key not in runtime_metadata and key in validated_arguments:
                runtime_metadata[key] = validated_arguments.get(key)
        browser_continuity = SkillPolicyGate._derive_browser_continuity_metadata(action, validated_arguments)
        browser_continuity_resolution = SkillPolicyGate._derive_browser_continuity_resolution(
            action,
            validated_arguments,
            browser_continuity,
        )

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
                "tool_family": action_metadata.get("tool_family"),
                "operation": action_metadata.get("operation"),
                "runtime_metadata_expectations": runtime_metadata_expectations,
                "runtime_metadata": runtime_metadata,
                "browser_continuity": browser_continuity,
                "browser_continuity_resolution": browser_continuity_resolution,
            },
        )
