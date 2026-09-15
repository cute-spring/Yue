# Session Context Deployment Guide

Yue includes its session-context implementation in `backend/app/modules/session_context/`.
It is part of the backend application rather than a separately installed Python package.

## Local development

Clone Yue and run the normal setup flow:

```bash
./setup.sh
./start.sh
```

No sibling repository, wheel, or session-context-specific environment variable is required.

## Docker deployment

Build from the Yue repository root with the normal deployment script:

```bash
./deploy_docker.sh
```

The image copies only Yue sources and has no build-context dependency on another repository.

## Quick validation

```bash
cd backend
python3 -c 'from app.modules import session_context; print(session_context.__file__)'
```

Then run the session-context host tests.
