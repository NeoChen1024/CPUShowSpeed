"""Audit complete classical-score vectors before attempting weight estimation."""

import csv
import hashlib
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path

import click
from cpushowspeed.classic_fit import linpack_n100, numeric, write_csv

TARGETS = ("SPECmark89", "SPECint89", "SPECfp89", "SPECrate_base_int92", "SPECrate_int92")


def clock_status(records):
    clocks = [numeric(r.get("clock_mhz")) for r in records]
    known = [x for x in clocks if x is not None]
    if known and max(known) - min(known) > 0.01 * max(known):
        return "conflict"
    return "known" if len(known) == len(clocks) else "unknown"


def audit(classical, specs, pairs, pages):
    candidates = defaultdict(lambda: defaultdict(set))
    keys = {}
    for pair in pairs:
        sid, cid = pair["spec_id"], pair["classic_id"]
        candidates[sid][classical[cid]["benchmark"]].add(cid)
        keys[sid] = pair["model_key"]
    coverage, vectors = [], []
    for sid, families in sorted(candidates.items()):
        spec = specs[sid]
        for target in TARGETS:
            if numeric(spec["metrics_raw"].get(target)) is None:
                continue
            for whet in ("MWIPS", "MWIPS_DP"):
                options = []
                for family, metric in [("Dhrystone", "v1.1_DMIPS"), ("Whetstone", whet), ("LINPACK", "n100_MFLOPS")]:
                    selected = []
                    for cid in sorted(families[family]):
                        record = classical[cid]
                        score = linpack_n100(record, pages) if family == "LINPACK" else numeric(record["metrics_raw"].get(metric))
                        if score is not None:
                            selected.append((cid, score))
                    options.append(selected)
                coverage.append(
                    dict(
                        spec_id=sid,
                        model_key=keys[sid],
                        system=spec["system"],
                        target=target,
                        whetstone=whet,
                        dhrystone_rows=len(options[0]),
                        whetstone_rows=len(options[1]),
                        linpack_rows=len(options[2]),
                        complete_score_vector=all(options),
                        source_url=spec["source_url"],
                    )
                )
                for combination in itertools.product(*options):
                    records = [classical[cid] for cid, _ in combination]
                    reasons = []
                    clocks = clock_status(records + [spec])
                    if clocks == "conflict":
                        reasons.append("cross_source_clock_conflict")
                    if target.startswith("SPECrate") and numeric(spec.get("cpu_count")) != 1:
                        reasons.append("spec_cpu_count_not_one")
                    if any(r.get("reported_processor_count") is not None and r["reported_processor_count"] != 1 for r in records):
                        reasons.append("classical_processor_count_not_one")
                    raw = spec["raw_record"]
                    if isinstance(raw, dict) and (
                        raw.get("measurement_type") == "reference_definition"
                        or "reference_definition" in raw.get("review_flags", "")
                    ):
                        reasons.append("reference_definition_not_independent_measurement")
                    # Sensitivity scenario only: normalize Dhrystone/Whetstone;
                    # retain original LINPACK and SPEC scores and unknown clocks.
                    destination = next((r for r in [spec, records[2], records[1], records[0]] if numeric(r.get("clock_mhz"))), None)
                    frequency = numeric(destination.get("clock_mhz")) if destination else None
                    multipliers = [
                        frequency / numeric(r.get("clock_mhz")) if frequency and numeric(r.get("clock_mhz")) else None
                        for r in records[:2]
                    ]
                    scaled_reasons = [r for r in reasons if r != "cross_source_clock_conflict"]
                    if frequency is None:
                        scaled_reasons.append("no_target_clock")
                    if any(m is None for m in multipliers):
                        scaled_reasons.append("missing_classical_clock_for_scaling")
                    if clock_status([records[2], spec]) == "conflict":
                        scaled_reasons.append("linpack_spec_clock_conflict_unscaled")
                    vectors.append(
                        dict(
                            spec_id=sid,
                            model_key=keys[sid],
                            system=spec["system"],
                            target=target,
                            whetstone=whet,
                            spec_score=numeric(spec["metrics_raw"][target]),
                            dhrystone=combination[0][1],
                            whetstone_score=combination[1][1],
                            linpack=combination[2][1],
                            dhrystone_id=combination[0][0],
                            whetstone_id=combination[1][0],
                            linpack_id=combination[2][0],
                            clock_status=clocks,
                            exclusion_reasons=";".join(reasons),
                            candidate_unknown_clock_allowed=not reasons,
                            candidate_known_clocks=not reasons and clocks == "known",
                            whetstone_language=records[1].get("language_raw", ""),
                            provenance=json.dumps(
                                [
                                    dict(
                                        id=r["id"],
                                        url=r["source_url"],
                                        locator=r.get("locator"),
                                        clock_mhz=r.get("clock_mhz"),
                                        raw=r["raw_record"],
                                    )
                                    for r in records + [spec]
                                ],
                                sort_keys=True,
                            ),
                            candidate_linear_clock_scaling=not scaled_reasons,
                            scaling_exclusion_reasons=";".join(scaled_reasons),
                            normalization_clock_mhz=frequency,
                            normalization_clock_source=destination["id"] if destination else "",
                            dhrystone_multiplier=multipliers[0],
                            whetstone_multiplier=multipliers[1],
                            dhrystone_adjusted=combination[0][1] * multipliers[0] if multipliers[0] else None,
                            whetstone_adjusted=combination[1][1] * multipliers[1] if multipliers[1] else None,
                            normalization_status="assumed_linear_not_measured;unknown_linpack_or_spec_clock_not_resolved",
                            configuration_verified=False,
                        )
                    )
    summary = []
    for target, whet in itertools.product(TARGETS, ("MWIPS", "MWIPS_DP")):
        subset = [r for r in vectors if r["target"] == target and r["whetstone"] == whet]
        for mode in ("candidate_known_clocks", "candidate_unknown_clock_allowed", "candidate_linear_clock_scaling"):
            selected = [r for r in subset if r[mode]]
            summary.append(
                dict(
                    target=target,
                    whetstone=whet,
                    scenario=mode,
                    complete_tuples=len(subset),
                    candidate_tuples=len(selected),
                    spec_records=len({r["spec_id"] for r in selected}),
                    models=len({r["model_key"] for r in selected}),
                    model_keys=";".join(sorted({r["model_key"] for r in selected})),
                    status="intersection_audit_only_no_weight_fit",
                )
            )
    return coverage, vectors, summary


