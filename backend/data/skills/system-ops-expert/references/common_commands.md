# Common Commands for Yue Project

## Backend Operations

### Testing
- `pytest`: Run all tests.
- `pytest backend/tests/test_api.py`: Run specific tests.
- `pytest --cov=backend`: Run tests with coverage report.

### Linting & Formatting
- `flake8 backend/`: Check for linting errors.
- `black backend/`: Format the codebase.
- `mypy backend/`: Type checking.

### Dependency Management
- `pip list`: List installed packages.
- `pip check`: Verify dependencies.
- `pip install -r backend/requirements.txt`: Install project dependencies.

### Codebase Search
- `grep -r "pattern" backend/`: Recursively search for a pattern in the backend.
- `find backend/ -name "*.py"`: List all Python files.

## Environment & Logs
- `env`: Check environment variables.
- `ls -l backend/data/logs`: Check log files.
- `tail -f backend/data/logs/app.log`: Tail the application log.

## System Status & Monitoring

### Resource Usage
- `top -l 1`: Show system resource usage (non-interactive on macOS).
- `df -h`: Check disk space availability.
- `memory_pressure`: Check memory pressure and statistics on macOS.
- `uptime`: Show how long the system has been running and the load average.

### Processes & Network
- `ps aux | grep <process_name>`: Search for running processes.
- `lsof -i -P -n | grep LISTEN`: List all listening network ports.
- `netstat -an | grep LISTEN`: Alternative to list listening ports.

## Cleanup
- `find . -type d -name "__pycache__" -exec rm -rf {} +`: Remove all __pycache__ directories.
- `rm -rf .pytest_cache`: Remove pytest cache.
