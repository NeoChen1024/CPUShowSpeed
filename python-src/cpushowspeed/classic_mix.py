"""Instruction-mix source inventory and classical bridge candidates, not fitted estimates."""

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import click
from blake3 import blake3
from bs4 import BeautifulSoup
from cpushowspeed.classic_overlap import model_key
from cpushowspeed.classic_values import numeric
from cpushowspeed.research_io import code_hashes, read_csv, write_csv

RECORDS = Path("data/derived/classic/overlap-spec/classical-records.jsonl")
SOURCE = Path("data/derived/classic/longbottom-cpumix-84dcf58a736b.json")
HISTORICAL = Path("data/derived/classic/historical-timeline/configurations.csv")
SNAPSHOT = Path("data/raw/classic/blobs/84/84dcf58a736be9fe1622801cbae47b984ae15915507f6b2108a5c29250180173")
ALIASES = Path("research/data/classic/mix-candidate-aliases.csv")


def weights(source):
    """Extract the two explicit operation-weight tables, excluding layout tables."""
    soup = BeautifulSoup(source["blocks"][0]["html"], "html.parser")
    result = []
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr", recursive=False):
            cells = tr.find_all(["td", "th"], recursive=False)
            if len(cells) == 2:
                text = [x.get_text(" ", strip=True) for x in cells]
                weight = numeric(text[1])
                if weight is not None:
                    rows.append((text[0], weight))
        if rows:
            result.append(rows)
    if len(result) != 2 or [len(t) for t in result] != [12, 7]:
        raise ValueError("Instruction-mix weight table layout changed")
    for table in result:
        if not math.isclose(sum(w for _, w in table), 1, abs_tol=1e-12):
            raise ValueError("Instruction weights do not sum to one")
    return [
        dict(
            mix=mix,
            operation=op,
            weight=w,
            source_url="http://www.roylongbottom.org.uk/cpumix.htm",
            source_locator=f"Operation-weight table {i+1}",
            variant="CCTA/TSU variation reproduced by Longbottom",
        )
        for i, (mix, table) in enumerate(zip(["Gibson Mix", "ADP Mix"], result))
        for op, w in table
    ]


