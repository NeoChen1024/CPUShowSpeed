"""Joint speed/rate predictors with distinct, earlier-generation rate targets."""

import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

import click
import numpy as np
from cpushowspeed.calibration import ANCHOR, error_summary
from cpushowspeed.execution_policy import POLICY, agreement
from cpushowspeed.input_context import snapshot_identity
from cpushowspeed.research_io import code_hashes, write_csv
from cpushowspeed.spec92_rate_fit import _software_near, collect_cpu92_rate
from cpushowspeed.spec95_overlap_audit import (
    ALIASES,
    MEMORY,
    blockers,
    candidate_processor_key,
    candidate_system_key,
)
from cpushowspeed.spec_inputs import runtime_fingerprint
from cpushowspeed.spec_overlap import _automatic_pairs, _pair
from cpushowspeed.spec_rate_chain import configuration_logs
from cpushowspeed.spec_rate_fit import GENERATIONS, MODES, collect_integer

METHODS = {"speed_only": 1.0, "rate_only": 0.0, "equal_geometric": 0.5}
EDGES = tuple(zip(("cpu92", *GENERATIONS), GENERATIONS))
VERSION = "joint-spec-predictors-v4-execution-evidence"
MIN_MODELS = 3
MATCHING_POLICIES = ("strict", "ram-aliases", "cpu-clock")
ELIGIBLE_MATCH_TIERS = {"hardware_near", "platform_alias_ram_relaxed", "cpu_clock_resources"}


def match(left, right, policy="strict"):
    if policy not in MATCHING_POLICIES:
        raise ValueError("unknown matching policy: " + policy)
    if policy == "strict":
        return _automatic_pairs({"left": left, "right": right}, "left", "right")
    allowed = MEMORY | ALIASES
    if policy == "cpu-clock":
        allowed |= {"unresolved_system"}

    def key(item):
        return (candidate_processor_key(item), item.chips, candidate_system_key(item) if policy == "ram-aliases" else "")

    indexed = defaultdict(list)
    for item in right:
        indexed[key(item)].append(item)
    pairs = []
    for a in left:
        for b in indexed[key(a)]:
            flags = blockers(a, b)
            tier = (
                ("platform_alias_ram_relaxed" if policy == "ram-aliases" else "cpu_clock_resources")
                if flags <= allowed
                else "name_cpu_chips_only"
            )
            row = _pair(a, b, tier)
            row.update(
                matching_policy=policy,
                matching_blockers=json.dumps(sorted(flags)),
                processor_key=candidate_processor_key(a),
                system_key=candidate_system_key(a) if policy == "ram-aliases" else a.system_key,
            )
            pairs.append(row)
    return pairs


