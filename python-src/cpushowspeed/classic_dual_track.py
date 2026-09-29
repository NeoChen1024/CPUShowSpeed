"""Re-anchor the sparse classical/mix model separately to observed speed and rate."""

import hashlib
import json
import math
from pathlib import Path

import click
import numpy as np
from cpushowspeed.calibration import ANCHOR, error_summary
from cpushowspeed.classic_89_rate import centers, evidence
from cpushowspeed.classic_bridge_data import bridge_rows
from cpushowspeed.classic_network import evaluate
from cpushowspeed.classic_network_data import build
from cpushowspeed.classic_network_model import bootstrap, train
from cpushowspeed.classic_overlap import compare
from cpushowspeed.input_context import ACTIVE_CATALOG, source_view
from cpushowspeed.mix_network import attach
from cpushowspeed.research_io import code_hashes, read_csv, write_csv
from cpushowspeed.spec_dual_track import collect_speed92

ROOT = Path("data/derived/classic")


def run(output, research, draws, seed):
    paths = [ROOT / "overlap-spec" / n for n in ("classical-records.jsonl", "spec-records.jsonl", "candidate-pairs.csv")]
    paths += [ROOT / "source-pair-fit" / n for n in ("vectors.jsonl", "matching-review.csv")]
    paths += [
        Path("research/data/spec89/v2.0.0/csv/bridges89_92.csv"),
        ROOT / "netlib-linpack-report.txt",
        ROOT / "mix-study/candidate-pairs.csv",
        ROOT / "historical-timeline/observations.csv",
    ]
    classical, specs = [{r["id"]: r for r in source_view(p, view)} for p, view in zip(paths[:2], ("classical", "historical-spec"))]
    vectors = source_view(paths[3], "vectors")
    matching, pages = read_csv(paths[4]), paths[6].read_text().split("\f")
    new = []
    speed_records, speed_audit = collect_speed92(Path("data/raw/spec"))
    for r in speed_records:
        new.append(
            dict(
                id="spec92-speed:" + r.result_id,
                cohort="SPEC92 speed Netlib",
                system=r.system,
                source_url=r.source_url,
                clock_mhz=r.clock_mhz,
                processor_raw=r.processor,
                os_raw=r.os,
                cpu_count=r.chips,
                evidence_class="reported_measurement",
                metrics_raw={"SPECint92": r.peak, "SPECbase_int92": r.base},
                raw_record=dict(source_sha256=r.source_container_sha256),
            )
        )
    specs.update({r["id"]: r for r in new})
    pairs = read_csv(paths[2]) + compare(list(classical.values()), new)
    ev, _ = evidence(list(specs.values()), vectors, bridge_rows(paths[5]))
    mixes, observations = read_csv(paths[7]), read_csv(paths[8])
    # Cached mix links must refer to the same immutable input records.
    for path, digest in json.loads((ROOT / "mix-study/audit.json").read_text())["input_sha256"].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
            raise ValueError("stale mix inventory: " + path)
    output.mkdir(parents=True, exist_ok=True)
    research.mkdir(parents=True, exist_ok=True)
    coefficients, summaries, predictions, records, links, observations_out, audits, evidence_out = [], [], [], [], [], [], [], []
    arrays = {}
    for track, metric, scale in (("speed", "SPECint92", 1.0), ("rate", "SPECrate_int92", ANCHOR)):
        for scaling in (False, True):
            scenario = "linear_clock" if scaling else "reported_clock"
            nodes, obs, clock_audit, aliases = build(classical, specs, pairs, vectors, matching, pages, scaling, metric, scale)
            extended, baseline, link, closure = attach(nodes, mixes, observations)
            links.extend(dict(r, track=track, scenario=scenario) for r in link)
            observations_out.extend(dict(r, track=track, scenario=scenario) for r in obs)
            audits.extend(dict(r, track=track, scenario=scenario) for r in clock_audit)
            aligned = [
                dict(
                    r,
                    model_key=closure.get(aliases.get(r["model_key"], r["model_key"]), aliases.get(r["model_key"], r["model_key"])),
                )
                for r in ev
                if track == "rate" or r["edge"] == "int89_to_int92"
            ]
            evidence_out.extend(dict(r, track=track, scenario=scenario) for r in aligned)
            edges = centers(aligned)
            for kind, selected in (("classical", baseline), ("classical_mix", extended)):
                for enabled in (False, True):
                    context = dict(
                        track=track,
                        target_unit="SPECint92_equivalent" if track == "speed" else "rate_VAXen",
                        scenario=scenario,
                        model=kind,
                        cohort="with_spec89" if enabled else "direct_only",
                    )
                    click.echo("Fitting " + " / ".join(str(v) for v in context.values()), err=True)
                    alpha, _ = train(selected, edges, enabled)
                    metrics, samples = bootstrap(selected, edges, enabled, draws, seed)
                    arrays["__".join((track, scenario, kind, context["cohort"]))] = samples
                    for m in metrics:
                        values = np.exp(samples[:, metrics.index(m)])
                        coefficients.append(
                            dict(
                                context,
                                metric=m,
                                coefficient=math.exp(alpha[m]),
                                ci95_low=float(np.quantile(values, 0.025)),
                                ci95_high=float(np.quantile(values, 0.975)),
                                valid_draws=len(values),
                            )
                        )
                    summary, heldout, _ = evaluate(selected, edges, enabled)
                    summaries.extend(dict(r, **context) for r in summary)
                    for r in heldout:
                        r["target_value"] = r.pop("target_vaxen")
                        r["predicted_value"] = r.pop("predicted_vaxen")
                        predictions.append(dict(r, **context))
                records.extend(
                    dict(
                        track=track,
                        scenario=scenario,
                        model=kind,
                        node_id=n["node_id"],
                        model_key=n["model_key"],
                        target_kind=n["target_kind"],
                        target=n["target"],
                        log_scores=json.dumps(n["log_scores"]),
                    )
                    for n in selected
                )
    # Same observed models, same availability subset, separate target semantics.
    common = []
    for scenario in ("reported_clock", "linear_clock"):
        for kind in ("classical", "classical_mix"):
            for cohort in ("direct_only", "with_spec89"):
                grouped = {
                    t: [
                        r
                        for r in predictions
                        if r["track"] == t
                        and r["scenario"] == scenario
                        and r["model"] == kind
                        and r["cohort"] == cohort
                        and r["method"] == "network"
                        and r["subset"] == "all_available"
                        and r["target_kind"] == "observed_" + t
                    ]
                    for t in ("speed", "rate")
                }
                keys = {r["model_key"] for r in grouped["speed"]} & {r["model_key"] for r in grouped["rate"]}
                for track, group in grouped.items():
                    selected = [r for r in group if r["model_key"] in keys]
                    if selected:
                        common.append(
                            dict(
                                track=track,
                                scenario=scenario,
                                model=kind,
                                cohort=cohort,
                                common_models=len(keys),
                                rows=len(selected),
                                model_keys=";".join(sorted(keys)),
                                **error_summary(selected),
                            )
                        )
    for name, rows in (("coefficients", coefficients), ("holdout-summary", summaries), ("common-model-comparison", common)):
        write_csv(research / (name + ".csv"), rows)
    write_csv(output / "speed-source-audit.csv", speed_audit)
    plot_comparison(common, output)
    for name, rows in (
        ("nodes", records),
        ("holdouts", predictions),
        ("mix-attachment", links),
        ("observations", observations_out),
        ("clock-audit", audits),
        ("bridge-evidence", evidence_out),
        ("candidate-pairs", pairs),
    ):
        write_csv(output / (name + ".csv"), rows)
    np.savez_compressed(output / "coefficient-log-draws.npz", **arrays)
    report = dict(
        method="dual-target-sparse-network-v1",
        code_hashes=code_hashes(__file__),
        speed_source_hashes={r.source_url: r.source_container_sha256 for r in speed_records},
        bootstrap_replicates=draws,
        seed=seed,
        speed92_records=len(new),
        source_hashes={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        target_units={"speed": "SPECint92_equivalent", "rate": "rate_VAXen"},
        limitations=[
            "Same-model comparisons do not guarantee identical OS/compiler/copy/thread configurations",
            "Speed uses only the SPEC89-to-SPEC92 bridge; no speed-to-rate edge",
            "Factor CI95 excludes unmodelled architecture/transport bias",
            "No prediction manifest or timeline scores replaced",
        ],
    )
    (research / "audit.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def plot_comparison(rows, output):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    labels = [(model, cohort) for model in ("classical", "classical_mix") for cohort in ("direct_only", "with_spec89")]
    for ax, scenario in zip(axes, ("reported_clock", "linear_clock")):
        for track, color, offset in (("speed", "#17628a", -0.1), ("rate", "#b76520", 0.1)):
            selected = {(r["model"], r["cohort"]): r for r in rows if r["scenario"] == scenario and r["track"] == track}
            ax.scatter(
                [selected[k]["model_center_p95_percent"] for k in labels if k in selected],
                [i + offset for i, k in enumerate(labels) if k in selected],
                label=track,
                c=color,
            )
        ax.set_yticks(range(len(labels)), [" / ".join(k) for k in labels])
        ax.set(title=scenario, xlabel="Held-out model-center P95 error (%)")
        ax.grid(alpha=0.2)
        ax.legend()
    fig.suptitle(
        "Classical and mix fits: common observed hardware models\nSeparate speed/rate targets; configurations and available inputs may differ"
    )
    for ext in ("png", "svg"):
        fig.savefig(output / ("common-model-comparison." + ext), dpi=160)
    plt.close(fig)


@click.command("compare-targets")
@click.option("--output-dir", type=click.Path(path_type=Path), default=ROOT / "dual-track", show_default=True)
@click.option(
    "--research-dir", type=click.Path(path_type=Path), default=Path("research/data/classic/dual-track"), show_default=True
)
@click.option("--bootstrap", "draws", type=click.IntRange(min=100), default=10000, show_default=True)
@click.option("--seed", type=int, default=20260929, show_default=True)
def compare_targets(output_dir, research_dir, draws, seed):
    """Compare classical/mix fits to SPEC92 speed and rate as separate targets."""
    try:
        result = run(output_dir, research_dir, draws, seed)
    except (OSError, ValueError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, sort_keys=True))
