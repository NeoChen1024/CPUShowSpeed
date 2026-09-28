"""Exploratory mix/classical fits and a direct SPEC89/SPEC92 feasibility inventory."""

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import click
from bs4 import BeautifulSoup
from cpushowspeed.calibration import fit
from cpushowspeed.classic_overlap import model_key
from cpushowspeed.classic_values import numeric
from cpushowspeed.research_io import code_hashes, read_csv, write_csv

MIX = Path("data/derived/classic/mix-study")
CURATED = Path("research/data/classic/mix-study")
SPEC = Path("data/derived/classic/overlap-spec/spec-records.jsonl")


def audit_spec92(mixes, output_dir):
    records, inputs, missing = [], [SPEC], []
    for line in SPEC.read_text().splitlines():
        r = json.loads(line)
        if r["cohort"].startswith("SPEC92"):
            for metric, value in r["metrics_raw"].items():
                if numeric(value) and numeric(value) > 0:
                    records.append(
                        dict(
                            source_kind="rate_archive",
                            source_id=r["id"],
                            system=r["system"],
                            metric=metric,
                            score=numeric(value),
                            source_url=r["source_url"],
                        )
                    )
    for p in sorted(Path("data/raw/spec/cpu92/netlib").glob("*.col0.html")):
        match = re.fullmatch(r"(spec|specbase)\.(cint92|cfp92)\..+\.col0\.html", p.name)
        if not match:
            continue
        inputs.append(p)
        metric = ("SPECbase_" if match[1] == "specbase" else "SPEC") + ("int92" if match[2] == "cint92" else "fp92")
        soup = BeautifulSoup(p.read_text(), "html.parser")
        for i, a in enumerate(soup.select("pre a[href]")):
            if ".notes.html" not in a["href"]:
                continue
            tail = str(a.next_sibling or "").strip().split()
            score = numeric(tail[0]) if tail else None
            if tail and tail[0] == "-":
                missing.append(
                    dict(source_path=str(p), system=a.get_text(" ", strip=True), metric=metric, raw_score="-", source_url=a["href"])
                )
                continue
            if score is None or score <= 0:
                raise ValueError("Unparsed SPEC92 summary row: " + str(p) + " " + a.get_text())
            records.append(
                dict(
                    source_kind="netlib_speed_summary",
                    source_id=f"{p.name}:link:{i}",
                    system=a.get_text(" ", strip=True),
                    metric=metric,
                    score=score,
                    source_url=a["href"],
                )
            )
    vectors = Path("data/derived/classic/source-pair-fit/vectors.jsonl")
    inputs.append(vectors)
    for l in vectors.read_text().splitlines():
        r = json.loads(l)
        for metric, value in r["targets"].items():
            if metric in ["SPECint92", "SPECbase_int92", "SPECfp92", "SPECbase_fp92"] and value > 0:
                records.append(
                    dict(
                        source_kind="curated_source_vector",
                        source_id=r["id"],
                        system=r["machine"],
                        metric=metric,
                        score=value,
                        source_url=r.get("source_url", ""),
                        observation_id=r["observation_ids"].get(metric, ""),
                    )
                )
    pairs = []
    for m in mixes:
        for r in records:
            if m["value"] and model_key(m["system"]) == model_key(r["system"]):
                pairs.append(dict(mix_id=m["id"], mix_system=m["system"], **r, fit_eligible=False))
    write_csv(output_dir / "spec92-source-scores.csv", records)
    write_csv(output_dir / "spec92-missing-scores.csv", missing)
    (output_dir / "spec92-candidate-pairs.jsonl").write_text("".join(json.dumps(p) + "\n" for p in pairs))
    coverage = []
    for source, metric in sorted({(r["source_kind"], r["metric"]) for r in records}):
        sub = [r for r in records if r["source_kind"] == source and r["metric"] == metric]
        coverage.append(
            dict(
                source_kind=source,
                metric=metric,
                positive_score_cells=len(sub),
                system_labels=len({r["system"] for r in sub}),
                candidate_pairs=sum(p["source_kind"] == source and p["metric"] == metric for p in pairs),
            )
        )
    write_csv(output_dir / "spec92-target-coverage.csv", coverage)
    return dict(
        score_cells=len(records),
        missing_score_cells=len(missing),
        candidate_pairs=len(pairs),
        fitted_models=0,
        notes="Repeated summary snapshots retained; score cells are not independent submissions. Speed and rate metrics remain separate.",
        input_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
    )