def triangles(targets, speeds, rates, policy="strict"):
    """Retain every observed triple passing all three hardware-near edges."""
    rate_pairs, speed_pairs, within = match(targets, rates, policy), match(targets, speeds, policy), match(rates, speeds, policy)
    rate_map, speed_map = defaultdict(list), defaultdict(list)
    for pairs, index in ((rate_pairs, rate_map), (speed_pairs, speed_map)):
        for p in pairs:
            if p["match_tier"] in ELIGIBLE_MATCH_TIERS:
                index[p["old_result_id"]].append(p)
    compatible = {(p["old_result_id"], p["new_result_id"]) for p in within if p["match_tier"] in ELIGIBLE_MATCH_TIERS}
    source = {r.source_url: r for r in [*targets, *speeds, *rates]}
    rows, rejected = [], []
    for target in sorted(rate_map.keys() & speed_map.keys()):
        for rp in rate_map[target]:
            for sp in speed_map[target]:
                t, r, s = [source[url] for url in (rp["old_source_url"], rp["new_source_url"], sp["new_source_url"])]
                reasons = []
                if (rp["new_result_id"], sp["new_result_id"]) not in compatible:
                    reasons.append("new_speed_rate_configuration_conflict")
                if len({t.source_url, r.source_url, s.source_url}) != 3:
                    reasons.append("reused_target_or_predictor_submission")
                common = dict(
                    old_generation=t.generation,
                    new_generation=r.generation,
                    model_key=rp["processor_key"],
                    system_key=rp["system_key"],
                    matching_policy=policy,
                    relaxed_fields=(
                        json.dumps(sorted(blockers(t, s) | blockers(t, r) | blockers(r, s))) if policy != "strict" else "[]"
                    ),
                    chips=t.chips,
                    clock_mhz=t.clock_mhz,
                    target_id=t.result_id,
                    speed_id=s.result_id,
                    rate_id=r.result_id,
                    target_url=t.source_url,
                    speed_url=s.source_url,
                    rate_url=r.source_url,
                    target_sha256=t.source_container_sha256,
                    speed_sha256=s.source_container_sha256,
                    rate_sha256=r.source_container_sha256,
                    target_system=t.system,
                    speed_system=s.system,
                    rate_system=r.system,
                    target_os=t.os,
                    speed_os=s.os,
                    rate_os=r.os,
                    target_compiler=t.compiler,
                    speed_compiler=s.compiler,
                    rate_compiler=r.compiler,
                    qualification=f"matching_policy={policy};runtime_copies_threads_and_software_equivalence_unverified",
                )
                for role, item in (("target", t), ("speed", s), ("rate", r)):
                    for field in ("cores", "enabled_threads_per_core", "clock_mhz", "memory_mib"):
                        common[f"{role}_{field}"] = getattr(item, field)
                if reasons:
                    rejected.append(dict(common, reason=";".join(reasons)))
                    continue
                for mode in MODES:
                    execution_status = agreement(t, r, mode)
                    if execution_status == "confirmed_count_conflict":
                        rejected.append(dict(common, mode=mode, reason="rate_copies_conflict"))
                        continue
                    y, sv, rv = (getattr(item, mode) for item in (t, s, r))
                    if any(v is None for v in (y, sv, rv)):
                        rejected.append(dict(common, mode=mode, reason="incomplete_positive_score_triplet"))
                    else:
                        rows.append(
                            dict(
                                common,
                                mode=mode,
                                target_rate=y,
                                speed_score=sv,
                                rate_score=rv,
                                rate_execution_status=execution_status,
                            )
                        )
    audit = dict(
        target_rate_candidates=len(rate_pairs),
        target_speed_candidates=len(speed_pairs),
        target_rate_hardware_near=sum(p["match_tier"] == "hardware_near" for p in rate_pairs),
        target_speed_hardware_near=sum(p["match_tier"] == "hardware_near" for p in speed_pairs),
        target_rate_eligible=sum(p["match_tier"] in ELIGIBLE_MATCH_TIERS for p in rate_pairs),
        target_speed_eligible=sum(p["match_tier"] in ELIGIBLE_MATCH_TIERS for p in speed_pairs),
        complete_mode_triples=len(rows),
        rejected_triples_or_modes=len(rejected),
        target_reuse_policy="three_distinct_submission_urls_required",
    )
    return rows, rejected, rate_pairs, audit


def predictor_log(row, method):
    w = METHODS[method]
    # Explicit masks: the absent input must never be read or imputed.
    if w == 1:
        return math.log(row["speed_score"])
    if w == 0:
        return math.log(row["rate_score"])
    return w * math.log(row["speed_score"]) + (1 - w) * math.log(row["rate_score"])


def configuration_centers(rows, method):
    systems, configs = defaultdict(list), defaultdict(list)
    for row in rows:
        key = (row["model_key"], int(row["chips"]), round(float(row["clock_mhz"]), 1))
        systems[(row["system_key"], *key)].append(math.log(row["target_rate"]) - predictor_log(row, method))
    for key, values in systems.items():
        configs[key[1:]].append(statistics.median(values))
    return {key: statistics.median(values) for key, values in sorted(configs.items())}


def log_factor(logs, exclude=None, minimum=MIN_MODELS):
    selected = {key: value for key, value in logs.items() if key[0] != exclude}
    if len({key[0] for key in selected}) < minimum:
        return None
    return statistics.mean(selected.values())


def bootstrap_means(logs, weights, index):
    if not logs:
        return np.full(len(weights), np.nan)
    w = weights[:, [index[key[0]] for key in logs]]
    total = w.sum(axis=1)
    return np.divide(w @ np.asarray(list(logs.values())), total, out=np.full(len(weights), np.nan), where=total > 0)


def prefix_log(backbone, edge_index, exclude=None):
    total = math.log(ANCHOR)
    for logs in backbone[:edge_index]:
        value = log_factor(logs, exclude, minimum=2 if exclude is not None else MIN_MODELS)
        if value is None:
            return None
        total += value
    return total


