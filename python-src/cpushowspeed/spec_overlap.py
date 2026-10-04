"""Shared source-checked SPEC result matching and clustered ratio statistics."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import re
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin

import numpy as np
from cpushowspeed.calibration import absolute_error_percent, quantile
from cpushowspeed.execution_policy import agreement

BASE_URL = "https://www.spec.org"
INTERVAL_FIELDS = ("confidence_level", "bootstrap_replicates", "bootstrap_seed", "bootstrap_unit", "quantile_method")
INTERVAL_METADATA = dict(zip(INTERVAL_FIELDS, (0.95, 10000, 892026, "processor_configuration", "linear")))

PAIR_FIELDS = [
    "old_generation",
    "new_generation",
    "old_result_id",
    "new_result_id",
    "system_key",
    "processor_key",
    "chips",
    "old_cores",
    "new_cores",
    "old_enabled_threads_per_core",
    "new_enabled_threads_per_core",
    "old_system",
    "new_system",
    "old_processor",
    "new_processor",
    "old_clock_mhz",
    "new_clock_mhz",
    "old_memory_mib",
    "new_memory_mib",
    "old_os",
    "new_os",
    "old_compiler",
    "new_compiler",
    "old_peak",
    "new_peak",
    "old_base",
    "new_base",
    "peak_ratio",
    "base_ratio",
    "match_tier",
    "old_source_url",
    "new_source_url",
    "old_source_container_sha256",
    "new_source_container_sha256",
    "source_check",
    "base_execution_status",
    "peak_execution_status",
    "base_unfiltered_ratio",
    "peak_unfiltered_ratio",
    "old_processor_basis",
    "new_processor_basis",
]


@dataclass(frozen=True)
class Result:
    generation: str
    result_id: str
    system: str
    system_key: str
    processor: str
    processor_key: str
    chips: int
    cores: int | None
    enabled_threads_per_core: int | None
    clock_mhz: float | None
    memory_mib: float | None
    os: str
    compiler: str
    peak: float | None
    base: float | None
    source_url: str
    source_container_sha256: str
    track: str = ""
    # How processor_key was resolved; "broad_family" keys cannot pair hardware.
    processor_basis: str = ""
    execution: dict = field(default_factory=dict, compare=False, hash=False)
    raw_fields: dict = field(default_factory=dict, compare=False, hash=False)


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def processor_text_key(value: str) -> str:
    """Remove disclosure prose while retaining model, generation, and SKU tokens."""
    name = value.lower()
    name = re.sub(r"\([^)]*\)", "", name)
    name = re.sub(r"\b(?:revision|rev)\b.*", "", name)
    name = re.sub(r"\d+(?:\.\d+)?\s*[gm]hz", "", name)
    for word in ("processor", "cpu", "chip", "intel", "amd", "ibm", "powerpc", "alpha", "microprocessor", "tm", "core"):
        name = re.sub(r"\b" + word + r"\b", " ", name)
    return normalized(name)


def clock_mhz(raw: dict[str, str], processor: str) -> float | None:
    value = raw.get("Processor MHz", "").strip()
    if re.fullmatch(r"\d+(?:\.\d+)?", value):
        return float(value)
    for candidate in (processor, raw["System"]):
        match = re.search(r"(\d+(?:\.\d+)?)\s*(GHz|MHz)", candidate, re.I)
        if match:
            return float(match.group(1)) * (1000 if match.group(2).lower() == "ghz" else 1)
    return None


def memory_mib(value: str) -> float | None:
    text = value.strip()
    match = re.match(r"(?:(\d+)\s*[x×*]\s*)?(\d+(?:\.\d+)?)\s*(TB|GB|MB)\b", text, re.I)
    if match:
        count = int(match.group(1)) if match.group(1) else 1
        return count * float(match.group(2)) * {"TB": 1024 * 1024, "GB": 1024, "MB": 1}[match.group(3).upper()]
    return None


def positive(value: str | None) -> float | None:
    try:
        score = float(value or "")
    except ValueError:
        return None
    return score if math.isfinite(score) and score > 0 else None


def disclosure_url(disclosure: str) -> str:
    match = re.search(r'<A\s+HREF="([^"]+\.html)"', disclosure, re.I)
    if not match:
        raise ValueError(f"result has no HTML disclosure: {disclosure[:100]}")
    url = urljoin(BASE_URL, match.group(1)).replace("https://www.spec.org/osg/", "https://www.spec.org/")
    if not url.startswith(("https://www.spec.org/", "https://spec.org/")):
        raise ValueError(f"unexpected disclosure URL: {url}")
    return url


def read_checked_bulk(path: Path) -> tuple[list[dict[str, str]], str]:
    body = path.read_bytes()
    meta = json.loads(path.with_name(path.name + ".meta.json").read_text())
    digest = hashlib.sha256(body).hexdigest()
    if digest != meta["sha256"] or not str(meta["source_url"]).startswith("https://www.spec.org/cgi-bin/osgresults?"):
        raise ValueError(f"bulk source metadata mismatch: {path}")
    with path.open(encoding="latin1", newline="") as stream:
        rows = [{key.strip(): value for key, value in row.items()} for row in csv.DictReader(stream)]
    return rows, digest


def _pair(old: Result, new: Result, tier: str, source_check: str = "bulk_hash_checked") -> dict[str, object]:
    row = {
        "old_generation": old.generation,
        "new_generation": new.generation,
        "old_result_id": old.result_id,
        "new_result_id": new.result_id,
        "system_key": old.system_key,
        "processor_key": old.processor_key,
        "chips": old.chips,
        "old_cores": old.cores or "",
        "new_cores": new.cores or "",
        "old_enabled_threads_per_core": old.enabled_threads_per_core or "",
        "new_enabled_threads_per_core": new.enabled_threads_per_core or "",
        "old_system": old.system,
        "new_system": new.system,
        "old_processor": old.processor,
        "new_processor": new.processor,
        "old_clock_mhz": old.clock_mhz or "",
        "new_clock_mhz": new.clock_mhz or "",
        "old_memory_mib": old.memory_mib or "",
        "new_memory_mib": new.memory_mib or "",
        "old_os": old.os,
        "new_os": new.os,
        "old_compiler": old.compiler,
        "new_compiler": new.compiler,
        "old_peak": old.peak or "",
        "new_peak": new.peak or "",
        "old_base": old.base or "",
        "new_base": new.base or "",
        "peak_ratio": old.peak / new.peak if old.peak and new.peak else "",
        "base_ratio": old.base / new.base if old.base and new.base else "",
        "match_tier": tier,
        "old_source_url": old.source_url,
        "new_source_url": new.source_url,
        "old_source_container_sha256": old.source_container_sha256,
        "new_source_container_sha256": new.source_container_sha256,
        "source_check": source_check,
        "old_processor_basis": old.processor_basis,
        "new_processor_basis": new.processor_basis,
    }

    for mode in ("base", "peak"):
        row[mode + "_execution_status"] = agreement(old, new, mode)
        row[mode + "_unfiltered_ratio"] = row[mode + "_ratio"]
        if row[mode + "_execution_status"] == "confirmed_count_conflict":
            row[mode + "_ratio"] = ""
    return row


def _same_text(left: str, right: str) -> bool:
    return " ".join(left.lower().split()) == " ".join(right.lower().split())


def automatic_pairs(results: dict[str, list[Result]], older: str, newer: str) -> list[dict[str, object]]:
    old_by_key: dict[tuple[str, str, int], list[Result]] = defaultdict(list)
    new_by_key: dict[tuple[str, str, int], list[Result]] = defaultdict(list)
    for item in results[older]:
        if item.system_key and item.processor_key:
            old_by_key[item.system_key, item.processor_key, item.chips].append(item)
    for item in results[newer]:
        if item.system_key and item.processor_key:
            new_by_key[item.system_key, item.processor_key, item.chips].append(item)
    pairs: list[dict[str, object]] = []
    for key in sorted(old_by_key.keys() & new_by_key.keys()):
        for old in old_by_key[key]:
            for new in new_by_key[key]:
                clock_agrees = old.clock_mhz and new.clock_mhz and abs(old.clock_mhz / new.clock_mhz - 1) <= 0.01
                memory_agrees = old.memory_mib and new.memory_mib and old.memory_mib == new.memory_mib
                cores_agree = old.cores is None or new.cores is None or old.cores == new.cores
                threads_agree = (
                    old.enabled_threads_per_core is None
                    or new.enabled_threads_per_core is None
                    or old.enabled_threads_per_core == new.enabled_threads_per_core
                )
                # A family that spans distinct SKUs at one clock establishes equal hardware only
                # when both disclosures name the system identically (e.g. "Alder System (200MHz, 256KB L2)").
                processor_known = "broad_family" not in (old.processor_basis, new.processor_basis) or _same_text(
                    old.system, new.system
                )
                near = clock_agrees and memory_agrees and cores_agree and threads_agree and processor_known
                tier = "hardware_near" if near else "name_cpu_chips_only"
                pairs.append(_pair(old, new, tier))
    return pairs


def _processor_family(key: str) -> str:
    for token, family in (
        ("xeon", "Xeon"),
        ("epyc", "EPYC"),
        ("opteron", "Opteron"),
        ("pentium", "Pentium"),
        ("athlon", "Athlon"),
        ("rs64", "RS64"),
        ("power", "POWER"),
        ("sparc", "SPARC"),
        ("parisc", "PA-RISC"),
        ("21264", "Alpha"),
        ("21164", "Alpha"),
    ):
        if token in key:
            return family
    return "Other"


def ratio_statistics(rows: list[dict[str, object]], mode: str, eligible_tiers: set[str] | None = None) -> dict[str, object] | None:
    tiers = eligible_tiers if eligible_tiers is not None else {"reviewed_detail", "hardware_near"}
    selected = [row for row in rows if row["match_tier"] in tiers and row[f"{mode}_ratio"] != ""]
    systems: dict[tuple[str, str, int, float], list[dict[str, object]]] = defaultdict(list)
    for row in selected:
        clock = float(row["old_clock_mhz"]) if row["old_clock_mhz"] != "" else 0.0
        systems[str(row["system_key"]), str(row["processor_key"]), int(row["chips"]), round(clock, 1)].append(row)
    processors: dict[tuple[str, int, float], list[tuple[float, float, float]]] = defaultdict(list)
    for key, members in systems.items():
        log_ratio = statistics.median(math.log(float(row[f"{mode}_ratio"])) for row in members)
        log_old = statistics.median(math.log(float(row[f"old_{mode}"])) for row in members)
        log_new = statistics.median(math.log(float(row[f"new_{mode}"])) for row in members)
        processors[key[1:]].append((log_ratio, log_old, log_new))
    if len(processors) < 3:
        return None
    config_values = {
        key: tuple(statistics.median(value[index] for value in group) for index in range(3)) for key, group in processors.items()
    }
    logs = [value[0] for value in config_values.values()]
    center = statistics.mean(logs)
    rng = random.Random(INTERVAL_METADATA["bootstrap_seed"])
    ordered_logs = [config_values[key][0] for key in sorted(config_values)]
    bootstrap = [
        math.exp(statistics.mean(rng.choices(ordered_logs, k=len(logs)))) for _ in range(INTERVAL_METADATA["bootstrap_replicates"])
    ]
    low, high = np.quantile(bootstrap, [0.025, 0.975], method="linear")
    x = np.asarray([value[2] for value in config_values.values()])
    y = np.asarray([value[1] for value in config_values.values()])
    slope = float(np.polyfit(x, y, 1)[0]) if float(np.var(x)) > 0 else None
    by_family: dict[str, list[float]] = defaultdict(list)
    for key, value in config_values.items():
        by_family[_processor_family(key[0])].append(value[0])
    heldout = [absolute_error_percent((sum(logs) - value) / (len(logs) - 1) - value) / 100 for value in logs]
    return {
        "factor_old_per_new": math.exp(center),
        "log_factor": center,
        "processor_configs": len(processors),
        "system_groups": len(systems),
        "candidate_pairings_used": len(selected),
        "system_weighted_factor": math.exp(
            statistics.mean(
                statistics.median(math.log(float(row[f"{mode}_ratio"])) for row in members) for members in systems.values()
            )
        ),
        "config_ratio_min": math.exp(min(logs)),
        "config_ratio_max": math.exp(max(logs)),
        "cluster_bootstrap_95_low": float(low),
        "cluster_bootstrap_95_high": float(high),
        **INTERVAL_METADATA,
        "heldout_p95_absolute_pct_error": quantile(heldout, 0.95),
        "model_center_p95_percent": 100 * quantile(heldout, 0.95),
        "heldout_median_absolute_pct_error": statistics.median(heldout),
        "loglog_slope_diagnostic": slope,
        "processor_family_factors": {
            family: {"processor_configs": len(values), "factor_old_per_new": math.exp(statistics.mean(values))}
            for family, values in sorted(by_family.items())
        },
    }
