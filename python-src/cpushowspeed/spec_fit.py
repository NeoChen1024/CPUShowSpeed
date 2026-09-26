"""Exploratory, source-linked SPEC integer-speed generation fitting."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import re
import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urljoin

import click
import numpy as np
from cpushowspeed.plot import collect_cpu92

GENERATIONS = ("cpu92", "cpu95", "cpu2000", "cpu2006", "cpu2017", "cpu2026")
BASE_URL = "https://www.spec.org"
METHOD_VERSION = "integer-speed-fit-v1"
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


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _processor_key(value: str) -> str:
    """Remove disclosure prose while retaining model, generation, and SKU tokens."""
    name = value.lower()
    name = re.sub(r"\([^)]*\)", "", name)
    name = re.sub(r"\b(?:revision|rev)\b.*", "", name)
    name = re.sub(r"\d+(?:\.\d+)?\s*[gm]hz", "", name)
    for word in ("processor", "cpu", "chip", "intel", "amd", "ibm", "powerpc", "alpha", "microprocessor", "tm", "core"):
        name = re.sub(r"\b" + word + r"\b", " ", name)
    return _normalized(name)


def _frequency(raw: dict[str, str], processor: str) -> float | None:
    value = raw.get("Processor MHz", "").strip()
    if re.fullmatch(r"\d+(?:\.\d+)?", value):
        return float(value)
    for candidate in (processor, raw["System"]):
        match = re.search(r"(\d+(?:\.\d+)?)\s*(GHz|MHz)", candidate, re.I)
        if match:
            return float(match.group(1)) * (1000 if match.group(2).lower() == "ghz" else 1)
    return None


def _memory_mib(value: str) -> float | None:
    text = value.strip()
    match = re.match(r"(?:(\d+)\s*[x×*]\s*)?(\d+(?:\.\d+)?)\s*(TB|GB|MB)\b", text, re.I)
    if match:
        count = int(match.group(1)) if match.group(1) else 1
        return count * float(match.group(2)) * {"TB": 1024 * 1024, "GB": 1024, "MB": 1}[match.group(3).upper()]
    return None


def _positive(value: str | None) -> float | None:
    try:
        score = float(value or "")
    except ValueError:
        return None
    return score if math.isfinite(score) and score > 0 else None


def _source_url(disclosure: str) -> str:
    match = re.search(r'<A\s+HREF="([^"]+\.html)"', disclosure, re.I)
    if not match:
        raise ValueError(f"result has no HTML disclosure: {disclosure[:100]}")
    url = urljoin(BASE_URL, match.group(1)).replace("https://www.spec.org/osg/", "https://www.spec.org/")
    if not url.startswith(("https://www.spec.org/", "https://spec.org/")):
        raise ValueError(f"unexpected disclosure URL: {url}")
    return url


def _checked_bulk(path: Path) -> tuple[list[dict[str, str]], str]:
    body = path.read_bytes()
    meta = json.loads(path.with_name(path.name + ".meta.json").read_text())
    digest = hashlib.sha256(body).hexdigest()
    if digest != meta["sha256"] or not str(meta["source_url"]).startswith("https://www.spec.org/cgi-bin/osgresults?"):
        raise ValueError(f"bulk source metadata mismatch: {path}")
    with path.open(encoding="latin1", newline="") as stream:
        rows = [{key.strip(): value for key, value in row.items()} for row in csv.DictReader(stream)]
    return rows, digest


def collect_speed(raw_dir: Path) -> dict[str, list[Result]]:
    old, _ = collect_cpu92(raw_dir)
    results: dict[str, list[Result]] = {
        "cpu92": [
            Result(
                "cpu92",
                item.source_url.rsplit("/", 1)[-1],
                item.system,
                _normalized(item.system),
                item.processor,
                _processor_key(item.processor),
                item.cpu_count,
                None,
                None,
                _frequency({"System": item.system}, item.processor),
                None,
                "",
                "",
                item.score,
                None,
                item.source_url,
                item.source_sha256,
            )
            for item in old
        ]
    }
    for generation in GENERATIONS[1:]:
        rows, digest = _checked_bulk(raw_dir / generation / "bulk.csv")
        selected: list[Result] = []
        seen: set[str] = set()
        for raw in rows:
            if raw["Benchmark"] != "CINT" + generation[3:]:
                continue
            peak = _positive(raw.get("Result") or raw.get("Peak Result"))
            base = _positive(raw.get("Baseline") or raw.get("Base Result"))
            if peak is None and base is None:
                continue
            processor = raw.get("Processor") or raw.get("CPU") or ""
            chips = raw.get("# chips") or raw.get("# Chips") or ""
            if not processor or not chips.isdigit():
                continue
            url = _source_url(raw["Disclosure"])
            result_id = url.split("/results/", 1)[1].removesuffix(".html")
            if result_id in seen:
                raise ValueError(f"duplicate {generation} integer-speed result: {result_id}")
            seen.add(result_id)
            selected.append(
                Result(
                    generation,
                    result_id,
                    raw["System"],
                    _normalized(raw["System"]),
                    processor,
                    _processor_key(processor),
                    int(chips),
                    (
                        int(raw.get("# Cores") or raw.get("# cores"))
                        if (raw.get("# Cores") or raw.get("# cores") or "").isdigit()
                        else None
                    ),
                    (
                        int(raw.get("# Enabled Threads Per Core") or raw.get("# Threads Per Core"))
                        if (raw.get("# Enabled Threads Per Core") or raw.get("# Threads Per Core") or "").isdigit()
                        else None
                    ),
                    _frequency(raw, processor),
                    _memory_mib(raw.get("Memory", "")),
                    raw.get("Operating System") or raw.get("Op. Sys.") or "",
                    raw.get("Compiler", ""),
                    peak,
                    base,
                    url,
                    digest,
                )
            )
        results[generation] = selected
    return results


def _pair(old: Result, new: Result, tier: str, source_check: str = "bulk_hash_checked") -> dict[str, object]:
    return {
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
    }


def _reviewed_pairs(results: dict[str, list[Result]], review: Path) -> list[dict[str, object]]:
    by_url = {item.source_url: item for generation in ("cpu92", "cpu95") for item in results[generation]}
    with review.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    pairs: list[dict[str, object]] = []
    for row in rows:
        old = by_url[row["cpu92_source_url"]]
        new = by_url[row["cpu95_source_url"]]
        if old.peak != float(row["cpu92_score"]) or new.peak != float(row["cpu95_score"]):
            raise ValueError(f"reviewed score differs from bulk source: {old.source_url}")
        paired = _pair(old, new, "reviewed_detail", "reviewed_detail_and_bulk_hash_checked")
        paired["old_base"] = float(row["cpu92_base_score"])
        paired["new_base"] = float(row["cpu95_base_score"])
        paired["base_ratio"] = float(row["cpu92_base_score"]) / float(row["cpu95_base_score"])
        pairs.append(paired)
    return pairs


def _automatic_pairs(results: dict[str, list[Result]], older: str, newer: str) -> list[dict[str, object]]:
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
                tier = (
                    "hardware_near" if clock_agrees and memory_agrees and cores_agree and threads_agree else "name_cpu_chips_only"
                )
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


def _statistics(rows: list[dict[str, object]], mode: str) -> dict[str, object] | None:
    selected = [row for row in rows if row["match_tier"] in {"reviewed_detail", "hardware_near"} and row[f"{mode}_ratio"] != ""]
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
    rng = random.Random(892026)
    bootstrap = sorted(math.exp(statistics.mean(rng.choices(logs, k=len(logs)))) for _ in range(1000))
    x = np.asarray([value[2] for value in config_values.values()])
    y = np.asarray([value[1] for value in config_values.values()])
    slope = float(np.polyfit(x, y, 1)[0]) if float(np.var(x)) > 0 else None
    by_family: dict[str, list[float]] = defaultdict(list)
    for key, value in config_values.items():
        by_family[_processor_family(key[0])].append(value[0])
    heldout = [math.exp(abs(value - (sum(logs) - value) / (len(logs) - 1))) - 1 for value in logs]
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
        "cluster_bootstrap_95_low": bootstrap[24],
        "cluster_bootstrap_95_high": bootstrap[974],
        "heldout_median_absolute_pct_error": statistics.median(heldout),
        "loglog_slope_diagnostic": slope,
        "processor_family_factors": {
            family: {"processor_configs": len(values), "factor_old_per_new": math.exp(statistics.mean(values))}
            for family, values in sorted(by_family.items())
        },
    }


def _graph_fit(edges: list[dict[str, object]], mode: str) -> dict[str, object]:
    accepted = [row for row in edges if row[mode] is not None]
    if not accepted:
        return {}
    matrix = np.zeros((len(accepted), len(GENERATIONS) - 1))
    target = np.zeros(len(accepted))
    weights = np.zeros(len(accepted))
    for index, edge in enumerate(accepted):
        old = GENERATIONS.index(edge["old_generation"])
        new = GENERATIONS.index(edge["new_generation"])
        if old:
            matrix[index, old - 1] = -1
        matrix[index, new - 1] = 1
        target[index] = edge[mode]["log_factor"]
        weights[index] = math.sqrt(edge[mode]["processor_configs"])
    solution, _, rank, _ = np.linalg.lstsq(matrix * weights[:, None], target * weights, rcond=None)
    if rank < len(GENERATIONS) - 1:
        return {"status": "disconnected; no all-generation VAXen path", "rank": int(rank)}
    log_factors = np.r_[0, solution]
    cycle_constraints = len(accepted) - (len(GENERATIONS) - 1)
    return {
        "status": (
            "chain-only exploratory fit; no independent cross-generation cycle check"
            if cycle_constraints == 0
            else "exploratory graph fit with cycle checks; not validated universal conversion"
        ),
        "independent_cycle_constraints": cycle_constraints,
        "vaxen_per_score": {generation: math.exp(float(log_factors[index])) for index, generation in enumerate(GENERATIONS)},
        "edge_log_residuals": (
            {
                f"{edge['old_generation']}-{edge['new_generation']}": float(matrix[index] @ solution - target[index])
                for index, edge in enumerate(accepted)
            }
            if cycle_constraints
            else {}
        ),
    }


def _write_scatter(
    pair_rows: list[dict[str, object]], edges: list[dict[str, object]], output_dir: Path, mode: str
) -> dict[str, str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 3, figsize=(15, 9.5))
    adjacent = [(GENERATIONS[i], GENERATIONS[i + 1]) for i in range(len(GENERATIONS) - 1)]
    for axis, (older, newer) in zip(axes.flat, adjacent):
        cohort = [
            row
            for row in pair_rows
            if row["old_generation"] == older and row["new_generation"] == newer and row[f"{mode}_ratio"] != ""
        ]
        accepted = [row for row in cohort if row["match_tier"] in {"reviewed_detail", "hardware_near"}]
        if cohort:
            axis.scatter(
                [float(row[f"new_{mode}"]) for row in cohort],
                [float(row[f"old_{mode}"]) for row in cohort],
                s=12,
                c="#9da9b2",
                alpha=0.34,
                label="All candidate pairings",
            )
        if accepted:
            axis.scatter(
                [float(row[f"new_{mode}"]) for row in accepted],
                [float(row[f"old_{mode}"]) for row in accepted],
                s=18,
                c="#17628a",
                alpha=0.55,
                label="Fit tier",
            )
            edge = next(item for item in edges if item["old_generation"] == older and item["new_generation"] == newer)
            fit = edge[mode]
            if fit:
                xs = [float(row[f"new_{mode}"]) for row in accepted]
                low, high = min(xs), max(xs)
                axis.plot(
                    [low, high],
                    [low * fit["factor_old_per_new"], high * fit["factor_old_per_new"]],
                    color="#b8472a",
                    linewidth=1.8,
                    label="Clustered factor",
                )
                axis.text(
                    0.04,
                    0.96,
                    f"{fit['processor_configs']} CPU configs; {fit['factor_old_per_new']:.3g} old/new",
                    transform=axis.transAxes,
                    va="top",
                    fontsize=9,
                )
        axis.set_xscale("log")
        axis.set_yscale("log")
        axis.set_title(f"{older.upper()} / {newer.upper()}")
        axis.set_xlabel(f"{newer.upper()} {mode} score")
        axis.set_ylabel(f"{older.upper()} {mode} score")
        axis.grid(which="both", alpha=0.2)
    axes.flat[-1].axis("off")
    axes.flat[-1].text(
        0.05,
        0.85,
        "Same-system submissions remain visible.\nFits weight processor configurations, not pair count.\n"
        "No exact three-generation hardware key was found.\n"
        "These factors are exploratory and not universal VAXen conversions.",
        va="top",
        fontsize=12,
        linespacing=1.5,
    )
    handles, labels = axes.flat[0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 0.995))
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    paths = {}
    for suffix in ("png", "svg"):
        path = output_dir / f"integer-speed-{mode}-overlaps.{suffix}"
        fig.savefig(path, dpi=170 if suffix == "png" else None)
        paths[suffix] = str(path)
    plt.close(fig)
    return paths


def analyze_all_generations(
    raw_dir: Path, review: Path, output_dir: Path, research_summary: Path | None = None
) -> dict[str, object]:
    results = collect_speed(raw_dir)
    pair_rows = _reviewed_pairs(results, review)
    for older_index, older in enumerate(GENERATIONS):
        for newer in GENERATIONS[older_index + 1 :]:
            if older == "cpu92":
                continue
            pair_rows.extend(_automatic_pairs(results, older, newer))
    pair_rows.sort(
        key=lambda row: (
            GENERATIONS.index(str(row["old_generation"])),
            GENERATIONS.index(str(row["new_generation"])),
            str(row["system_key"]),
            str(row["old_result_id"]),
            str(row["new_result_id"]),
        )
    )
    edges: list[dict[str, object]] = []
    for old_index, older in enumerate(GENERATIONS):
        for newer in GENERATIONS[old_index + 1 :]:
            cohort = [row for row in pair_rows if row["old_generation"] == older and row["new_generation"] == newer]
            edges.append(
                {
                    "old_generation": older,
                    "new_generation": newer,
                    "candidate_pairings": len(cohort),
                    "hardware_near_or_reviewed": sum(row["match_tier"] in {"reviewed_detail", "hardware_near"} for row in cohort),
                    "peak": _statistics(cohort, "peak"),
                    "base": _statistics(cohort, "base"),
                }
            )
    by_result_key: dict[tuple[str, str, int], set[str]] = defaultdict(set)
    for generation, records in results.items():
        for record in records:
            if record.system_key and record.processor_key:
                by_result_key[record.system_key, record.processor_key, record.chips].add(generation)
    triple_keys = {key: sorted(suites) for key, suites in by_result_key.items() if len(suites) >= 3}
    output_dir.mkdir(parents=True, exist_ok=True)
    records_path = output_dir / "integer-speed-source-records.csv"
    with records_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(Result.__dataclass_fields__))
        writer.writeheader()
        writer.writerows(asdict(item) for suite in GENERATIONS for item in results[suite])
    pairs_path = output_dir / "integer-speed-generation-pairs.csv"
    with pairs_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PAIR_FIELDS)
        writer.writeheader()
        writer.writerows(pair_rows)
    input_hashes = {
        "cpu92": hashlib.sha256(
            "\n".join(sorted(f"{item.source_url} {item.source_container_sha256}" for item in results["cpu92"])).encode()
        ).hexdigest(),
        **{generation: results[generation][0].source_container_sha256 for generation in GENERATIONS[1:]},
        "cpu92_cpu95_review": hashlib.sha256(review.read_bytes()).hexdigest(),
    }
    summary = {
        "method_version": METHOD_VERSION,
        "source_input_hashes": input_hashes,
        "scope": "integer speed; source submissions retained; system ratios aggregated then processor configurations weighted equally",
        "limitations": [
            "bulk CSV hashes checked, but detailed disclosures verified only for reviewed CPU92/95 pairs and selected spot checks",
            "requested benchmark thread counts are not present in bulk exports and are not pairwise validated",
            "compiler and tuning differences remain; fitted factors are exploratory, not official or universal conversions",
        ],
        "source_records": {generation: len(results[generation]) for generation in GENERATIONS},
        "pair_records": str(pairs_path),
        "source_record_export": str(records_path),
        "edges": edges,
        "three_generation_keys": len(triple_keys),
        "three_generation_examples": [
            {"system_key": key[0], "processor_key": key[1], "chips": key[2], "generations": suites}
            for key, suites in list(sorted(triple_keys.items()))[:20]
        ],
        "peak_graph": _graph_fit(edges, "peak"),
        "base_graph": _graph_fit(edges, "base"),
        "scatter_figures": {mode: _write_scatter(pair_rows, edges, output_dir, mode) for mode in ("peak", "base")},
    }
    if research_summary is not None:
        research_summary.parent.mkdir(parents=True, exist_ok=True)
        columns = [
            "method_version",
            "old_generation",
            "new_generation",
            "mode",
            "candidate_pairings",
            "hardware_near_or_reviewed",
            "fit_pairings",
            "system_groups",
            "processor_configs",
            "factor_old_per_new",
            "cluster_bootstrap_95_low",
            "cluster_bootstrap_95_high",
            "config_ratio_min",
            "config_ratio_max",
            "heldout_median_absolute_pct_error",
            "loglog_slope_diagnostic",
            "old_input_sha256",
            "new_input_sha256",
            "review_sha256",
            "pair_export_sha256",
        ]
        pair_hash = hashlib.sha256(pairs_path.read_bytes()).hexdigest()
        with research_summary.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            for edge in edges:
                for mode in ("peak", "base"):
                    fit = edge[mode] or {}
                    writer.writerow(
                        {
                            "method_version": METHOD_VERSION,
                            "old_generation": edge["old_generation"],
                            "new_generation": edge["new_generation"],
                            "mode": mode,
                            "candidate_pairings": edge["candidate_pairings"],
                            "hardware_near_or_reviewed": edge["hardware_near_or_reviewed"],
                            "fit_pairings": fit.get("candidate_pairings_used", ""),
                            "system_groups": fit.get("system_groups", ""),
                            "processor_configs": fit.get("processor_configs", ""),
                            **{
                                field: fit.get(field, "")
                                for field in (
                                    "factor_old_per_new",
                                    "cluster_bootstrap_95_low",
                                    "cluster_bootstrap_95_high",
                                    "config_ratio_min",
                                    "config_ratio_max",
                                    "heldout_median_absolute_pct_error",
                                    "loglog_slope_diagnostic",
                                )
                            },
                            "old_input_sha256": input_hashes[edge["old_generation"]],
                            "new_input_sha256": input_hashes[edge["new_generation"]],
                            "review_sha256": input_hashes["cpu92_cpu95_review"],
                            "pair_export_sha256": pair_hash,
                        }
                    )
        summary["research_summary_csv"] = str(research_summary)
        chain_path = research_summary.with_name("integer-speed-vaxen-chain.csv")
        with chain_path.open("w", newline="") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=[
                    "method_version",
                    "mode",
                    "generation",
                    "vaxen_per_score",
                    "status",
                    "source_input_sha256",
                    "pair_export_sha256",
                ],
            )
            writer.writeheader()
            for mode in ("peak", "base"):
                graph = summary[f"{mode}_graph"]
                for generation in GENERATIONS:
                    writer.writerow(
                        {
                            "method_version": METHOD_VERSION,
                            "mode": mode,
                            "generation": generation,
                            "vaxen_per_score": graph.get("vaxen_per_score", {}).get(generation, ""),
                            "status": "exploratory_chain_only_not_adopted",
                            "source_input_sha256": input_hashes[generation],
                            "pair_export_sha256": pair_hash,
                        }
                    )
        summary["research_chain_csv"] = str(chain_path)
    summary_path = output_dir / "integer-speed-generation-fit.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    summary["summary_file"] = str(summary_path)
    return summary


@click.command("fit-generations")
@click.option("--raw-dir", type=click.Path(path_type=Path), default=Path("data/raw/spec"), show_default=True)
@click.option("--review", type=click.Path(path_type=Path), default=Path("research/cpu92-cpu95-reviewed.csv"), show_default=True)
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("data/derived/spec/fitting"), show_default=True)
@click.option(
    "--research-summary",
    type=click.Path(path_type=Path),
    default=Path("research/data/spec/fitting/integer-speed-factors.csv"),
    show_default=True,
)
def fit_generations_command(raw_dir: Path, review: Path, output_dir: Path, research_summary: Path) -> None:
    """Test paired scaling from CPU92 through CPU2026 and audit three-suite overlaps."""
    try:
        summary = analyze_all_generations(raw_dir, review, output_dir, research_summary)
    except (OSError, ValueError, KeyError, IndexError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(
        json.dumps(
            {
                "summary_file": summary["summary_file"],
                "source_records": summary["source_records"],
                "three_generation_keys": summary["three_generation_keys"],
            },
            sort_keys=True,
        )
    )