def evaluate(rows, method, backbone, edge_index):
    """Whole CPU-model holdout, including every upstream rate edge."""
    logs = configuration_centers(rows, method)
    models = sorted({key[0] for key in logs})
    summary = dict(
        method=method,
        speed_weight=METHODS[method],
        tuples=len(rows),
        processor_configs=len(logs),
        models=len(models),
        status="insufficient_models",
    )
    if len(models) < MIN_MODELS:
        return summary, [], [], logs
    point = log_factor(logs)
    prefix = prefix_log(backbone, edge_index)
    summary.update(
        status="conditional_fit",
        coefficient_older_rate=math.exp(point),
        coefficient_vaxen=math.exp(point + prefix) if prefix is not None else None,
    )
    predictions, config_errors = [], []
    for model in models:
        fold = log_factor(logs, model, minimum=2)
        folded_prefix = prefix_log(backbone, edge_index, model)
        if fold is None:
            raise ValueError("unexpected empty model holdout")
        for key, value in logs.items():
            if key[0] == model:
                config_errors.append(dict(model_key=model, chips=key[1], clock_mhz=key[2], log_error=fold - value))
        for row in rows:
            if row["model_key"] != model:
                continue
            predicted = fold + predictor_log(row, method)
            predictions.append(
                dict(
                    row,
                    method=method,
                    input_mask={"speed_only": "rate_hidden", "rate_only": "speed_hidden", "equal_geometric": "both_visible"}[
                        method
                    ],
                    predicted_older_rate=math.exp(predicted),
                    log_error=predicted - math.log(row["target_rate"]),
                    training_coefficient_older_rate=math.exp(fold),
                    training_prefix_vaxen_per_older_rate=math.exp(folded_prefix) if folded_prefix is not None else None,
                    predicted_vaxen=math.exp(predicted + folded_prefix) if folded_prefix is not None else None,
                    observed_target_vaxen=row["target_rate"] * ANCHOR if edge_index == 0 else None,
                    target_evidence=(
                        "observed_cpu92_rate" if edge_index == 0 else "observed_older_suite_rate;no_observed_vaxen_target"
                    ),
                    prefix_status="available_model_excluded" if folded_prefix is not None else "insufficient_after_model_exclusion",
                )
            )
    summary.update(error_summary(predictions))
    summary["model_center_p95_percent"] = error_summary(config_errors)["model_center_p95_percent"]
    summary["primary_error_unit"] = "CPU_model_median_of_configuration_log_residuals"
    summary["holdout_scope"] = "all_configurations_of_processor_key;excluded_from_all_prefix_edges"
    return summary, predictions, config_errors, logs


def plot(rows, output):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {"speed_only": "#17628a", "rate_only": "#b76520", "equal_geometric": "#38844b"}
    fig, axes = plt.subplots(1, 2, figsize=(13, 6), constrained_layout=True, sharex=True, sharey=True)
    for ax, mode in zip(axes, MODES):
        for j, (method, color) in enumerate(colors.items()):
            selected = {r["new_generation"]: r for r in rows if r["mode"] == mode and r["method"] == method}
            for i, generation in enumerate(GENERATIONS):
                row = selected[generation]
                if row["status"] == "conditional_fit":
                    x = row["model_center_p95_percent"]
                    y = i + (j - 1) * 0.18
                    ax.scatter(x, y, color=color, label=method if i == 0 else None)
                    ax.annotate(f"{x:.1f}%", (x, y), xytext=(5, 0), textcoords="offset points", va="center", fontsize=8)
                elif method == "equal_geometric":
                    ax.text(
                        0.98,
                        i,
                        f"insufficient: {row['models']} model(s)",
                        ha="right",
                        va="center",
                        transform=ax.get_yaxis_transform(),
                        fontsize=8,
                    )
        ax.set_yticks(range(len(EDGES)), [f"{new.upper()} → {old.upper()} rate" for old, new in EDGES])
        ax.set(title=mode, xlabel="Held-out CPU-model center P95 error (%)", xlim=(0, None))
        ax.grid(alpha=0.2)
        ax.legend(loc="upper right", fontsize=8)
    axes[0].invert_yaxis()
    fig.suptitle(
        f"Joint speed/rate predictors; all-generation matching: {rows[0].get('matching_scenario', 'strict')}\nCPU95 targets measured CPU92 rate; later rows validate only the adjacent observed-rate edge"
    )
    maximum = max((r.get("model_center_p95_percent", 0) for r in rows), default=1)
    axes[0].set_xlim(0, max(1, maximum) * 1.25)
    for ext in ("png", "svg"):
        fig.savefig(output / ("joint-holdout-comparison." + ext), dpi=160)
    plt.close(fig)


