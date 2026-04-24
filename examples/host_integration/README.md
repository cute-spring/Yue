# Minimal Host Integration

This folder demonstrates how to wire Skill Runtime Core in a same-stack FastAPI host using:
- `register_stage4_lite_host_runtime_adapter_bundle(...)`
- `build_skill_runtime_bootstrap_spec_from_env(...)`
- `bootstrap_skill_runtime_app(...)`

## Files
- `minimal_fastapi_host.py`: minimal reusable host wiring
- `.env.example`: neutral runtime config + host alias examples

## Day 1 Smoke Commands
```bash
cd /Users/gavinzhang/ws-ai-recharge-2026/Yue
set -a; source examples/host_integration/.env.example; set +a
PYTHONPATH=/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend uvicorn examples.host_integration.minimal_fastapi_host:app --host 127.0.0.1 --port 8010
```

In another terminal:
```bash
curl -s http://127.0.0.1:8010/api/skills/summary
curl -s http://127.0.0.1:8010/api/skill-imports/
```
