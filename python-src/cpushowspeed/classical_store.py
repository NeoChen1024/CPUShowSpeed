"""Classical and SPEC89/92 results from the built database, and their pairing over resolved systems.

A result is one source row or report column: its classical scores (Dhrystone,
Whetstone, LINPACK) and SPEC values were reported together. Two results are
paired only when both resolve to the same `system_id`; names are never
compared. Pairing records, but does not establish, equal configuration: OS,
compiler, cache and FPU options remain unverified unless both values come from
one result (`same_result`).
"""

import json
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field

CLASSICAL = (
    "Dhrystone:v1.1_DMIPS",
    "Dhrystone:v2.1_DMIPS",
    "Whetstone:MWIPS",
    "Whetstone:MWIPS_DP",
    "Whetstone:MWIPS_SP",
    "LINPACK:n100_MFLOPS",
)
TARGETS = ("SPECint89", "SPECint92", "SPECbase_int92", "SPECrate_int92", "SPECrate_base_int92")
# The metric table names one CPU92 quantity twice: per suite for SPEC disclosures,
# by historical label for collections. Targets use the historical label.
SAME_METRIC = {
    "cpu92:integer:rate:peak": "SPECrate_int92",
    "cpu92:integer:rate:base": "SPECrate_base_int92",
    "cpu92:integer:speed:peak": "SPECint92",
    "cpu92:integer:speed:base": "SPECbase_int92",
}
SCOPES = (
    "classical:%",
    "reviewed-vector:%",
    "historical-spec:spec89",
    "historical-spec:spec92-dec",
    "spec:cpu92",
)
BRIDGE_SCOPE = "historical-spec:spec89-bridge"
CLOCK_TOLERANCE = 0.01


def family(metric: str) -> str:
    return metric.split(":", 1)[0]


@dataclass
class Result:
    result_id: str
    scope: str
    system: str
    system_id: str
    processor_entity: str
    clock_mhz: float | None
    cpu_count: float | None
    os: str
    source_url: str
    reference: bool = False
    values: dict = field(default_factory=dict)
    observation_ids: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict, repr=False)

    @property
    def classical(self) -> dict:
        return {m: v for m, v in self.values.items() if m in CLASSICAL}

    @property
    def targets(self) -> dict:
        return {m: v for m, v in self.values.items() if m in TARGETS}


def _reference(raw: dict) -> bool:
    inner = raw.get("raw_record") if isinstance(raw.get("raw_record"), dict) else {}
    return inner.get("measurement_type") == "reference_definition" or "reference_definition" in str(inner.get("review_flags", ""))


def results(db, scopes=SCOPES) -> list[Result]:
    """Every result in the scopes with any classical or target metric, ordered by result ID."""
    found = {}
    where = " OR ".join("scope LIKE ?" for _ in scopes)
    query = (
        "SELECT result_id, scope, metric_id, value, observation_id, system_id, processor_entity, record "
        f"FROM observation WHERE ({where}) ORDER BY result_id, metric_id"
    )
    for result_id, scope, metric, value, oid, system_id, entity, record in db.execute(query, scopes):
        metric = SAME_METRIC.get(metric, metric)
        if metric not in CLASSICAL + TARGETS:
            continue
        if result_id not in found:
            o = json.loads(record)
            hw, run, raw = o["hardware"], o["run"], o["raw"] if isinstance(o["raw"], dict) else {}
            found[result_id] = Result(
                result_id,
                scope,
                o["system"],
                system_id or "",
                entity or "",
                hw.get("nominal_mhz"),
                hw.get("enabled_chips") or hw.get("legacy_cpu_count"),
                run.get("os", ""),
                o["source"]["url"],
                _reference(raw),
                raw=raw,
            )
        found[result_id].values[metric] = value
        found[result_id].observation_ids[metric] = oid
    return [found[k] for k in sorted(found)]


def clock_relation(a: Result, b: Result) -> str:
    if not a.clock_mhz or not b.clock_mhz:
        return "unknown"
    return "compatible" if abs(a.clock_mhz - b.clock_mhz) <= CLOCK_TOLERANCE * max(a.clock_mhz, b.clock_mhz) else "conflict"


def pair(classical: Result, target: Result, scaling: bool) -> tuple[dict, str]:
    """Classical scores carried to the target's configuration, or the reason they cannot be.

    LINPACK is never clock-scaled. Dhrystone and Whetstone are scaled linearly to
    the target clock only when `scaling` and both results resolve to one processor.
    """
    if classical.cpu_count not in (None, 1):
        return {}, "classical_cpu_count_not_one"
    if target.reference:
        return {}, "reference_definition"
    if classical is target:
        return dict(classical.classical), "same_result"
    clocks = clock_relation(classical, target)
    if clocks != "conflict":
        return dict(classical.classical), f"clock_{clocks}"
    if not scaling:
        return {}, "clock_conflict"
    if not classical.processor_entity or classical.processor_entity != target.processor_entity:
        return {}, "clock_conflict_processor_unverified"
    ratio = target.clock_mhz / classical.clock_mhz
    scaled = {m: v * ratio for m, v in classical.classical.items() if family(m) != "LINPACK"}
    return scaled, "linear_clock_scaled" if scaled else "clock_conflict"


def pairings(rows: list[Result], scaling: bool = False) -> list[dict]:
    """Each target result with every classical result of its system: one row per pairing, with its status."""
    by_system = defaultdict(list)
    for r in rows:
        if r.classical and r.system_id:
            by_system[r.system_id].append(r)
    out = []
    for target in rows:
        if not target.targets:
            continue
        candidates = [target] if target.classical else []
        candidates += [c for c in by_system.get(target.system_id, []) if c is not target] if target.system_id else []
        for c in candidates:
            scores, status = pair(c, target, scaling)
            out.append(dict(target=target, classical=c, scores=scores, status=status))
    return out


def target_value(target: Result, metric: str) -> float | None:
    """Target value; a rate score counts every CPU, so a reported CPU count other than one excludes it.

    An unreported count (the DEC report columns) is kept and qualified as unverified.
    """
    value = target.values.get(metric)
    if value and metric.startswith("SPECrate") and target.cpu_count not in (None, 1):
        return None
    return value


def node_scores(paired: list[dict]) -> dict:
    """Median log score per metric over the accepted pairings of one target."""
    logs = defaultdict(list)
    for p in paired:
        for m, v in p["scores"].items():
            logs[m].append(math.log(v))
    return {m: statistics.median(v) for m, v in sorted(logs.items())}
