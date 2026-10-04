"""Exploratory instruction-mix/classical fits and SPEC89/SPEC92 overlap audits over resolved systems."""

import json
from collections import defaultdict
from pathlib import Path

import click
from cpushowspeed.calibration import fit
from cpushowspeed.classical_store import CLASSICAL, SCOPES, results
from cpushowspeed.curated import DATABASE
from cpushowspeed.observation_store import connect, inputs_digest
from cpushowspeed.research_io import code_hashes, write_csv

MIX_SCOPE = "mix:longbottom-cpumix"
SPEC89 = ("SPECint89", "SPECmark89", "SPECfp89")
SPEC92 = ("SPECint92", "SPECbase_int92", "SPECfp92", "SPECrate_int92", "SPECrate_base_int92")
SCENARIOS = ("resolved_system", "plus_pending_links")
RESEARCH = Path("research/data/classic/mix-study")


def observation_rows(db, scope):
    """(result_id, system, system_id, metric, value, source_url) for every observation in one scope."""
    query = (
        "SELECT result_id, json_extract(record, '$.system'), system_id, metric_id, value, json_extract(record, '$.source.url') "
        "FROM observation WHERE scope = ? ORDER BY result_id, metric_id"
    )
    return db.execute(query, (scope,)).fetchall()


def pending_links(db):
    """System pairs whose identity a review leaves open; rejected links never pair."""
    links = defaultdict(set)
    for left, right in db.execute(
        "SELECT left_system_ids, right_system_ids FROM review_system_link WHERE decision = 'needs_review'"
    ):
        for a in json.loads(left):
            for b in json.loads(right):
                links[a].add(b)
                links[b].add(a)
    return links


def mix_pairs(mixes, classical, links):
    """Each positive mix rating with each classical score of the same (or a pending-linked) resolved system."""
    by_system = defaultdict(list)
    for r in classical:
        if r.system_id:
            by_system[r.system_id].append(r)
    pairs = []
    for m in mixes:
        if not m["system_id"]:
            continue
        for tier, systems in (("resolved_system", {m["system_id"]}), ("pending_link", links.get(m["system_id"], set()))):
            for system_id in sorted(systems):
                for c in by_system.get(system_id, []):
                    for metric, value in sorted(c.classical.items()):
                        pairs.append(
                            dict(
                                mix_id=m["result_id"],
                                mix=m["mix"],
                                mix_system=m["system"],
                                mix_system_id=m["system_id"],
                                mix_kips=m["kips"],
                                classical_result_id=c.result_id,
                                classical_system=c.system,
                                classical_system_id=c.system_id,
                                metric=metric,
                                classical_score=value,
                                candidate_tier=tier,
                                mix_source_url=m["source_url"],
                                classical_source_url=c.source_url,
                                source_lineage_relation=(
                                    "same_Longbottom_compilation"
                                    if "roylongbottom" in c.source_url
                                    else "different_archive_independence_unestablished"
                                ),
                                review_status="pending_configuration_review",
                            )
                        )
    return pairs


def overlap(mixes, db, scope, metrics, kind):
    """Mix ratings and SPEC values of one resolved system; an audit, not fitting pairs."""
    pairs, coverage = [], []
    values = defaultdict(list)
    for result_id, system, system_id, metric, value, url in observation_rows(db, scope) if isinstance(scope, str) else scope:
        metric = {"cpu92:integer:speed:peak": "SPECint92", "cpu92:integer:speed:base": "SPECbase_int92"}.get(metric, metric)
        metric = {"cpu92:integer:rate:peak": "SPECrate_int92", "cpu92:integer:rate:base": "SPECrate_base_int92"}.get(metric, metric)
        if metric in metrics and system_id:
            values[system_id].append(dict(spec_id=result_id, spec_system=system, metric=metric, score=value, source_url=url))
    for m in mixes:
        matched = values.get(m["system_id"], []) if m["system_id"] else []
        coverage.append(
            dict(
                mix_id=m["result_id"],
                mix=m["mix"],
                system=m["system"],
                system_id=m["system_id"],
                kind=kind,
                spec_values=len(matched),
            )
        )
        pairs.extend(dict(mix_id=m["result_id"], mix_system=m["system"], **v, fit_eligible=False) for v in matched)
    target_coverage = [
        dict(
            metric=metric,
            spec_values=sum(v["metric"] == metric for vs in values.values() for v in vs),
            systems=sum(any(v["metric"] == metric for v in vs) for vs in values.values()),
            mix_pairs=sum(p["metric"] == metric for p in pairs),
            mix_systems=len({p["mix_system"] for p in pairs if p["metric"] == metric}),
        )
        for metric in metrics
    ]
    return pairs, coverage, target_coverage


