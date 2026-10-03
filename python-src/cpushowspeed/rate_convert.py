"""Convert a reported integer-rate score using the saved calibration snapshot."""

from __future__ import annotations

import csv
import hashlib
import math
from pathlib import Path


def _positive(value: object, field: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{field} must be finite and greater than zero")
    return number


def _matching(rows: list[dict], generation: str, mode: str, scenario: str) -> dict:
    matches = [row for row in rows if (row["generation"], row["mode"], row["scenario"]) == (generation, mode, scenario)]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one calibration for {generation}/{mode}/{scenario}, found {len(matches)}")
    return matches[0]


def convert_rate(generation: str, mode: str, score: float, scenario: str, calibration_dir: Path) -> dict:
    score = _positive(score, "score")
    interval_path = calibration_dir / "integer-rate-chain-intervals.csv"
    chain_path = calibration_dir / "integer-rate-cpu92-vaxen-chain.csv"
    interval_bytes = interval_path.read_bytes()
    chain_bytes = chain_path.read_bytes()
    interval_rows = list(csv.DictReader(interval_bytes.decode("utf-8").splitlines()))
    chain_rows = list(csv.DictReader(chain_bytes.decode("utf-8").splitlines()))
    interval = _matching(interval_rows, generation, mode, scenario)
    chain = _matching(chain_rows, generation, mode, scenario)
    chain_hash = hashlib.sha256(chain_bytes).hexdigest()
    if interval["factor_chain_sha256"] != chain_hash:
        raise ValueError("confidence table is stale for the factor chain; rerun bridge bootstrap-rate-chain")
    factor = _positive(interval["vaxen_per_rate_score"], "calibration factor")
    low = _positive(interval["bootstrap_95_low"], "CI lower factor")
    high = _positive(interval["bootstrap_95_high"], "CI upper factor")
    if low > high or float(interval["confidence_level"]) != 0.95:
        raise ValueError("invalid 95% calibration interval")
    if not math.isclose(factor, _positive(chain["vaxen_per_rate_score"], "chain factor"), rel_tol=1e-12):
        raise ValueError("confidence table central factor differs from the saved chain")
    values = [score * value for value in (factor, low, high)]
    if not all(math.isfinite(value) and value > 0 for value in values):
        raise ValueError("converted score is outside the finite positive numeric range")
    return {
        "generation": generation,
        "metric_family": "SPEC integer rate",
        "mode": mode,
        "reported_score": score,
        "calibration_scenario": scenario,
        "vaxen": values[0],
        "ci95": {"low": values[1], "high": values[2]},
        "vaxen_per_rate_score": factor,
        "confidence_level": 0.95,
        "uncertainty_scope": interval["scope"],
        "reference": "VAX-11/780 one-copy CPU92 integer-rate throughput",
        "calibration_method": interval["method_version"],
        "factor_chain_sha256": chain_hash,
        "interval_table_sha256": hashlib.sha256(interval_bytes).hexdigest(),
    }
