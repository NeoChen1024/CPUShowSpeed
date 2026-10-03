"""Extracted benchmark-observation-v2 rows joined to sources, metrics, identity and chronology."""

import json
from collections import Counter
from pathlib import Path

from cpushowspeed.benchmark_records import SCHEMA

OBSERVATIONS = Path("data/derived/schema/observations.jsonl")
COLUMNS = (
    "observation_id TEXT PRIMARY KEY",
    "result_id TEXT NOT NULL",
    "scope TEXT NOT NULL",
    "metric_id TEXT NOT NULL",
    "registry_metric TEXT",
    "mode TEXT",
    "track TEXT",
    "value REAL NOT NULL",
    "unit TEXT",
    "evidence_class TEXT",
    "verification TEXT",
    "source_id TEXT",
    "source_basis TEXT",
    "hardware_id TEXT",
    "system_id TEXT",
    "processor_entity TEXT",
    "date_kind TEXT",
    "year INTEGER",
    "year_low INTEGER",
    "year_high INTEGER",
    "record TEXT NOT NULL",
)


class SourceIndex:
    """Content hash, then a registry key the adapter cites, then an address claimed by exactly
    one source, then the longest dataset member prefix."""

    def __init__(self, sources):
        self.hash, self.legacy, urls = {}, {}, {}
        for s in sources:
            if s.get("hash"):
                self.hash[s["hash"]] = s["source_id"]
            for key in s.get("legacy_ids", ()):
                self.legacy[key] = s["source_id"]
            for url in {s.get("url"), s.get("final_url"), *(s.get("alternate_urls") or [])} - {None}:
                urls.setdefault(url, set()).add(s["source_id"])
        self.url = {u: next(iter(ids)) for u, ids in urls.items() if len(ids) == 1}
        self.prefix = sorted(
            ((s["member_url_prefix"], s["source_id"]) for s in sources if s.get("member_url_prefix")), key=lambda p: -len(p[0])
        )

    def resolve(self, source):
        for key in ("sha256", "blake3"):
            if source.get(key) in self.hash:
                return self.hash[source[key]], "hash"
        if source.get("legacy_id") in self.legacy:
            return self.legacy[source["legacy_id"]], "registry_key"
        url = source.get("url") or ""
        if url in self.url:
            return self.url[url], "url"
        for prefix, source_id in self.prefix:
            if url.startswith(prefix):
                return source_id, "dataset_member"
        return None, None


def build_observations(db, tables):
    """Table `observation`: one row per extracted score with the entities and year it resolved to."""
    if not OBSERVATIONS.exists():
        return {"observations": "skipped: run `cpushowspeed data extract`"}
    from cpushowspeed.curated import sha256

    metrics = {m["metric_id"]: m for m in tables["metric"]}
    sources = SourceIndex(tables["source"])
    chronology = {
        r[0]: r[1:]
        for r in db.execute(
            "SELECT result_id, hardware_id, system_id, processor_entity, date_kind, year, year_low, year_high FROM result_chronology"
        )
    }
    db.execute(f"CREATE TABLE observation ({', '.join(COLUMNS)})")
    counts = Counter()
    rows = []
    with OBSERVATIONS.open() as stream:
        for line in stream:
            o = json.loads(line)
            if o["schema_version"] != SCHEMA:
                raise ValueError(f"unsupported observation schema: {o['schema_version']}")
            metric = metrics.get(o["metric_id"])
            if metric is None:
                raise ValueError(f"observation metric not in metric table: {o['metric_id']}")
            source_id, basis = sources.resolve(o["source"])
            chrono = chronology.get(o["result_id"])
            if chrono is None:
                raise ValueError(f"observation result missing from result_chronology: {o['result_id']}")
            counts["observations"] += 1
            counts["source:" + (basis or "unresolved") + ":" + o["scope"]] += 1
            rows.append(
                (
                    o["observation_id"],
                    o["result_id"],
                    o["scope"],
                    o["metric_id"],
                    metric["registry_metric"],
                    o["mode"],
                    o["track"],
                    o["value"],
                    o["unit"],
                    o["evidence_class"],
                    o["verification"],
                    source_id,
                    basis,
                    *chrono,
                    line.rstrip("\n"),
                )
            )
    db.executemany(f"INSERT INTO observation VALUES ({', '.join('?' for _ in COLUMNS)})", rows)
    for column in ("result_id", "metric_id", "hardware_id", "system_id"):
        db.execute(f"CREATE INDEX observation_{column} ON observation ({column})")
    meta = {"observations_sha256": sha256(OBSERVATIONS)}
    meta.update({f"observations:{k}": str(v) for k, v in sorted(counts.items())})
    return meta