@click.command("mix-bridge")
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("data/derived/classic/mix-bridge"), show_default=True)
@click.option("--bootstrap", type=click.IntRange(min=100), default=2000, show_default=True)
@click.option("--seed", type=int, default=20260928, show_default=True)
def mix_bridge(output_dir, bootstrap, seed):
    """Fit unapproved classical candidate cohorts; audit direct SPEC89/SPEC92 overlap without inventing matches."""
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        paths = [
            MIX / "mix-records.csv",
            MIX / "candidate-pairs.csv",
            MIX / "audit.json",
            CURATED / "additional-observations.csv",
            CURATED / "sc3-observations.csv",
            SPEC,
        ]
        inventory_audit = json.loads((MIX / "audit.json").read_text())
        for p, digest in inventory_audit["input_sha256"].items():
            if hashlib.sha256(Path(p).read_bytes()).hexdigest() != digest:
                raise ValueError("Stale mix inventory; rerun classic mix-inventory: " + p)
        specs = [json.loads(l) for l in SPEC.read_text().splitlines() if json.loads(l)["id"].startswith("spec89:")]
        source_mixes = read_csv(paths[0])
        mixes = [
            dict(
                id=r["mix_id"],
                system=r["system"],
                metric=r["mix"],
                value=numeric(r["kips"]),
                unit="KIPS",
                source_url=r["source_url"],
            )
            for r in source_mixes
        ]
        for r in read_csv(paths[3]):
            if r["metric"].startswith("gibson"):
                mixes.append(
                    dict(
                        id=r["record_id"],
                        system=r["machine"],
                        metric=r["metric"],
                        value=numeric(r["reported_value"]),
                        unit=r["reported_unit"],
                        source_url=r["source_url"],
                    )
                )
        for r in read_csv(paths[4]):
            if r["metric"] == "qualified_gibson":
                mixes.append(
                    dict(
                        id=r["record_id"],
                        system=r["machine"],
                        metric=r["metric"],
                        value=numeric(r["reported_value"]),
                        unit=r["reported_unit"],
                        source_url=r["source_url"],
                    )
                )
        overlaps, coverage = [], []
        for m in mixes:
            matching = [s for s in specs if model_key(m["system"]) and model_key(m["system"]) == model_key(s["system"])]
            coverage.append(
                dict(
                    **m,
                    normalized_model=model_key(m["system"]),
                    name_matched_spec_records=len(matching),
                    status="candidate_only" if matching else "no_model_overlap",
                )
            )
            for s in matching:
                for target in ["SPECint89", "SPECmark89", "SPECfp89"]:
                    y = numeric(s["metrics_raw"].get(target))
                    if m["value"] and y:
                        overlaps.append(
                            dict(
                                mix_id=m["id"],
                                spec_id=s["id"],
                                mix_system=m["system"],
                                spec_system=s["system"],
                                target_metric=target,
                                target_score=y,
                                fit_eligible=False,
                            )
                        )
        (output_dir / "spec89-candidate-pairs.jsonl").write_text("".join(json.dumps(r) + "\n" for r in overlaps))
        write_csv(output_dir / "spec89-coverage.csv", coverage)
        target_coverage = []
        for metric in ["SPECint89", "SPECmark89", "SPECfp89"]:
            sub = [s for s in specs if numeric(s["metrics_raw"].get(metric)) and numeric(s["metrics_raw"].get(metric)) > 0]
            target_coverage.append(
                dict(
                    metric=metric,
                    positive_records=len(sub),
                    source_system_labels=len({s["system"] for s in sub}),
                    reference_definition_records=sum(
                        s["raw_record"].get("measurement_type") == "reference_definition" for s in sub
                    ),
                    candidate_pairs=sum(p["target_metric"] == metric for p in overlaps),
                )
            )
        write_csv(output_dir / "spec89-target-coverage.csv", target_coverage)
        # A CPU-family lead is preserved separately, never silently admitted as a model match.
        leads = []
        for s in specs:
            if s["system"] == "i386/387":
                leads.append(
                    dict(
                        mix_id="sc3-gibson-SC-3",
                        mix_clock_mhz=16,
                        spec_id=s["id"],
                        spec_system=s["system"],
                        spec_clock_mhz=s["clock_mhz"],
                        spec_scores=json.dumps(s["metrics_raw"]),
                        fit_eligible=False,
                        reason="CPU-family lead only; different machine and clock; SC-3 Gibson uses 16-bit memory; SPEC cache/configuration differ or unspecified; SPECmark89 is not SPECint89.",
                        spec_source_url=s["source_url"],
                    )
                )
        write_csv(output_dir / "spec89-family-leads.csv", leads)
        pairs = read_csv(paths[1])
        summaries = []
        for mix, metric in sorted({(p["mix"], p["metric"]) for p in pairs}):
            for scenario in ["literal_names_only", "all_candidate_aliases"]:
                selected = [
                    p
                    for p in pairs
                    if p["mix"] == mix
                    and p["metric"] == metric
                    and (scenario == "all_candidate_aliases" or p["candidate_tier"] == "literal_name")
                ]
                # Shared helper's historical y_vaxen argument holds the actual classical score here.
                # Exported units are explicit: these factors are NOT VAXen coefficients.
                sample = [
                    dict(model_key=model_key(p["classical_system"]), x=float(p["mix_kips"]), y_vaxen=float(p["classical_score"]))
                    for p in selected
                ]
                result = fit(sample, bootstrap, seed)
                summaries.append(
                    dict(
                        mix=mix,
                        target_metric=metric,
                        scenario=scenario,
                        x_unit="mix_KIPS",
                        factor_unit=metric + "/mix_KIPS",
                        approved_pairs=0,
                        **result,
                    )
                )
        write_csv(output_dir / "classical-fit-summary.csv", summaries)
        write_csv(output_dir / "classical-candidate-pairs.csv", pairs)
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axs = plt.subplots(2, 3, figsize=(17, 10))
        for ax, (mix, metric) in zip(axs.flat, sorted({(p["mix"], p["metric"]) for p in pairs})):
            group = [p for p in pairs if p["mix"] == mix and p["metric"] == metric]
            ax.scatter([float(p["mix_kips"]) for p in group], [float(p["classical_score"]) for p in group], s=25, alpha=0.6)
            for scenario, color in [("literal_names_only", "#dd8822"), ("all_candidate_aliases", "#17628a")]:
                r = next(s for s in summaries if s["mix"] == mix and s["target_metric"] == metric and s["scenario"] == scenario)
                if "factor" in r:
                    x = [min(float(p["mix_kips"]) for p in group) * 0.8, max(float(p["mix_kips"]) for p in group) * 1.2]
                    ax.plot(x, [v * r["factor"] for v in x], color=color, label=f'{scenario}: {r["models"]} models')
                    ax.fill_between(
                        x, [v * r["factor_ci95_low"] for v in x], [v * r["factor_ci95_high"] for v in x], alpha=0.1, color=color
                    )
            ax.set(xscale="log", yscale="log", xlabel=mix + " KIPS", ylabel=metric)
            ax.grid(alpha=0.2)
            ax.legend(fontsize=7)
        axs.flat[-1].axis("off")
        fig.suptitle("Exploratory unapproved configuration matches — y = kx; conditional coefficient CI95")
        fig.tight_layout()
        for ext in ["png", "svg"]:
            fig.savefig(output_dir / f"classical-mix-scatter.{ext}", dpi=150)
        plt.close(fig)
        spec92 = audit_spec92(mixes, output_dir)
        audit = dict(
            method="mix-bridge-feasibility-v2",
            spec92=spec92,
            spec89_records=len(specs),
            spec89_system_labels=len({s["system"] for s in specs}),
            mix_listings=len(mixes),
            positive_mix_listings=sum(bool(m["value"]) for m in mixes),
            direct_name_pairs=len(overlaps),
            direct_fitted_models=0,
            approved_pairs=0,
            classical_candidate_pairs=len(pairs),
            bootstrap=bootstrap,
            seed=seed,
            weighting="Median log ratio per normalized classical model; geometric mean across models; all existing candidate rows retained.",
            uncertainty="Conditional model bootstrap CI95; not configuration-validation uncertainty or chained VAXen CI.",
            input_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
            code_sha256=code_hashes(__file__),
            notes=[
                "SPEC89 metrics kept separate; no SPECmark-to-int substitution.",
                "CPU-family leads are not fitting pairs.",
                "Classical values are original score aggregates, not predicted VAXen.",
                "All fits are conditional on unreviewed configuration matches. No production calibration updated.",
            ],
        )
        (output_dir / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
        click.echo(json.dumps({k: v for k, v in audit.items() if k not in ["input_sha256", "code_sha256", "notes"]}))
    except (OSError, ValueError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc
