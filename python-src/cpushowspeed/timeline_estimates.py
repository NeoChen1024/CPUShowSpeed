"""Timeline rows predicted by the saved mix network, and the freshness check of saved bundles.

Nothing is fitted here. Each bundle must have been fitted on the same database
inputs and with the current code; its saved values are copied, never recomputed
from other calibrations.
"""

import csv
import hashlib
import json
import math
from pathlib import Path

from cpushowspeed.mix_network import OUTPUT as MIX_OUTPUT
from cpushowspeed.mix_network import TIMELINE_RUN

MIX_ROUTES = {"InstructionMix:Gibson_KIPS": "Gibson mix", "InstructionMix:ADP_KIPS": "ADP mix"}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def fresh_audit(audit_path: Path, digest: str, digest_key: str, files: dict) -> dict:
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
    audit = fresh_audit(MIX_OUTPUT / "audit.json", digest, "inputs_sha256", {})
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
                quantity="speed",
                mix_combination=r["combination"],
                evidence_class="instruction_mix_estimate_calibrated_to_speed",
                uncertainty_scope="conditional_joint_network_CI95_not_machine_prediction_interval",
                calibration_route="instruction mix + classical network → SPECint92 speed",
                calibration_scenario=run,
                measurement_scope="historical_one_processor_proxy",
                limitation="Mix coefficients rest on unapproved system links and are correlated with the classical route.",
                **dates[members[0]],
            )
        )
    return rows, audit
