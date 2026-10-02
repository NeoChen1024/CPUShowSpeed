"""Timeline rows predicted by the saved mix network and SPEC speed/rate predictors.

Nothing is fitted here. Each bundle must have been fitted on the same database
inputs and with the current code; its saved values are copied, never recomputed
from other calibrations.
"""

import csv
import hashlib
import json
import math
from pathlib import Path

from cpushowspeed.annual_rate import _month
from cpushowspeed.mix_network import OUTPUT as MIX_OUTPUT
from cpushowspeed.mix_network import TIMELINE_RUN
from cpushowspeed.observation_store import spec_results
from cpushowspeed.spec_predictors import DERIVED as PREDICTOR_OUTPUT
from cpushowspeed.spec_predictors import RESEARCH as PREDICTOR_RESEARCH
from cpushowspeed.spec_rate_fit import GENERATIONS

MIX_ROUTES = {"InstructionMix:Gibson_KIPS": "Gibson mix", "InstructionMix:ADP_KIPS": "ADP mix"}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _fresh(audit_path: Path, digest: str, digest_key: str, files: dict) -> dict:
    """The audit of a saved bundle, after checking its database inputs, code and output files are current."""
    audit = json.loads(audit_path.read_text())
    if audit[digest_key] != digest:
        raise ValueError(f"{audit_path} was fitted on other database inputs; rerun its fit")
    for path, expected in {**audit["code_sha256"], **files}.items():
        if not Path(path).is_file() or _sha(Path(path)) != expected:
            raise ValueError(f"{path} changed since {audit_path} was written; rerun its fit")
    return audit


def _values(score, vaxen, low, high):
    values = [score * float(v) for v in (vaxen, low, high)]
    if not all(math.isfinite(v) and v > 0 for v in values) or not values[1] <= values[0] <= values[2]:
        raise ValueError("invalid saved estimate or interval")
    return dict(zip(("vaxen", "ci95_low", "ci95_high"), values))


def mix_rows(dates, digest):
    """Every Gibson/ADP rating and every source row's combined available mixes, from the timeline run of the mix network."""
    audit = _fresh(MIX_OUTPUT / "audit.json", digest, "inputs_sha256", {})
    run = " / ".join(TIMELINE_RUN[k] for k in ("links", "scenario", "cohort"))
    rows = []
    for r in _read(MIX_OUTPUT / "mix-estimates.csv"):
        if any(r[k] != v for k, v in TIMELINE_RUN.items()):
            continue
        members = json.loads(r["result_ids"])
        scores = {k: float(v) for k, v in json.loads(r["scores"]).items()}
        single = r["kind"] == "single"
        rows.append(
            dict(
                record_id=r["record_id"] if single else r["record_id"] + ":combined",
                configuration_id=r["record_id"],
                result_id=members[0] if single else r["record_id"],
                route=MIX_ROUTES[next(iter(scores))] if single else "Combined mixes",
                generation="instruction_mix",
                mode="peak_proxy",
                estimate_kind="mix" if single else "mix_combined",
                system=r["system"],
                system_id=r["system_id"],
                cpu="",
                clock_mhz="",
                os="",
                configuration="",
                scores=scores,
                reported_score=next(iter(scores.values())) if single else None,
                reported_unit="KIPS",
                benchmark_id=next(iter(scores)) if single else "Gibson+ADP available mixes",
                observation_count=len(members),
                source_record_ids=members,
                source_url=r["source_url"],
                benchmark_sources=[r["source_url"]],
                **_values(1.0, r["estimated_vaxen"], r["ci95_low"], r["ci95_high"]),
                estimated_specint92_rate=float(r["estimated_rate"]),
                mix_combination=r["combination"],
                evidence_class="instruction_mix_estimate_calibrated_to_rate",
                uncertainty_scope="conditional_joint_network_CI95_not_machine_prediction_interval",
                calibration_route="instruction mix + classical network → CPU92 rate",
                calibration_scenario=run,
                measurement_scope="historical_one_processor_proxy",
                limitation="Mix coefficients rest on unapproved system links and are correlated with the classical route.",
                **dates[members[0]],
            )
        )
    return rows, audit


def _predictors(digest):
    files = {str(p): _sha(p) for p in (PREDICTOR_RESEARCH / "summary.csv", PREDICTOR_OUTPUT / "speed-rate-pairs.csv")}
    audit = _fresh(PREDICTOR_RESEARCH / "audit.json", digest, "database_inputs_sha256", {})
    for path, expected in audit["files_sha256"].items():
        if path in files and files[path] != expected:
            raise ValueError(f"{path} differs from its predictor audit; rerun bridge fit-speed-predictors")
    fits = {
        (r["new_generation"], r["mode"], r["method"]): r
        for r in _read(PREDICTOR_RESEARCH / "summary.csv")
        if r["status"] == "conditional_fit"
    }
    return fits, audit


