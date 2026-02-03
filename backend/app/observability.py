import logging
import os
import uuid
from contextvars import ContextVar, Token


TRACE_HEADER = "X-Request-Id"

_trace_id_var: ContextVar[str] = ContextVar("trace_id", default="-")


def get_trace_id() -> str:
    return _trace_id_var.get()


def set_trace_id(trace_id: str) -> Token[str]:
    token = _trace_id_var.set(trace_id)
    return token


def reset_trace_id(token: Token[str]) -> None:
    _trace_id_var.reset(token)


def new_trace_id() -> str:
    return uuid.uuid4().hex


class TraceIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        trace_id = get_trace_id()
        setattr(record, "trace_id", trace_id)
        return True


def setup_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)

    if any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        for handler in root.handlers:
            handler.addFilter(TraceIdFilter())
        return

    handler = logging.StreamHandler()
    handler.addFilter(TraceIdFilter())
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s trace_id=%(trace_id)s %(message)s"
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)
