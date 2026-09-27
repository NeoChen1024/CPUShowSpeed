"""Classical pair eligibility and values, without regression or plotting."""

import itertools
import json
from collections import defaultdict

from cpushowspeed.calibration import ANCHOR
from cpushowspeed.classic_values import TARGETS, clock_status, linpack_n100, numeric

PATTERNS = [(("Dhrystone", d), ("Whetstone", w)) for d in ("v1.1_DMIPS", "v2.1_DMIPS") for w in ("MWIPS", "MWIPS_DP")]
PATTERNS += [(("Dhrystone", d), ("LINPACK", "n100_MFLOPS")) for d in ("v1.1_DMIPS", "v2.1_DMIPS")]
PATTERNS += [(("Whetstone", w), ("LINPACK", "n100_MFLOPS")) for w in ("MWIPS", "MWIPS_DP")]
SCENARIOS = ("known_clocks", "unknown_allowed", "linear_clock_scaling")


def values(records, scores, spec, scenario):
    reasons = []
    clocks = clock_status(records + [spec])
    multipliers = [1.0, 1.0]
    destination = None
    if scenario != "linear_clock_scaling":
        if clocks == "conflict":
            reasons.append("clock_conflict")
        elif clocks == "unknown" and scenario == "known_clocks":
            reasons.append("unknown_clock")
    else:
        # Prefer SPEC, then LINPACK (never scaled), then Whetstone, Dhrystone.
        ordered = [spec] + sorted(records, key=lambda r: {"LINPACK": 0, "Whetstone": 1, "Dhrystone": 2}[r["benchmark"]])
        destination = next((r for r in ordered if numeric(r.get("clock_mhz"))), None)
        for i, record in enumerate(records):
            if record["benchmark"] == "LINPACK":
                if clock_status([record, spec]) == "conflict":
                    reasons.append("unscaled_linpack_spec_clock_conflict")
                continue
            frequency = numeric(record.get("clock_mhz"))
            if not destination or not frequency:
                reasons.append("missing_clock_for_scaling")
            else:
                multipliers[i] = numeric(destination["clock_mhz"]) / frequency
    return [x * m for x, m in zip(scores, multipliers)], multipliers, destination, reasons


def build(classical, specs, pairs, pages):
    groups = defaultdict(lambda: defaultdict(set))
    keys = {}
    for p in pairs:
        groups[p["spec_id"]][classical[p["classic_id"]]["benchmark"]].add(p["classic_id"])
        keys[p["spec_id"]] = p["model_key"]
    rows = []
    cache = {}
    for sid, families in sorted(groups.items()):
        spec = specs[sid]
        for pattern in PATTERNS:
            label = "+".join(f"{family}:{metric}" for family, metric in pattern)
            options = []
            for family, metric in pattern:
                members = []
                for cid in sorted(families[family]):
                    r = classical[cid]
                    if (cid, metric) not in cache:
                        cache[cid, metric] = (
                            linpack_n100(r, pages) if family == "LINPACK" else numeric(r["metrics_raw"].get(metric))
                        )
                    if cache[cid, metric]:
                        members.append((r, cache[cid, metric]))
                options.append(members)
            for target in TARGETS:
                score = numeric(spec["metrics_raw"].get(target))
                if score is None:
                    continue
                for combination in itertools.product(*options):
                    records = [x[0] for x in combination]
                    scores = [x[1] for x in combination]
                    exclusions = []
                    if target.startswith("SPECrate") and numeric(spec.get("cpu_count")) != 1:
                        exclusions.append("spec_cpu_count_not_one")
                    if any(r.get("reported_processor_count") is not None and r["reported_processor_count"] != 1 for r in records):
                        exclusions.append("classic_cpu_count_not_one")
                    raw = spec["raw_record"]
                    if isinstance(raw, dict) and (
                        raw.get("measurement_type") == "reference_definition"
                        or "reference_definition" in raw.get("review_flags", "")
                    ):
                        exclusions.append("reference_definition")
                    for scenario in SCENARIOS:
                        adjusted, multipliers, destination, reasons = values(records, scores, spec, scenario)
                        rows.append(
                            dict(
                                pattern=label,
                                target=target,
                                scenario=scenario,
                                model_key=keys[sid],
                                spec_id=sid,
                                first_id=records[0]["id"],
                                second_id=records[1]["id"],
                                system=spec["system"],
                                first_original=scores[0],
                                second_original=scores[1],
                                first=adjusted[0],
                                second=adjusted[1],
                                first_multiplier=multipliers[0],
                                second_multiplier=multipliers[1],
                                normalization_clock_source=destination["id"] if destination else "",
                                y=score * (ANCHOR if target.startswith("SPECrate") else 1),
                                included=not (exclusions + reasons),
                                exclusion_reasons=";".join(exclusions + reasons),
                                provenance=json.dumps(
                                    [
                                        dict(id=r["id"], url=r["source_url"], locator=r.get("locator"), raw=r["raw_record"])
                                        for r in records + [spec]
                                    ],
                                    sort_keys=True,
                                ),
                            )
                        )
    return rows
