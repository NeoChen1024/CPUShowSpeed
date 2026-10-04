"""OCR environment defaults, retaining the former local.env convention."""

import os

from dotenv import dotenv_values, find_dotenv

_LOCAL = dotenv_values(find_dotenv("local.env"))


def value(name, default):
    raw = os.environ.get(name, _LOCAL.get(name))
    return default if raw is None else type(default)(raw)


API_BASE = value("VLLM_API_BASE", "http://localhost:8000/v1")
API_KEY = value("VLLM_API_KEY", "EMPTY")
MAX_RETRIES = value("MAX_VLLM_RETRIES", 5)
