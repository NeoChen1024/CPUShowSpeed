"""Saved joint-model estimates and full-rate scenario variants for the timeline."""

import hashlib
import json
import math
from pathlib import Path

from cpushowspeed.annual_rate import _month
from cpushowspeed.research_io import read_csv
from cpushowspeed.spec_inputs import collect_integer, runtime_fingerprint
from cpushowspeed.spec_overlap import _checked_bulk, _source_url
from cpushowspeed.timeline_dates import candidate, select_date
from cpushowspeed.timeline_resources import resource_fields

POLICIES = ("strict", "ram-aliases", "cpu-clock")
ROOT = Path("research/data/spec/joint-tracks")
DERIVED = Path("data/derived/spec/joint-tracks")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bundle(policy):
    root = ROOT / (policy if policy != "strict" else "")
    derived = DERIVED / (policy if policy != "strict" else "")
    audit = json.loads((root / "audit.json").read_text())
    if audit.get("runtime_fingerprint") != runtime_fingerprint(Path("data/raw/spec")):
        raise ValueError("stale runtime evidence; rerun fit-joint-tracks: " + policy)
    for path, sha in audit["code_hashes"].items():
        if digest(Path(path)) != sha:
            raise ValueError("stale joint model code; rerun fit-joint-tracks: " + policy)
    for gen, sha in audit["raw_bulk_sha256"].items():
        if digest(Path("data/raw/spec") / gen / "bulk.csv") != sha:
            raise ValueError("stale joint inputs: " + gen)
    if digest(Path("data/derived/spec/cpu92-rate/cpu92-rate-records.csv")) != audit["cpu92_records_sha256"]:
        raise ValueError("stale CPU92 anchor")
    for name, sha in audit["research_csv_sha256"].items():
        if digest(root / name) != sha:
            raise ValueError("joint factor export mismatch: " + name)
    for name in ("triples.csv", "configuration-centers.csv"):
        if digest(derived / name) != audit["output_csv_sha256"][name]:
            raise ValueError("joint evidence export mismatch: " + name)
    factors = {
        (r["new_generation"], r["mode"], r["method"]): r for r in read_csv(root / "summary.csv") if r["status"] == "conditional_fit"
    }
    backbone = {(r["generation"], r["mode"]): r for r in read_csv(root / "backbone-summary.csv")}
    return factors, backbone, read_csv(derived / "triples.csv"), {str(root / "audit.json"): digest(root / "audit.json")}


def value(score, factor, backbone=False):
    k, lo, hi = ("coefficient", "ci95_low", "ci95_high") if backbone else ("coefficient_vaxen", "vaxen_ci95_low", "vaxen_ci95_high")
    values = [score * float(factor[x]) for x in (k, lo, hi)]
    if not all(math.isfinite(x) and x > 0 for x in values) or values[1] > values[2]:
        raise ValueError("invalid timeline calibration interval")
    return values


