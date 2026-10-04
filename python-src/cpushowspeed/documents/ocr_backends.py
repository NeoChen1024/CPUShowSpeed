"""Model-specific page adapters used by the shared OCR pipeline."""

import re

from cpushowspeed.documents import chandra, infinity

BACKENDS = {"chandra": chandra, "infinity": infinity}


def detect_backend(model: str) -> str:
    """Match model-family tokens, ignoring repository paths and arbitrary suffixes."""
    name = model.strip().rstrip("/").rsplit("/", 1)[-1].casefold()
    patterns = {
        "chandra": r"(?<![a-z0-9])chandra(?![a-z0-9])",
        "infinity": r"(?<![a-z0-9])infinity[-_. ]+parser[-_. ]*2[-_. ]+flash(?![a-z0-9])",
    }
    matches = [backend for backend, pattern in patterns.items() if re.search(pattern, name)]
    if len(matches) != 1:
        raise ValueError(f"cannot unambiguously detect OCR backend from model {model!r}; specify --backend chandra|infinity")
    return matches[0]


class LayoutError(ValueError):
    """A model response that needs another inference attempt."""


def get_backend(name: str):
    return BACKENDS[name]


def sampling(name: str, attempts: int) -> dict:
    adapter = get_backend(name)
    return {"temperature": min(0.2 * attempts, 0.8), "top_p": adapter.TOP_P[bool(attempts)]}


def compatible_settings(stored: dict, current: dict) -> bool:
    """Allow verified Chandra 0.2.0 runs to resume without rewriting their provenance."""
    previous = dict(stored)
    if "backend" not in previous and previous.get("chandra_version") == "0.2.0":
        previous.pop("chandra_version")
        previous.update(backend="chandra", adapter_version=1)
    return previous == current