def analyze(raw, cpu92_records, output, research, draws, seed, matching_policy="strict"):
    output.mkdir(parents=True, exist_ok=True)
    research.mkdir(parents=True, exist_ok=True)
    speeds, rates = collect_integer(raw, "speed"), collect_integer(raw, "rate")
    rates["cpu92"] = collect_cpu92_rate(cpu92_records, raw)
    canonical_processors = {r.processor_key: candidate_processor_key(r) for group in rates.values() for r in group}
    triples, rejected, rate_cohorts, coverage = [], [], [], []
    for old, new in EDGES:
        policy = matching_policy
        rows, rejects, pairs, audit = triangles(rates[old], speeds[new], rates[new], policy)
        if matching_policy != "strict":
            # Use one alias identity throughout the holdout/bootstrap graph.
            for row in rows:
                row["model_key"] = canonical_processors.get(row["model_key"], row["model_key"])
            for pair in pairs:
                pair["processor_key"] = canonical_processors.get(pair["processor_key"], pair["processor_key"])
        triples.extend(rows)
        rejected.extend(rejects)
        rate_cohorts.append([p for p in pairs if p["match_tier"] in ELIGIBLE_MATCH_TIERS and (old != "cpu92" or _software_near(p))])
        coverage.append(dict(old_generation=old, new_generation=new, matching_policy=policy, **audit))
    backbone = {mode: [configuration_logs(cohort, mode) for cohort in rate_cohorts] for mode in MODES}
    # Common bootstrap weights preserve speed/rate pairing and shared hardware across edges.
    keys = sorted({key[0] for mode in MODES for edge in backbone[mode] for key in edge} | {r["model_key"] for r in triples})
    if not keys:
        raise ValueError("no matched hardware groups")
    index = {key: i for i, key in enumerate(keys)}
    weights = np.random.default_rng(seed).multinomial(len(keys), np.full(len(keys), 1 / len(keys)), size=draws)
    summaries, predictions, config_errors, arrays, config_rows = [], [], [], {}, []
    backbone_summary = []
    for mode in MODES:
        prefix_samples = np.full(draws, math.log(ANCHOR))
        for i, (old, new) in enumerate(EDGES):
            rows = [r for r in triples if r["mode"] == mode and r["new_generation"] == new]
            for method in METHODS:
                summary, heldout, errors, logs = evaluate(rows, method, backbone[mode], i)
                summary.update(
                    old_generation=old,
                    new_generation=new,
                    mode=mode,
                    matching_scenario=matching_policy,
                    local_matching_policy=matching_policy,
                    target_unit="older_suite_rate",
                    vaxen_route="local_predictor_then_upstream_rate_chain",
                    bootstrap_unit="shared_processor_model",
                    seed=seed,
                    requested_draws=draws,
                )
                if summary["status"] == "conditional_fit":
                    samples = bootstrap_means(logs, weights, index)
                    valid = np.isfinite(samples)
                    low, high = np.quantile(np.exp(samples[valid]), [0.025, 0.975])
                    summary.update(local_ci95_low=float(low), local_ci95_high=float(high), valid_local_draws=int(valid.sum()))
                    chain = samples + prefix_samples
                    # Do not expose chain estimates when an upstream edge lacks the minimum support.
                    prefix_ok = prefix_log(backbone[mode], i) is not None
                    valid_chain = np.isfinite(chain) & prefix_ok
                    if valid_chain.any():
                        low, high = np.quantile(np.exp(chain[valid_chain]), [0.025, 0.975])
                        summary.update(
                            vaxen_ci95_low=float(low), vaxen_ci95_high=float(high), valid_chain_draws=int(valid_chain.sum())
                        )
                    arrays[f"{new}__{mode}__{method}__log_vaxen"] = np.where(valid_chain, chain, np.nan)
                    arrays[f"{new}__{mode}__{method}__log_local"] = samples
                summaries.append(summary)
                predictions.extend(heldout)
                config_errors.extend(dict(r, mode=mode, old_generation=old, new_generation=new, method=method) for r in errors)
                config_rows.extend(
                    dict(
                        kind="local",
                        mode=mode,
                        old_generation=old,
                        new_generation=new,
                        method=method,
                        model_key=k[0],
                        chips=k[1],
                        clock_mhz=k[2],
                        log_ratio=v,
                    )
                    for k, v in logs.items()
                )
            logs = backbone[mode][i]
            config_rows.extend(
                dict(
                    kind="upstream_rate",
                    mode=mode,
                    old_generation=old,
                    new_generation=new,
                    method="rate_only",
                    model_key=k[0],
                    chips=k[1],
                    clock_mhz=k[2],
                    log_ratio=v,
                )
                for k, v in logs.items()
            )
            prefix_samples += bootstrap_means(logs, weights, index)
            valid = np.isfinite(prefix_samples)
            point = prefix_log(backbone[mode], i + 1)
            if point is not None and valid.any():
                low, high = np.quantile(np.exp(prefix_samples[valid]), [0.025, 0.975])
                backbone_summary.append(
                    dict(
                        generation=new,
                        mode=mode,
                        coefficient=math.exp(point),
                        ci95_low=float(low),
                        ci95_high=float(high),
                        valid_draws=int(valid.sum()),
                        matching_policy=matching_policy,
                    )
                )
                arrays[f"backbone__{new}__{mode}__log_vaxen"] = prefix_samples.copy()
    write_csv(research / "summary.csv", summaries)
    write_csv(research / "backbone-summary.csv", backbone_summary)
    write_csv(research / "coverage.csv", coverage)
    for name, rows in (
        ("triples", triples),
        ("rejections", rejected),
        ("holdout-predictions", predictions),
        ("holdout-configurations", config_errors),
        ("configuration-centers", config_rows),
        ("rate-backbone-pairs", [p for cohort in rate_cohorts for p in cohort]),
    ):
        write_csv(output / (name + ".csv"), rows)
    np.savez_compressed(output / "coefficient-draws.npz", **arrays)
    plot(summaries, output)
    audit = dict(
        method_version=VERSION,
        execution_policy=POLICY,
        input_snapshot=snapshot_identity(),
        runtime_fingerprint=runtime_fingerprint(raw),
        matching_policy=matching_policy,
        relaxed_edge="all adjacent generations; includes within-generation speed/rate predictor matching",
        bootstrap_replicates=draws,
        seed=seed,
        predictor_weights=METHODS,
        code_hashes=code_hashes(__file__),
        raw_bulk_sha256={g: hashlib.sha256((raw / g / "bulk.csv").read_bytes()).hexdigest() for g in GENERATIONS},
        cpu92_records_sha256=hashlib.sha256(cpu92_records.read_bytes()).hexdigest(),
        output_csv_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob("*.csv")},
        research_csv_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in research.glob("*.csv")},
        primary_validation="newer speed/rate predict distinct older observed rate; no synthetic targets",
        full_chain="local predictor -> older native rate -> existing rate-backbone estimator -> rate-VAXen",
        mask_policy="all methods trained/evaluated on identical complete triplets; single-input models never read hidden input",
        limitations=[
            "CPU95-to-CPU92 alone has direct measured VAXen targets",
            "Later VAXen coefficients remain conditional on the upstream rate chain",
            "Common-case masking does not validate machines structurally missing a benchmark",
            "Run copies/threads and software equivalence unverified",
            "CI95 describes coefficient sampling, not individual prediction intervals",
            "No runtime conversion factor or public timeline overwritten",
        ],
    )
    (research / "audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    return dict(
        summary=str(research / "summary.csv"),
        triplets=len(triples),
        fitted_rows=sum(s["status"] == "conditional_fit" for s in summaries),
        insufficient_rows=sum(s["status"] != "conditional_fit" for s in summaries),
    )