@click.command("mix-inventory")
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("data/derived/classic/mix-study"), show_default=True)
def mix_inventory(output_dir):
    """Inventory Gibson/ADP scores, definitions and unapproved classical overlap candidates."""
    records = [json.loads(s) for s in RECORDS.read_text().splitlines()]
    mixes = [r for r in records if r["benchmark"] in ("Gibson Mix", "ADP Mix")]
    original = json.loads(SOURCE.read_text())
    definitions = weights(original)
    raw_bytes = SNAPSHOT.read_bytes()
    raw_sha = hashlib.sha256(raw_bytes).hexdigest()
    if blake3(raw_bytes).hexdigest() != SNAPSHOT.name:
        raise ValueError("source snapshot BLAKE3 mismatch")
    soup = BeautifulSoup(raw_bytes, "html.parser")
    raw_rows = []
    for tr in soup.find_all("tr"):
        cells = tr.find_all(["td", "th"], recursive=False)
        if len(cells) == 8 and not any(c.find("table") for c in cells):
            v = tuple(c.get_text(" ", strip=True) for c in cells)
            if v[0] and v[1] and v[0] != "Manufacturer":
                raw_rows.append(v)
    for mix in ("Gibson Mix", "ADP Mix"):
        if Counter(raw_rows) != Counter(tuple(r["raw_record"]) for r in mixes if r["benchmark"] == mix):
            raise ValueError("parsed mix records differ from original HTML rows")
    source_rows = []
    for r in mixes:
        raw = r["raw_record"]
        score = numeric(r["metrics_raw"]["KIPS"])
        source_rows.append(
            dict(
                mix_id=r["id"],
                mix=r["benchmark"],
                system=r["system"],
                kips=score,
                raw_score=r["metrics_raw"]["KIPS"],
                word_bits=raw[2],
                memory_capacity_raw=raw[3],
                memory_cycle_us_raw=raw[4],
                introduction_year_raw=raw[7],
                source_url=r["source_url"],
                source_locator=r["locator"],
                source_snapshot_sha256=raw_sha,
                mix_variant="CCTA/TSU variation reproduced by Longbottom",
                architecture_factor="unknown_per_row",
                evidence_kind="instruction_mix_estimate",
                verification=r["verification"],
                fit_eligible=False,
            )
        )
    classical = [r for r in read_csv(HISTORICAL) if r["route"] == "classical"]
    aliases = read_csv(ALIASES)
    pairs = []
    for m in source_rows:
        if not m["kips"]:
            continue
        for c in classical:
            tier = ""
            if m["system"].casefold() == c["system"].casefold():
                tier = "literal_name"
            elif model_key(m["system"]) == model_key(c["system"]):
                tier = "normalized_model"
            reasons = []
            for a in aliases:
                if re.fullmatch(a["mix_regex"], m["system"], re.I) and re.fullmatch(a["classical_regex"], c["system"], re.I):
                    tier = tier or "explicit_candidate_alias"
                    reasons.append(a["reason"])
            if not tier:
                continue
            scores = json.loads(c["scores"])
            for metric, value in scores.items():
                pairs.append(
                    dict(
                        mix_id=m["mix_id"],
                        mix=m["mix"],
                        mix_system=m["system"],
                        mix_kips=m["kips"],
                        classical_configuration_id=c["configuration_id"],
                        classical_system=c["system"],
                        metric=metric,
                        classical_score=value,
                        observation_count=c["observation_count"],
                        candidate_tier=tier,
                        mix_memory_cycle_us_raw=m["memory_cycle_us_raw"],
                        classical_configuration=c["configuration"],
                        mix_source_url=m["source_url"],
                        mix_locator=m["source_locator"],
                        classical_source_url=c["source_url"],
                        source_lineage_relation=(
                            "same_Longbottom_compilation"
                            if "roylongbottom" in c["source_url"]
                            else "different_archive_independence_unestablished"
                        ),
                        review_status="pending_configuration_review",
                        fit_eligible=False,
                        review_reason="; ".join(reasons)
                        or "Name overlap only; options, memory timing and workload semantics require review.",
                    )
                )
    summaries = []
    for mix in ("Gibson Mix", "ADP Mix"):
        ms = [r for r in source_rows if r["mix"] == mix]
        ps = [r for r in pairs if r["mix"] == mix]
        for metric in sorted({p["metric"] for p in ps}):
            sub = [p for p in ps if p["metric"] == metric]
            summaries.append(
                dict(
                    mix=mix,
                    metric=metric,
                    candidate_pairs=len(sub),
                    mix_rows=len({r["mix_id"] for r in sub}),
                    classical_configurations=len({r["classical_configuration_id"] for r in sub}),
                    model_keys=len({model_key(r["classical_system"]) for r in sub}),
                    approved_pairs=0,
                )
            )
    audit = dict(
        method_version="instruction-mix-inventory-v1",
        source_rows=len(source_rows),
        scores={
            mix: dict(
                total=sum(r["mix"] == mix for r in source_rows),
                positive=sum(r["mix"] == mix and bool(r["kips"]) for r in source_rows),
            )
            for mix in ("Gibson Mix", "ADP Mix")
        },
        candidate_pairs=len(pairs),
        classical_configurations=len({r["classical_configuration_id"] for r in pairs}),
        approved_pairs=0,
        fitted_models=0,
        weights_sum={mix: sum(r["weight"] for r in definitions if r["mix"] == mix) for mix in ("Gibson Mix", "ADP Mix")},
        input_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [RECORDS, SOURCE, SNAPSHOT, HISTORICAL, ALIASES]},
        code_sha256=code_hashes(__file__),
        notes=[
            "Missing-score listings retained; no VAXen targets synthesized.",
            "Model normalization can drop EAE/EAU/FPU flags: every pairing is unapproved.",
            "Positive numeric cells are transcriptions of calculated ratings, not executed benchmark observations.",
        ],
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "mix-records.csv", source_rows)
    write_csv(output_dir / "mix-weights.csv", definitions)
    write_csv(output_dir / "candidate-pairs.csv", pairs)
    write_csv(output_dir / "coverage.csv", summaries)
    (output_dir / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    click.echo(json.dumps({k: v for k, v in audit.items() if k not in ("input_sha256", "code_sha256")}))