@click.command("fit-classical")
@click.option("--database", type=click.Path(path_type=Path, dir_okay=False), default=DATABASE, show_default=True)
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("data/derived/classic/mix-bridge"), show_default=True)
@click.option("--research-dir", type=click.Path(path_type=Path), default=RESEARCH, show_default=True)
@click.option("--bootstrap", type=click.IntRange(min=100), default=2000, show_default=True)
@click.option("--seed", type=int, default=20260928, show_default=True)
def mix_bridge(database, output_dir, research_dir, bootstrap, seed):
    """Fit exploratory mix/classical cohorts over resolved systems; audit SPEC89/SPEC92 overlap without fitting it."""
    with connect(database) as db:
        mixes = [
            dict(
                result_id=rid,
                system=system,
                system_id=system_id or "",
                mix=metric.removeprefix("InstructionMix:").removesuffix("_KIPS"),
                kips=value,
                source_url=url,
            )
            for rid, system, system_id, metric, value, url in observation_rows(db, MIX_SCOPE)
        ]
        classical = [r for r in results(db, SCOPES) if r.classical and set(r.classical) <= set(CLASSICAL)]
        links = pending_links(db)
        spec89_pairs, spec89_coverage, spec89_targets = overlap(mixes, db, "historical-spec:spec89", SPEC89, "spec89")
        spec92_rows = [
            row
            for scope in ("spec:cpu92", "historical-spec:spec92-dec", "reviewed-vector:dec-n3909-1994")
            for row in observation_rows(db, scope)
        ]
        spec92_pairs, spec92_coverage, spec92_targets = overlap(mixes, db, spec92_rows, SPEC92, "spec92")
        digest = inputs_digest(db)
    pairs = mix_pairs(mixes, classical, links)
    summaries = []
    for mix, metric in sorted({(p["mix"], p["metric"]) for p in pairs}):
        for scenario in SCENARIOS:
            selected = [
                p
                for p in pairs
                if p["mix"] == mix
                and p["metric"] == metric
                and (scenario == "plus_pending_links" or p["candidate_tier"] == "resolved_system")
            ]
            # fit() names its target y_vaxen; here it holds the classical score, and the factor is classical score per mix KIPS.
            sample = [dict(model_key=p["classical_system_id"], x=p["mix_kips"], y_vaxen=p["classical_score"]) for p in selected]
            summaries.append(
                dict(
                    mix=mix,
                    target_metric=metric,
                    scenario=scenario,
                    x_unit="mix_KIPS",
                    factor_unit=metric + "/mix_KIPS",
                    **fit(sample, bootstrap, seed),
                )
            )
    coverage = [
        dict(
            mix=mix,
            metric=metric,
            candidate_pairs=len(sub),
            mix_rows=len({p["mix_id"] for p in sub}),
            classical_results=len({p["classical_result_id"] for p in sub}),
            classical_systems=len({p["classical_system_id"] for p in sub}),
            pending_link_pairs=sum(p["candidate_tier"] == "pending_link" for p in sub),
        )
        for mix, metric in sorted({(p["mix"], p["metric"]) for p in pairs})
        for sub in [[p for p in pairs if p["mix"] == mix and p["metric"] == metric]]
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    research_dir.mkdir(parents=True, exist_ok=True)
    for name, data in [
        ("classical-candidate-pairs", pairs),
        ("classical-fit-summary", summaries),
        ("classical-coverage", coverage),
        ("spec89-candidate-pairs", spec89_pairs),
        ("spec89-coverage", spec89_coverage),
        ("spec89-target-coverage", spec89_targets),
        ("spec92-candidate-pairs", spec92_pairs),
        ("spec92-coverage", spec92_coverage),
        ("spec92-target-coverage", spec92_targets),
    ]:
        write_csv(output_dir / (name + ".csv"), data)
    for name, data in [
        ("bridge-classical-fit-summary", summaries),
        ("bridge-classical-coverage", coverage),
        ("bridge-spec89-target-coverage", spec89_targets),
        ("bridge-spec92-target-coverage", spec92_targets),
    ]:
        write_csv(research_dir / (name + ".csv"), data)
    audit = dict(
        method="mix-bridge-v3-resolved-systems",
        mix_listings=len(mixes),
        positive_mix_listings=sum(bool(m["kips"]) for m in mixes),
        mix_systems=len({m["system_id"] for m in mixes if m["system_id"]}),
        classical_candidate_pairs=len(pairs),
        pending_link_pairs=sum(p["candidate_tier"] == "pending_link" for p in pairs),
        spec89_pairs=len(spec89_pairs),
        spec92_pairs=len(spec92_pairs),
        approved_pairs=0,
        direct_fitted_models=0,
        bootstrap=bootstrap,
        seed=seed,
        pairing="same resolved system_id; plus_pending_links adds system links a review leaves open (needs_review); rejected links never pair",
        weighting="Median log ratio per classical system; geometric mean across systems.",
        uncertainty="Conditional system bootstrap CI95; not configuration-validation uncertainty or chained VAXen CI.",
        inputs_sha256=digest,
        shared_code_sha256=code_hashes(Path(__file__)),
        notes=[
            "SPEC89 metrics kept separate; no SPECmark-to-int substitution.",
            "SPEC overlaps are audits, not fitting pairs.",
            "Classical values are original scores, not predicted VAXen.",
            "Curated vendor and SC-3 Gibson cells are not in the database yet and do not enter this command.",
        ],
    )
    for path in (output_dir / "audit.json", research_dir / "bridge-audit.json"):
        path.write_text(json.dumps(audit, indent=2) + "\n")
    click.echo(json.dumps({k: v for k, v in audit.items() if k not in ("inputs_sha256", "shared_code_sha256", "notes")}))