@click.command("fit-joint-tracks")
@click.option("--raw-dir", type=click.Path(path_type=Path), default=Path("data/raw/spec"), show_default=True)
@click.option(
    "--cpu92-records",
    type=click.Path(path_type=Path),
    default=Path("data/derived/spec/cpu92-rate/cpu92-rate-records.csv"),
    show_default=True,
)
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("data/derived/spec/joint-tracks"), show_default=True)
@click.option("--research-dir", type=click.Path(path_type=Path), default=Path("research/data/spec/joint-tracks"), show_default=True)
@click.option("--bootstrap", "draws", type=click.IntRange(min=100), default=10000, show_default=True)
@click.option("--seed", type=int, default=20260929, show_default=True)
@click.option("--matching-policy", type=click.Choice(MATCHING_POLICIES), default="strict", show_default=True)
def fit_joint_tracks(raw_dir, cpu92_records, output_dir, research_dir, draws, seed, matching_policy):
    """Fit speed-only, rate-only and joint predictors against independent older-rate results."""
    try:
        if matching_policy != "strict":
            output_dir, research_dir = output_dir / matching_policy, research_dir / matching_policy
        result = analyze(raw_dir, cpu92_records, output_dir, research_dir, draws, seed, matching_policy)
    except (OSError, KeyError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, sort_keys=True))
