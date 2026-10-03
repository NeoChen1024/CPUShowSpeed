"""Compare saved coefficient families after an input-contract migration."""

import csv
import math
from pathlib import Path

import click
from cpushowspeed.research_io import write_csv


def numeric(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def compare(before, output):
    rows = []
    for old_path in sorted(before.rglob("*.csv")):
        relative = old_path.relative_to(before)
        current = Path(relative)
        if not current.exists():
            continue
        with old_path.open() as f:
            old = list(csv.DictReader(f))
        with current.open() as f:
            new = list(csv.DictReader(f))
        if not old or not new:
            continue
        fields = [
            f
            for f in old[0]
            if f in new[0]
            and (
                f.startswith("coefficient")
                or f
                in (
                    "factor",
                    "factor_old_per_new",
                    "factor_cpu92_per_cpu95",
                    "vaxen_per_rate_score",
                    "vaxen_per_cpu95_rate_score",
                    "factor_to_cpu92",
                    "specint92_equivalent_per_score",
                )
            )
        ]
        if not fields:
            continue
        keys = [
            k
            for k in (
                "scenario",
                "cohort",
                "old_generation",
                "new_generation",
                "generation",
                "mode",
                "metric",
                "method",
                "edge",
                "track",
                "matching_policy",
                "target_metric",
                "target_unit",
                "model",
                "benchmark",
                "variant",
                "target",
                "whetstone",
                "predictor",
                "pattern",
                "stage",
                "scope",
                "comparison",
                "origin",
                "environment",
                "mix",
            )
            if k in old[0] and k in new[0]
        ]

        def index(data):
            result = {}
            for r in data:
                key = tuple(r[k] for k in keys)
                if key in result:
                    return None
                result[key] = r
            return result

        a, b = index(old), index(new)
        if a is None or b is None:
            continue  # Diagnostic observation tables are not coefficient registries.
        for identity in a.keys() | b.keys():
            for field in fields:
                x, y = numeric(a.get(identity, {}).get(field)), numeric(b.get(identity, {}).get(field))
                if x is None and y is None:
                    continue
                changed = x is None or y is None or not math.isclose(x, y, rel_tol=1e-12, abs_tol=0)
                rows.append(
                    dict(
                        table=str(relative),
                        identity=";".join(f"{k}={v}" for k, v in zip(keys, identity)),
                        field=field,
                        before=x,
                        after=y,
                        change_percent=100 * (y / x - 1) if x and y is not None else "",
                        status="changed" if changed else "unchanged",
                    )
                )
    rows.sort(key=lambda r: (r["table"], r["identity"], r["field"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    write_csv(output, rows)
    return dict(coefficients=len(rows), changed=sum(r["status"] == "changed" for r in rows))


@click.command("compare-factors")
@click.option("--before", type=click.Path(path_type=Path), default=Path("data/derived/input-unification/before"), show_default=True)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=Path("data/derived/input-unification/factor-changes.csv"),
    show_default=True,
)
def compare_factors(before, output):
    """Compare coefficient identities without pairing unrelated CSV rows by position."""
    import json

    result = compare(before, output)
    review_models(output, output.parent / "model-review.csv")
    click.echo(json.dumps(result))


def review_models(changes_path, output):
    """Resolve registered output row selectors; never call untested families recomputed."""
    import json

    comparisons = list(csv.DictReader(changes_path.open()))
    models = json.loads(Path("research/model-registry.json").read_text())["models"]
    review = []
    for model in models:
        paths = {o["path"] for o in model.get("outputs", [])}
        selected = []
        for row in comparisons:
            if row["table"] not in paths:
                continue
            identity = dict(part.split("=", 1) for part in row["identity"].split(";") if "=" in part)
            if all(
                identity.get(k) in list(map(str, v if isinstance(v, list) else [v]))
                for k, v in model.get("output_row_selection", {}).items()
            ):
                selected.append(row)
        changes = sum(r["status"] == "changed" for r in selected)
        if model["status"] == "planned":
            decision, reason = "not_implemented", "No implemented coefficient to update."
        elif model["status"] == "defined":
            decision, reason = "definition_unchanged", "Unit/formula definition is unchanged."
        elif changes:
            decision, reason = "updated", "Execution-count exclusion or upstream factor changed; see factor-changes.csv."
        elif selected:
            decision, reason = (
                "numerically_unchanged",
                "Compared table entries unchanged; active families recomputed, legacy snapshots retained.",
            )
        else:
            decision, reason = (
                "no_direct_numeric_comparison",
                "Derived or legacy output outside compared coefficient tables; no automatic rewrite.",
            )
        review.append(
            dict(
                model_id=model["id"],
                decision=decision,
                compared_entries=len(selected),
                changed_entries=changes,
                dependencies=";".join(model.get("depends_on", [])),
                reason=reason,
                owner=model["owner"],
            )
        )
    write_csv(output, review)
