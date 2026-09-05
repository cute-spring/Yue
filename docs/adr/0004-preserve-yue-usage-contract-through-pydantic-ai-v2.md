# Preserve the Yue usage contract through Pydantic AI V2

Yue will retain `prompt_tokens` and `completion_tokens` in its application and persistence contract while its usage adapter translates Pydantic AI V2 `input_tokens` and `output_tokens`. A temporary V1 fallback is permitted only during the compatibility stage, while observability queries are migrated separately to V2 instrumentation fields.

