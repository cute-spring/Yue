# Require explicit output completion behavior for side-effecting tools

Yue will not set a global Pydantic AI `end_strategy` during the V2 migration because no current agent combines structured output with function tools. Any future agent that combines structured output with side-effecting tools must set `end_strategy` explicitly, defaulting to `early` unless post-output execution is intentional and tested.