@click.command("composite-overlap")
@click.option(
    "--input-root",
    type=click.Path(path_type=Path, exists=True),
    default=Path("data/derived/classic/overlap-spec"),
    show_default=True,
)
@click.option(
    "--linpack-text",
    type=click.Path(path_type=Path, exists=True),
    default=Path("data/derived/classic/netlib-linpack-report.txt"),
    show_default=True,
)
@click.option(
    "--output", type=click.Path(path_type=Path), default=Path("data/derived/classic/composite-overlap"), show_default=True
)
def composite_overlap(input_root, linpack_text, output):
    """Audit Dhrystone 1.1 + Whetstone + LINPACK intersections for separate SPEC targets."""
    paths = [input_root / name for name in ("classical-records.jsonl", "spec-records.jsonl", "candidate-pairs.csv")]
    classical, specs = [{r["id"]: r for r in map(json.loads, p.read_text().splitlines())} for p in paths[:2]]
    with paths[2].open(newline="") as f:
        pairs = list(csv.DictReader(f))
    coverage, vectors, summary = audit(classical, specs, pairs, linpack_text.read_text().split("\f"))
    output.mkdir(parents=True, exist_ok=True)
    for name, rows in [("coverage", coverage), ("vectors", vectors), ("summary", summary)]:
        write_csv(output / f"{name}.csv", rows)
    metadata = dict(
        method="classic-three-benchmark-intersection-v1",
        inputs_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths + [linpack_text]},
        code_sha256={
            str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__), Path(__file__).with_name("classic_fit.py"))
        },
        exclusions=dict(Counter(reason for r in vectors for reason in r["exclusion_reasons"].split(";") if reason)),
        output_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.glob("*.csv"))},
    )
    (output / "audit.json").write_text(json.dumps(metadata, indent=2) + "\n")
    click.echo(json.dumps(dict(output=str(output), vector_tuples=len(vectors), summaries=len(summary))))
