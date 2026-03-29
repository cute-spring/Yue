from typing import Any, List


def persist_action_lifecycle_events(
    *,
    lifecycle_results: List[Any],
    ctx: Any,
    emitter: Any,
    deps: Any,
) -> List[str]:
    payloads: List[str] = []
    for lifecycle_result in lifecycle_results:
        for event_payload in lifecycle_result.event_payloads:
            enveloped_event = emitter.event_payload(event_payload)
            deps.chat_service.add_action_event(
                ctx.chat_id,
                enveloped_event,
                assistant_turn_id=ctx.assistant_turn_id,
                run_id=ctx.run_id,
            )
            payloads.append(deps.serialize_sse_payload(enveloped_event))
    return payloads