def extend_estimates(modern, chronology, schema):
    bundles = {p: bundle(p) for p in POLICIES}
    provenance = {k: v for b in bundles.values() for k, v in b[3].items()}
    by_rate = {(r["source_url"], r["mode"]): r for r in modern}
    for row in modern:
        row["estimate_kind"] = "baseline"
        row["variants"] = {}
        row["comparison_keys"] = [row["source_url"] + "|" + row["mode"]]
        for p, (_, backbone, _, _) in bundles.items():
            if row["generation"] == "cpu92":
                v = [row[k] for k in ("vaxen", "ci95_low", "ci95_high")]
            else:
                v = value(float(row["reported_score"]), backbone[row["generation"], row["mode"]], True)
            row["variants"][p] = v
        row["value_scenario"] = "ram-aliases"
        row.update(zip(("vaxen", "ci95_low", "ci95_high"), row["variants"]["ram-aliases"]))
        if row["generation"] != "cpu92":
            row["uncertainty_scope"] = "conditional shared-model rate-chain coefficient CI95"
            row["calibration_scenario"] = "ram-aliases"
    speed = collect_integer(Path("data/raw/spec"), "speed")
    raw = {r.source_url: r.raw_fields for records in speed.values() for r in records}
    additional = []
    by_speed = {}
    for generation, records in speed.items():
        for src in records:
            for mode in ("base", "peak"):
                score = getattr(src, mode)
                if score is None:
                    continue
                variants = {
                    p: value(score, b[0][generation, mode, "speed_only"])
                    for p, b in bundles.items()
                    if (generation, mode, "speed_only") in b[0]
                }
                if not variants:
                    continue
                fields = raw[src.source_url]
                cid = "speed:" + generation + ":" + src.result_id + ":" + mode
                row = dict(
                    schema_version=schema,
                    record_id=cid,
                    configuration_id=cid,
                    estimate_kind="speed",
                    variants=variants,
                    comparison_keys=[src.source_url + "|" + mode],
                    route=generation.upper(),
                    generation=generation,
                    mode=mode,
                    system=src.system,
                    cpu=src.processor,
                    clock_mhz=src.clock_mhz or "",
                    os=src.os,
                    configuration="",
                    scores={generation.upper() + " integer speed " + mode: score},
                    reported_score=score,
                    benchmark_id=generation.upper() + " integer speed " + mode,
                    reported_unit=generation.upper() + " native integer speed points",
                    source_container_sha256=src.source_container_sha256,
                    value_scenario="ram-aliases" if "ram-aliases" in variants else next(iter(variants)),
                    source_record_ids=[src.result_id],
                    benchmark_sources=[src.source_url],
                    source_url=src.source_url,
                    observation_count=1,
                    chips=src.chips,
                    cores=src.cores or "",
                    threads_per_core=src.enabled_threads_per_core or "",
                    copies_min="",
                    copies_max="",
                    evidence_class="speed_inferred_rate_estimate",
                    measurement_scope="predicted_reported_system_rate",
                    calibration_route=generation.upper() + " speed → older rate → CPU92 rate",
                    calibration_scenario="selectable_joint_model",
                    uncertainty_scope="conditional full-route coefficient CI95; not a prediction interval",
                    limitation="Speed predicts throughput here; it is not speed-VAXen. Transfer beyond overlap hardware is unvalidated.",
                )
                row.update(resource_fields(row, fields, "speed"))
                row.update(zip(("vaxen", "ci95_low", "ci95_high"), variants.get("ram-aliases", next(iter(variants.values())))))
                row.update(
                    select_date(
                        chronology.lookup(row)
                        + [
                            candidate(
                                "hardware", _month(fields.get("HW Avail", "")), src.source_url, "reported_hardware_availability"
                            ),
                            candidate(
                                "submission", _month(fields.get("Published", "")), src.source_url, "reported_result_publication"
                            ),
                        ]
                    )
                )
                additional.append(row)
                by_speed[src.source_url, mode] = row
    paired = {}
    for policy, (factors, _, triples, _) in bundles.items():
        for t in triples:
            g, m = t["new_generation"], t["mode"]
            factor = factors.get((g, m, "equal_geometric"))
            if not factor:
                continue
            key = (t["speed_url"], t["rate_url"], m)
            if key not in paired:
                s, r = by_speed[t["speed_url"], m], by_rate[t["rate_url"], m]
                cid = "joint:" + hashlib.sha256(json.dumps(key).encode()).hexdigest()[:24]
                row = dict(
                    r,
                    record_id=cid,
                    configuration_id=cid,
                    estimate_kind="joint",
                    variants={},
                    matched_rate_variants={},
                    source_record_ids=[s["source_record_ids"][0], r["source_record_ids"][0]],
                    benchmark_sources=[t["speed_url"], t["rate_url"]],
                    observation_count=2,
                    comparison_keys=[t["speed_url"] + "|" + m, t["rate_url"] + "|" + m],
                    system=s["system"] if s["system"] == r["system"] else s["system"] + " / " + r["system"],
                    scores={"speed": float(t["speed_score"]), "rate": float(t["rate_score"])},
                    reported_score=None,
                    benchmark_id=g.upper() + " paired integer speed/rate " + m,
                    reported_unit=g.upper() + " native speed and rate points",
                    calibration_scenario="selectable_joint_model",
                    configuration="Speed: " + s["system"] + "; rate: " + r["system"],
                    evidence_class="paired_speed_rate_estimate",
                    calibration_route=g.upper() + " speed + rate → older rate → CPU92 rate",
                    uncertainty_scope="conditional joint full-route coefficient CI95; not a prediction interval",
                    limitation="Matched input pair; calibration targets are not extra observations. Pair date follows the rate input.",
                    input_source_sha256={
                        s["source_url"]: s["source_container_sha256"],
                        r["source_url"]: r["source_container_sha256"],
                    },
                    input_configurations={
                        "speed": {
                            k: s.get(k)
                            for k in (
                                "system",
                                "clock_mhz",
                                "chips",
                                "cores",
                                "threads_per_core",
                                "cores_per_chip",
                                "runtime_resources",
                                "resource_basis",
                                "resource_warning",
                                "year",
                                "date_candidates",
                            )
                        },
                        "rate": {
                            k: r.get(k)
                            for k in (
                                "system",
                                "clock_mhz",
                                "chips",
                                "cores",
                                "threads_per_core",
                                "cores_per_chip",
                                "runtime_resources",
                                "resource_basis",
                                "resource_warning",
                                "year",
                                "date_candidates",
                            )
                        },
                    },
                )
                paired[key] = row
            row = paired[key]
            v = value(math.sqrt(float(t["speed_score"]) * float(t["rate_score"])), factor)
            if policy in row["variants"] and row["variants"][policy] != v:
                raise ValueError("conflicting duplicate predictor pair")
            row["variants"][policy] = v
            row["matched_rate_variants"][policy] = value(float(t["rate_score"]), factors[g, m, "rate_only"])
    for row in paired.values():
        row["value_scenario"] = "ram-aliases" if "ram-aliases" in row["variants"] else next(iter(row["variants"]))
        row.update(
            zip(("vaxen", "ci95_low", "ci95_high"), row["variants"].get("ram-aliases", next(iter(row["variants"].values()))))
        )
    return additional + list(paired.values()), provenance, bundles
