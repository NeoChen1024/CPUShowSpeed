"""Validate cached rate-factor provenance before consuming the chain."""

import csv
import hashlib
import math
from pathlib import Path

from cpushowspeed.spec92_rate_fit import VAX_RATE92_REFERENCE
from cpushowspeed.spec_rate_fit import GENERATIONS

SCENARIOS = ("same_os", "hardware_near")
MODES = ("base", "peak")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rate_factors(raw_dir: Path, cpu92_records: Path, research_dir: Path, fit_dir: Path) -> dict[tuple[str, str, str], float]:
    direct_path = research_dir / "cpu92-cpu95-rate-direct-factors.csv"
    later_path = research_dir / "integer-rate-factors.csv"
    chain_path = research_dir / "integer-rate-cpu92-vaxen-chain.csv"
    pair_path = fit_dir / "cpu92-cpu95-rate-pairs.csv"
    with direct_path.open(newline="") as stream:
        direct = list(csv.DictReader(stream))
    with later_path.open(newline="") as stream:
        later = list(csv.DictReader(stream))
    with chain_path.open(newline="") as stream:
        chain = list(csv.DictReader(stream))
    if len(direct) != 4 or len(later) != 8 or len(chain) != 24:
        raise ValueError("rate factor tables have unexpected coverage; rerun the rate fits")
    for row in direct:
        if row["cpu92_records_sha256"] != _sha256(cpu92_records):
            raise ValueError("CPU92 direct fit is stale; rerun fit-rate92-anchor")
        if row["cpu95_bulk_sha256"] != _sha256(raw_dir / "cpu95" / "bulk.csv"):
            raise ValueError("CPU95 direct fit is stale; rerun fit-rate92-anchor")
        if row["pair_export_sha256"] != _sha256(pair_path):
            raise ValueError("CPU92 pair export differs from its factor table")
    edge = {}
    later_pair_hash = _sha256(fit_dir / "integer-rate-generation-pairs.csv")
    for row in later:
        old, new = row["old_generation"], row["new_generation"]
        if row["pair_export_sha256"] != later_pair_hash:
            raise ValueError("later rate pair export differs from its factor table")
        if row["scenario"] != "strict" or row["old_input_sha256"] != _sha256(raw_dir / old / "bulk.csv"):
            raise ValueError(f"stale or non-strict rate fit for {old}")
        if row["new_input_sha256"] != _sha256(raw_dir / new / "bulk.csv"):
            raise ValueError(f"stale rate fit for {new}")
        edge[old, new, row["mode"]] = float(row["factor_old_per_new"])
    factors = {}
    for row in direct:
        scenario, mode = row["scenario"], row["mode"]
        if scenario not in SCENARIOS or mode not in MODES:
            raise ValueError("unexpected direct rate fit scenario or mode")
        factors[scenario, mode, "cpu92"] = 1 / VAX_RATE92_REFERENCE
        factors[scenario, mode, "cpu95"] = float(row["vaxen_per_cpu95_rate_score"])
        for old, new in zip(GENERATIONS, GENERATIONS[1:]):
            factors[scenario, mode, new] = factors[scenario, mode, old] * edge[old, new, mode]
    if len(factors) != 24:
        raise ValueError("incomplete rate normalization chain")
    for row in chain:
        key = row["scenario"], row["mode"], row["generation"]
        if key not in factors or not math.isclose(factors[key], float(row["vaxen_per_rate_score"]), rel_tol=1e-12):
            raise ValueError(f"rate chain disagrees with edge factors: {key}")
    return factors
