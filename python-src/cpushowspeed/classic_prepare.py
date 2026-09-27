"""Data preparation independent of historical fitting/plotting commands."""

import hashlib
import json
from pathlib import Path

import click
from cpushowspeed.classic_pair_data import build
from cpushowspeed.classic_source_data import prepare, source_vectors
from cpushowspeed.research_io import code_hashes, read_csv, write_csv


def audit(output, paths, **counts):
    result = dict(
        method="classical-preparation-v2",
        **counts,
        input_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        shared_code_sha256=code_hashes(Path(__file__)),
    )
    (output / "prepare-audit.json").write_text(json.dumps(result, indent=2) + "\n")
    click.echo(json.dumps(dict(output=str(output), **counts)))


@click.command("prepare-pairs")
@click.option(
    "--input-root",
    type=click.Path(path_type=Path, exists=True),
    default=Path("data/derived/classic/overlap-spec"),
    show_default=True,
)
@click.option(
    "--linpack-text",
    type=click.Path(path_type=Path, exists=True),
    default=Path("data/derived/classic/netlib-linpack-report.txt"),
    show_default=True,
)
@click.option("--output", type=click.Path(path_type=Path), default=Path("data/derived/classic/pair-fit"), show_default=True)
def prepare_pairs(input_root, linpack_text, output):
    """Prepare classical candidate pair inputs without fitting or figures."""
    paths = [input_root / n for n in ("classical-records.jsonl", "spec-records.jsonl", "candidate-pairs.csv")]
    classical, specs = [{r["id"]: r for r in map(json.loads, p.read_text().splitlines())} for p in paths[:2]]
    rows = build(classical, specs, read_csv(paths[2]), linpack_text.read_text().split("\f"))
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "pairs.csv", rows)
    audit(output, paths + [linpack_text], rows=len(rows))


@click.command("prepare-sources")
@click.option(
    "--pdf-root",
    type=click.Path(path_type=Path, exists=True),
    default=Path("research/data/classic/pdf-extraction"),
    show_default=True,
)
@click.option(
    "--legacy-pairs",
    type=click.Path(path_type=Path, exists=True),
    default=Path("data/derived/classic/pair-fit/pairs.csv"),
    show_default=True,
)
@click.option(
    "--spec-records",
    type=click.Path(path_type=Path, exists=True),
    default=Path("data/derived/classic/overlap-spec/spec-records.jsonl"),
    show_default=True,
)
@click.option("--output", type=click.Path(path_type=Path), default=Path("data/derived/classic/source-pair-fit"), show_default=True)
def prepare_sources(pdf_root, legacy_pairs, spec_records, output):
    """Prepare reviewed source vectors and staged pairs without regressions."""
    paths = [pdf_root / n for n in ("tables.jsonl", "dec-interpreted.csv", "interpretation-policy.json")] + [
        legacy_pairs,
        spec_records,
    ]
    vectors, units = source_vectors(list(map(json.loads, paths[0].read_text().splitlines())), read_csv(paths[1]))
    rows, matching = prepare(vectors, read_csv(legacy_pairs), list(map(json.loads, spec_records.read_text().splitlines())))
    output.mkdir(parents=True, exist_ok=True)
    (output / "vectors.jsonl").write_text("".join(json.dumps(v) + "\n" for v in vectors))
    for name, records in [("pairs", rows), ("unit-review", units), ("matching-review", matching)]:
        write_csv(output / (name + ".csv"), records)
    audit(output, paths, vectors=len(vectors), pairs=len(rows))
