"""Optional immutable input snapshot shared by fitting commands."""

import hashlib
import json
from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path

ACTIVE_CATALOG = ContextVar("benchmark_input_catalog", default=None)


@lru_cache(maxsize=2)
def load_catalog(path):
    path = Path(path)
    manifest = json.loads((path / "audit.json").read_text())
    for name, digest in manifest["files_sha256"].items():
        if hashlib.sha256((path / name).read_bytes()).hexdigest() != digest:
            raise ValueError("input snapshot digest mismatch: " + name)
    sources = {}
    with (path / "sources.jsonl").open() as stream:
        for line in stream:
            r = json.loads(line)
            if r["schema_version"] != "benchmark-source-v1":
                raise ValueError("unsupported source snapshot")
            sources.setdefault(r["view"], []).append(r["record"])
    sources["_manifest"] = manifest
    sources["_spec_index"] = {(r["source_url"], r["track"]): r for r in sources["spec"]}
    return sources


def source_view(default_path, view):
    selected = ACTIVE_CATALOG.get()
    if selected is not None:
        # Consumers receive independent data, never mutable cached shared records.
        return json.loads(json.dumps(load_catalog(str(selected))[view]))
    return [json.loads(line) for line in Path(default_path).read_text().splitlines()]


def snapshot_identity():
    selected = ACTIVE_CATALOG.get()
    if selected is None:
        return {"mode": "live_source_adapters"}
    path = Path(selected) / "audit.json"
    return {"mode": "input_snapshot", "path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