def _common(result):
    raw = result.raw_fields
    return dict(
        system=result.system,
        system_id=result.system_key,
        cpu=result.processor,
        clock_mhz=result.clock_mhz or "",
        os=result.os,
        configuration="",
        chips=result.chips or "",
        cores=result.cores or "",
        threads_per_core=result.enabled_threads_per_core or "",
        copies_min="",
        copies_max="",
        nodes="",
        source_container_sha256=result.source_container_sha256,
        hardware_date=_month(raw.get("HW Avail") or ""),
        submission_date=_month(raw.get("Published") or ""),
        test_date=_month(raw.get("Test Date") or ""),
    )


def predictor_rows(db, dates, digest):
    """Speed-only estimates of every speed result and joint estimates of every hardware-near speed/rate pair."""
    fits, audit = _predictors(digest)
    speeds = {g: {r.result_id: r for r in spec_results(db, g, "speed")} for g in GENERATIONS}
    rates = {g: {r.result_id: r for r in spec_results(db, g, "rate")} for g in GENERATIONS}
    rows = []
    for generation in GENERATIONS:
        for result in speeds[generation].values():
            for mode in ("base", "peak"):
                score, fit = getattr(result, mode), fits.get((generation, mode, "speed_only"))
                if score is None or fit is None:
                    continue
                rid = f"spec:{generation}:speed:{result.result_id}"
                benchmark = f"{generation.upper()} integer speed {mode}"
                rows.append(
                    dict(
                        record_id=f"speed:{generation}:{result.result_id}:{mode}",
                        configuration_id=rid,
                        result_id=rid,
                        route=generation.upper(),
                        generation=generation,
                        mode=mode,
                        estimate_kind="speed",
                        scores={benchmark: score},
                        reported_score=score,
                        reported_unit=generation.upper() + " native integer speed points",
                        benchmark_id=benchmark,
                        observation_count=1,
                        source_record_ids=[rid],
                        source_url=result.source_url,
                        benchmark_sources=[result.source_url],
                        **_common(result),
                        **_values(score, fit["coefficient_vaxen"], fit["vaxen_ci95_low"], fit["vaxen_ci95_high"]),
                        evidence_class="speed_inferred_rate_estimate",
                        measurement_scope="predicted_reported_system_rate",
                        calibration_route=f"{generation.upper()} speed → {fit['old_generation'].upper()} rate → CPU92 rate",
                        calibration_scenario="hardware_near / same_os",
                        uncertainty_scope="conditional full-route coefficient CI95; not a prediction interval",
                        limitation="Speed predicts throughput here; it is not speed-VAXen. Transfer beyond overlap hardware is unvalidated.",
                        **dates[rid],
                    )
                )
    for pair in _read(PREDICTOR_OUTPUT / "speed-rate-pairs.csv"):
        generation = pair["generation"]
        s, r = speeds[generation][pair["speed_id"]], rates[generation][pair["rate_id"]]
        for mode in ("base", "peak"):
            fit = fits.get((generation, mode, "equal_geometric"))
            speed, rate = getattr(s, mode), getattr(r, mode)
            if fit is None or speed is None or rate is None:
                continue
            ids = [f"spec:{generation}:speed:{s.result_id}", f"spec:{generation}:rate:{r.result_id}"]
            rows.append(
                dict(
                    record_id=f"joint:{generation}:{r.result_id}:{s.result_id}:{mode}",
                    configuration_id=f"joint:{generation}:{r.result_id}:{s.result_id}",
                    result_id=ids[1],
                    route=generation.upper(),
                    generation=generation,
                    mode=mode,
                    estimate_kind="joint",
                    scores={"speed": speed, "rate": rate},
                    reported_score=None,
                    reported_unit=generation.upper() + " native speed and rate points",
                    benchmark_id=f"{generation.upper()} paired integer speed/rate {mode}",
                    observation_count=2,
                    source_record_ids=ids,
                    source_url=r.source_url,
                    benchmark_sources=[s.source_url, r.source_url],
                    **_common(r),
                    **_values(math.sqrt(speed * rate), fit["coefficient_vaxen"], fit["vaxen_ci95_low"], fit["vaxen_ci95_high"]),
                    speed_system=s.system,
                    evidence_class="paired_speed_rate_estimate",
                    measurement_scope="predicted_reported_system_rate",
                    calibration_route=f"{generation.upper()} speed + rate → {fit['old_generation'].upper()} rate → CPU92 rate",
                    calibration_scenario="hardware_near / same_os",
                    uncertainty_scope="conditional joint full-route coefficient CI95; not a prediction interval",
                    limitation="Hardware-near speed/rate pair; the pair's date follows the rate input.",
                    **dates[ids[1]],
                )
            )
    return rows, audit
