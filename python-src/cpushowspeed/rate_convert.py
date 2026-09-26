"""Convert a reported integer-rate score using the saved calibration snapshot."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import click

GENERATIONS = ("cpu92", "cpu95", "cpu2000", "cpu2006", "cpu2017", "cpu2026")


def _generation(value: str) -> str:
    suffix = value.lower().removeprefix("spec").removeprefix("cpu")
    normalized = "cpu" + suffix
    if normalized not in GENERATIONS:
        raise click.BadParameter("choose 92, 95, 2000, 2006, 2017 or 2026 (optional cpu/spec prefix)")
    return normalized


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


def _si(value: float) -> str:
    for scale, prefix in ((1e12, "T"), (1e9, "G"), (1e6, "M"), (1e3, "k"), (1, ""), (1e-3, "m"), (1e-6, "µ")):
        if value >= scale:
            return f"{value / scale:.6g}{prefix}"
    return f"{value:.6g}"


@click.command("convert-rate")
@click.argument("generation")
@click.argument("mode", type=click.Choice(("base", "peak"), case_sensitive=False))
@click.argument("score", type=float)
@click.option("--scenario", type=click.Choice(("same_os", "hardware_near")), default="same_os", show_default=True)
@click.option("--format", "output_format", type=click.Choice(("json", "text")), default="json", show_default=True)
@click.option("--calibration-dir", type=click.Path(path_type=Path), default=Path("research/data/spec/fitting"), show_default=True)
def convert_rate_command(
    generation: str, mode: str, score: float, scenario: str, output_format: str, calibration_dir: Path
) -> None:
    """Convert GENERATION MODE SCORE to estimated VAXen and calibration CI95.

    Example: convert-rate 2017 base 11800 --format text

    Accepts integer-rate scores only. CI95 covers conditional calibration
    sampling uncertainty, not individual-machine prediction error. CPU92
    uses a defined reference scale and has a zero-width calibration interval.
    The saved CSVs suffice; raw submissions and bootstrap arrays are not needed.
    """
    generation = _generation(generation)
    try:
        result = convert_rate(generation, mode.lower(), score, scenario, calibration_dir)
    except (OSError, ValueError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc
    if output_format == "json":
        click.echo(json.dumps(result, sort_keys=True, allow_nan=False))
    else:
        click.echo(f"{generation.upper()} integer rate {mode.lower()} {score:g} [{scenario}]")
        unit = "VAX" if result["vaxen"] == 1 else "VAXen"
        click.echo(f"Estimated: {_si(result['vaxen'])} {unit}")
        click.echo(f"CI95: {_si(result['ci95']['low'])}–{_si(result['ci95']['high'])} VAXen")
        if result["uncertainty_scope"] == "defined_reference":
            click.echo("Defined CPU92 reference scale; zero-width calibration interval.")
        else:
            click.echo("Conditional calibration CI; excludes individual-machine prediction error and systematic bias.")
