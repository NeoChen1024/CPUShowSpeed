"""Adapt conditional CCTA mix predictions to the shared timeline contract."""

import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
from cpushowspeed.calibration import ANCHOR
from cpushowspeed.research_io import read_csv
from cpushowspeed.timeline_dates import candidate, select_date

ROOT = Path("data/derived/classic/mix-network-fit")
SCORES = Path("data/derived/classic/mix-study/mix-records.csv")
OVERRIDES = Path("research/data/historical/timeline-year-overrides.csv")
DATES = Path("research/data/historical/hardware-date-evidence.csv")


def combined_mixes(rows, draws, metrics):
    """Group exact source table rows; combine aligned log draws, never CI endpoints."""
    groups = defaultdict(list)
    for row in rows:
        oid = row["source_record_ids"][0]
        stem, suffix = oid.rsplit(":", 1)
        if suffix not in ("Gibson Mix", "ADP Mix"):
            raise ValueError("Unknown mix source identity")
        groups[row["source_snapshot_sha256"], row["source_url"], stem].append(row)
    combined = []
    for (_, _, stem), members in groups.items():
        if len(members) > 2 or len({r["benchmark_id"] for r in members}) != len(members):
            raise ValueError("Duplicate mix within source row")
        for field in ["system", "configuration", "year", "year_low", "year_high"]:
            if len({r[field] for r in members}) != 1:
                raise ValueError("Conflicting mix row configuration: " + stem)
        scores = {k: v for r in members for k, v in r["scores"].items()}
        logs = sum((draws[:, metrics.index(m)] + math.log(v)) / len(scores) for m, v in scores.items())
        interval = np.quantile(np.exp(logs), [0.025, 0.975])
        value = math.exp(sum(math.log(r["vaxen"]) for r in members) / len(members))
        row = dict(members[0])
        row.update(
            record_id="instruction-mix-combined:" + stem,
            configuration_id="instruction-mix-combined:" + stem,
            route="Combined mixes",
            scores=scores,
            reported_score=None,
            benchmark_id="Gibson + ADP" if len(members) == 2 else members[0]["benchmark_id"],
            source_record_ids=[r["source_record_ids"][0] for r in members],
            source_locator=stem,
            observation_count=len(members),
            vaxen=value,
            ci95_low=float(interval[0]),
            ci95_high=float(interval[1]),
            estimated_specint92_rate=value / ANCHOR,
            mix_combination="equal log weights; aligned joint draws" if len(members) == 2 else "single available mix fallback",
            calibration_route="Available CCTA mixes → geometric combination → SPEC92 integer rate",
        )
        row[
            "limitation"
        ] += " Correlated mix components; combined and individual views are alternatives, not additional measurements."
        combined.append(row)
    return combined


def mix_dates(source, row, chronology, overrides, evidence):
    dates = chronology.lookup(row)
    reported = candidate(
        "hardware",
        source["introduction_year_raw"],
        source["source_url"],
        "source_approximate_introduction_year",
        "CCTA/Longbottom approximate model introduction; configuration date unverified.",
    )
    reviewed = []
    for e in evidence:
        if e["use_for_timeline"] == "true" and re.search(e["system_regex"], row["system"], re.I):
            c = candidate("hardware", e["date"], e["source_url"], "reviewed_" + e["event_type"], e["notes"])
            if c:
                reviewed.append(c)
    rules = [
        r
        for r in overrides
        if re.search(r["system_regex"], row["system"], re.I) and not (r.get("fallback") == "true" and (reported or reviewed))
    ]
    if rules:
        r = rules[0]
        if reported:
            reported.update(eligible=False, notes=reported["notes"] + " Superseded by reviewed year rule: " + r["notes"])
        reviewed = [candidate("hardware", r["year"], r["source_url"], r["method"], r["notes"])]
    elif reviewed and reported:
        reported.update(eligible=False, notes=reported["notes"] + " Reviewed model evidence takes precedence.")
    return select_date(dates + [reported] + reviewed)


def mix_records(chronology, schema):
    paths = [ROOT / n for n in ["audit.json", "mix-estimates.csv", "coefficients.csv", "coefficient-log-draws.npz"]] + [
        SCORES,
        OVERRIDES,
        DATES,
    ]
    audit = json.loads(paths[0].read_text())
    if audit["method"] != "instruction-mix-joint-network-v1":
        raise ValueError("Unsupported mix calibration")
    for path, digest in audit["input_sha256"].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
            raise ValueError("Stale mix calibration input: " + path)
    scenario, cohort = "linear_clock", "with_spec89"
    run = next(r for r in audit["runs"] if r["scenario"] == scenario and r["cohort"] == cohort)
    coeff = {r["metric"]: r for r in read_csv(paths[2]) if r["scenario"] == scenario and r["cohort"] == cohort}
    with np.load(paths[3]) as f:
        draws = f[scenario + "__" + cohort]
    source = {r["mix_id"]: r for r in read_csv(SCORES)}
    estimates = [r for r in read_csv(paths[1]) if r["scenario"] == scenario and r["cohort"] == cohort]
    if len({r["mix_id"] for r in estimates}) != len(estimates):
        raise ValueError("Duplicate mix estimate")
    if {r["mix_id"] for r in estimates} != {k for k, v in source.items() if v["kips"] and float(v["kips"]) > 0}:
        raise ValueError("Incomplete mix prediction population")
    overrides, evidence = read_csv(OVERRIDES), read_csv(DATES)
    rows = []
    for r in estimates:
        s = source[r["mix_id"]]
        score = float(r["kips"])
        metric = r["metric"]
        c = coeff[metric]
        expected_metric = "InstructionMix:Gibson_KIPS" if s["mix"] == "Gibson Mix" else "InstructionMix:ADP_KIPS"
        if metric != expected_metric:
            raise ValueError("Mix metric identity changed")
        if not math.isclose(score, float(s["kips"]), rel_tol=1e-12):
            raise ValueError("Mix source score changed")
        expected = score * float(c["coefficient_vaxen_per_score"])
        interval = np.quantile(np.exp(draws[:, run["metrics"].index(metric)]) * score, [0.025, 0.975])
        for value, want in [
            (r["estimated_vaxen"], expected),
            (r["ci95_low"], interval[0]),
            (r["ci95_high"], interval[1]),
            (r["estimated_rate"], expected / ANCHOR),
        ]:
            if not math.isclose(float(value), float(want), rel_tol=1e-10):
                raise ValueError("Mix prediction disagrees with coefficient/draws")
        config = "; ".join(
            f"{label}: {s[key]}"
            for label, key in [
                ("word bits", "word_bits"),
                ("memory", "memory_capacity_raw"),
                ("memory cycle µs", "memory_cycle_us_raw"),
            ]
            if s[key]
        )
        row = dict(
            schema_version=schema,
            record_id="instruction-mix:" + r["mix_id"],
            configuration_id="instruction-mix:" + r["mix_id"],
            route="Gibson mix" if s["mix"] == "Gibson Mix" else "ADP mix",
            generation="instruction_mix",
            mode="peak_proxy",
            system=s["system"],
            cpu="",
            clock_mhz="",
            os="",
            configuration=config,
            scores={metric: score},
            reported_score=score,
            reported_unit="KIPS",
            benchmark_id=s["mix"],
            mix_variant=s["mix_variant"],
            vaxen=expected,
            ci95_low=float(interval[0]),
            ci95_high=float(interval[1]),
            estimated_specint92_rate=float(r["estimated_rate"]),
            calibration_route="CCTA mix → joint classical network → SPEC92 integer rate",
            calibration_scenario=scenario + "/" + cohort,
            uncertainty_scope="conditional joint calibration CI95; not individual prediction interval",
            source_record_ids=[r["mix_id"]],
            benchmark_sources=[s["source_url"]],
            source_url=s["source_url"],
            source_locator=s["source_locator"],
            source_snapshot_sha256=s["source_snapshot_sha256"],
            observation_count=1,
            evidence_class="instruction_mix_estimate_calibrated_to_rate",
            measurement_scope="historical_system_mix_estimate; processor count unspecified",
            chips="",
            cores="",
            threads_per_core="",
            copies_min="",
            copies_max="",
            nodes="",
            limitation="CCTA/TSU mix variant only. Candidate configuration matches; no direct SPEC observations for mix-bearing nodes. Architecture adjustment unknown per source row. Shares classical calibration evidence.",
        )
        row.update(mix_dates(s, row, chronology, overrides, evidence))
        rows.append(row)
    combined = combined_mixes(rows, draws, run["metrics"])
    rows.extend(combined)
    provenance = dict(
        combined_records=len(combined),
        dual_mix_records=sum(r["observation_count"] == 2 for r in combined),
        records=len(rows),
        scenario=scenario,
        cohort=cohort,
        inputs_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
    )
    return rows, provenance
