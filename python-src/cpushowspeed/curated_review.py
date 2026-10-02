"""Reviews (schema step 4): judgements that qualify extracted evidence without editing it.

A review targets one reported date of a result (`result_date`), two results treated as
one configuration (`result_pair`) or two source system texts that may denote one
machine (`system_link`). Targets are selectors resolved at build time against the
extracted result records and hardware records; a selector that matches nothing is
reported, never dropped silently. Rejected result dates leave the chronology
candidates (also as model-level dates for other results) but stay in the extracted
records. Aliases and date events carry their own status and need no review row.
"""

import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from contextlib import closing
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import click
from cpushowspeed.cpu_chronology import sku_key
from cpushowspeed.curated import CURATED, DATABASE, read_table, validate, write_jsonl
from cpushowspeed.curated_dates import RESULTS, new_source, short_hash, source_finder
from cpushowspeed.curated_identity import slug
from cpushowspeed.curated_sources import norm_url
from cpushowspeed.research_io import read_csv

DATE_EXCLUSIONS = Path("research/data/spec/hardware-date-exclusions.csv")
OVERRIDES = Path("research/data/historical/timeline-year-overrides.csv")
PAIRS = Path("research/cpu92-cpu95-reviewed.csv")
MIX_CANDIDATES = Path("research/data/classic/mix-candidate-aliases.csv")
# The candidate file has no review date; it was committed (031f8e4) on this day.
MIX_CANDIDATES_ADDED = "2026-09-28"


def result_key(url):
    """The source-local part of a SPEC result ID: 'res9509/p026' or a Netlib detail file name."""
    path = urlsplit(url).path
    if "/results/" in path:
        return path.split("/results/", 1)[1].removesuffix(".html")
    return path.rsplit("/", 1)[-1]


def spec_result(results, url, track=None):
    key = result_key(url)
    found = [r for r in results if r.startswith("spec:") and r.split(":", 3)[3] == key and (track is None or f":{track}:" in r)]
    if len(found) != 1:
        raise ValueError(f"{url}: expected one result, found {found}")
    return found[0]


def seed_reviews(tables, db):
    """Convert hardware-date exclusions (and their launch dates), rejected table years, reviewed CPU92–CPU95 pairs and mix candidates."""
    today = date.today().isoformat()
    sources = list(tables["source"])
    _, by_url = source_finder(sources)
    results = [json.loads(line)["result_id"] for line in RESULTS.read_text().splitlines()]
    records = [json.loads(line) for line in RESULTS.read_text().splitlines()]
    skus, events = list(tables["processor_sku"]), [e for e in tables["date_event"] if not e["event_id"].startswith("evt:review/")]
    reviews, report = [], Counter()

    def source_for(url, legacy):
        sid = by_url.get(norm_url(url))
        if sid:
            row = next(s for s in sources if s["source_id"] == sid)
            if legacy not in row["legacy_ids"]:
                row["legacy_ids"] = sorted(row["legacy_ids"] + [legacy])
            return sid
        row = new_source(url, legacy, today)
        sources.append(row)
        by_url[norm_url(url)] = row["source_id"]
        return row["source_id"]

    # 1. A SPEC hardware-availability date contradicted by the processor's launch date.
    for r in read_csv(DATE_EXCLUSIONS):
        legacy = "spec/hardware-date-exclusions:" + r["source_url"]
        rid = spec_result(results, r["source_url"])
        reviews.append(
            dict(
                review_id=f"rev:hardware-date-exclusions/{slug(result_key(r['source_url']))}",
                target_kind="result_date",
                target=dict(result_id=rid),
                field="hardware_availability",
                decision="reject",
                reason=f"{r['decision']}: {r['reason']} (reported {r['hardware_avail_raw']}; {r['processor']} launched {r['conflict_date']})",
                source_id=source_for(r["conflict_source_url"], legacy),
                reviewed_on=r["reviewed_on"],
                legacy_ids=[legacy],
            )
        )
        report["result_date"] += 1
        # The conflicting launch date is itself release evidence for that SKU.
        key = sku_key(r["processor"])
        sku_id = "sku:" + slug(key)
        if not any(f"sku-key-v1:{key}" in s["keys"] for s in skus):
            vendor, model = r["processor"].split(" ", 1)
            clock = next(x["clock_mhz"] for x in records if x["result_id"] == rid)
            skus.append(
                dict(
                    sku_id=sku_id,
                    family_id=f"fam:{slug(vendor)}-{slug(model.split()[0])}",
                    vendor=vendor,
                    model=model,
                    keys=[f"sku-key-v1:{key}"],
                    base_clocks_mhz=[clock],
                    source_ids=[source_for(r["conflict_source_url"], legacy)],
                )
            )
            report["processor_sku"] += 1
        events.append(
            dict(
                event_id=f"evt:review/{sku_id.removeprefix('sku:')}",
                subject_kind="processor_sku",
                subject_id=sku_id,
                event_type="release",
                date=r["conflict_date"],
                date_precision="day",
                claim_status="reported",
                chronology="primary",
                source_id=source_for(r["conflict_source_url"], legacy),
                verification="web_text_checked",
                reviewed_on=r["reviewed_on"],
                note=f"Launch date stated by the vendor page, recorded when the {r['generation']} hardware date was reviewed.",
                legacy_ids=[legacy + "#conflict_date"],
            )
        )
        report["date_event"] += 1
    # 2. Compilation-table years the year overrides rejected ("Reject source table 1963").
    for r in read_csv(OVERRIDES):
        if not (re.search(r"\breject (?:source )?table\b", r["notes"], re.I) or r["method"] == "conflicting_source_year"):
            continue
        legacy = "historical/timeline-year-overrides:" + r["system_regex"]
        hits = sorted({(x["scope"], x["system"]) for x in records if x["table_year"] and re.search(r["system_regex"], x["system"])})
        if not hits:
            raise ValueError(f"override {r['system_regex']} rejects a table year but matches no result")
        for scope, system in hits:
            reviews.append(
                dict(
                    review_id=f"rev:timeline-year-overrides/{slug(system)}",
                    target_kind="result_date",
                    target=dict(scope=scope, system=system),
                    field="table_year",
                    decision="reject",
                    reason=f"{r['method']}: {r['notes']}",
                    source_id=source_for(r["source_url"], legacy),
                    reviewed_on=r["reviewed_on"],
                    legacy_ids=[legacy],
                )
            )
            report["result_date"] += 1
    # 3. CPU92–CPU95 integer-speed pairs reviewed as configuration-near.
    for r in read_csv(PAIRS):
        legacy = f"research/cpu92-cpu95-reviewed:{r['cpu92_source_url']}"
        left, right = spec_result(results, r["cpu92_source_url"], "speed"), spec_result(results, r["cpu95_source_url"], "speed")
        reviews.append(
            dict(
                review_id=f"rev:cpu92-cpu95-reviewed/{slug(result_key(r['cpu92_source_url']))}",
                target_kind="result_pair",
                target=dict(left=dict(result_id=left), right=dict(result_id=right)),
                decision="accept",
                reason="Configuration-near CPU92/CPU95 integer-speed pair: " + r["decision_note"],
                reviewed_on=r["reviewed_on"],
                legacy_ids=[legacy],
            )
        )
        report["result_pair"] += 1
    # 4. Mix-to-classical identity candidates, expanded to the exact texts their patterns matched.
    texts = defaultdict(set)
    for scope, system in db.execute(
        "SELECT DISTINCT scope, system FROM hardware_record WHERE scope LIKE 'mix:%' OR scope LIKE 'classical:%'"
    ):
        texts[scope.split(":")[0]].add((scope, system))
    for r in read_csv(MIX_CANDIDATES):
        legacy = f"classic/mix-candidate-aliases:{r['mix_regex']}|{r['classical_regex']}"
        lefts = sorted(t for t in texts["mix"] if re.fullmatch(r["mix_regex"], t[1], re.I))
        rights = sorted(t for t in texts["classical"] if re.fullmatch(r["classical_regex"], t[1], re.I))
        if not lefts or not rights:
            raise ValueError(f"mix candidate {legacy} matches no record on one side")
        for (ls, lt), (rs, rt) in ((a, b) for a in lefts for b in rights):
            reviews.append(
                dict(
                    review_id=f"rev:mix-candidate-aliases/{slug(lt)}@{short_hash(ls, lt, rs, rt)}",
                    target_kind="system_link",
                    target=dict(left=dict(scope=ls, system=lt), right=dict(scope=rs, system=rt)),
                    decision="needs_review",
                    reason=r["reason"],
                    reviewed_on=MIX_CANDIDATES_ADDED,
                    legacy_ids=[legacy],
                )
            )
            report["system_link"] += 1
    return (
        dict(
            source=sorted(sources, key=lambda s: s["source_id"]),
            processor_sku=sorted(skus, key=lambda s: s["sku_id"]),
            date_event=sorted(events, key=lambda e: e["event_id"]),
            review=sorted(reviews, key=lambda r: r["review_id"]),
        ),
        report,
    )


@click.command("import-reviews")
@click.option("--root", type=click.Path(path_type=Path, file_okay=False), default=CURATED, show_default=True)
@click.option("--force", is_flag=True, help="Overwrite an existing review table, discarding curated edits.")
def import_reviews_command(root, force):
    """One-time migration: review decisions from the legacy exclusion, override, pair and mix-candidate files."""
    if (root / "review.jsonl").exists() and not force:
        raise click.ClickException("review.jsonl exists and is curated data; pass --force to rebuild it")
    if not DATABASE.exists() or not RESULTS.exists():
        raise click.ClickException("run `cpushowspeed data extract-mentions` and `cpushowspeed data build` first")
    tables = {n: read_table(root, dict(file=n + ".jsonl")) for n in ("source", "processor_sku", "date_event")}
    with closing(sqlite3.connect(DATABASE)) as db:
        out, report = seed_reviews(tables, db)
    for name, rows in out.items():
        write_jsonl(root / f"{name}.jsonl", rows)
    _, tables, errors, _ = validate(root)
    for e in errors:
        click.echo(e, err=True)
    json.dump(dict(tables={k: len(v) for k, v in tables.items()}, report=report, errors=len(errors)), sys.stdout, indent=2)
    click.echo()
    if errors:
        sys.exit(1)


def build_reviews(db, tables):
    """Resolve review selectors: review_result (one row per matched result) and review_system_link."""
    db.execute(
        "CREATE TABLE review_result (review_id TEXT, target_kind TEXT, side TEXT, field TEXT, decision TEXT, result_id TEXT)"
    )
    db.execute(
        "CREATE TABLE review_system_link (review_id TEXT PRIMARY KEY, decision TEXT, left_system_ids TEXT, "
        "right_system_ids TEXT, same_model INTEGER)"
    )
    db.execute("CREATE TABLE review_finding (review_id TEXT, finding TEXT, detail TEXT)")
    if not RESULTS.exists():
        return {"reviews": "skipped: run `cpushowspeed data extract-mentions`"}
    by_id, by_text = set(), defaultdict(list)
    for line in RESULTS.read_text().splitlines():
        r = json.loads(line)
        by_id.add(r["result_id"])
        by_text[r["scope"], r["system"]].append(r["result_id"])
    systems = defaultdict(set)
    for scope, system, system_id in db.execute("SELECT scope, system, system_id FROM hardware_record"):
        systems[scope, system].add(system_id)
    counts = Counter()

    def finding(review, kind, detail):
        db.execute("INSERT INTO review_finding VALUES (?, ?, ?)", (review["review_id"], kind, detail))
        counts[f"finding:{kind}"] += 1

    def matched(selector):
        if "result_id" in selector:
            return [selector["result_id"]] if selector["result_id"] in by_id else []
        return by_text.get((selector["scope"], selector["system"]), [])

    for review in tables.get("review", []):
        kind, target = review["target_kind"], review["target"]
        counts[f"{kind}:{review['decision']}"] += 1
        if kind == "system_link":
            sides = [
                sorted(x for x in systems.get((target[s]["scope"], target[s]["system"]), set()) if x) for s in ("left", "right")
            ]
            if not all(systems.get((target[s]["scope"], target[s]["system"])) for s in ("left", "right")):
                finding(review, "target_unmatched", json.dumps(target, ensure_ascii=False))
            same = bool(sides[0]) and sides[0] == sides[1]
            if same and review["decision"] != "accept":
                finding(review, "unreviewed_link_merged_by_rule", f"both texts resolve to {sides[0][0]}")
            db.execute(
                "INSERT INTO review_system_link VALUES (?, ?, ?, ?, ?)",
                (review["review_id"], review["decision"], json.dumps(sides[0]), json.dumps(sides[1]), int(same)),
            )
            continue
        for side, selector in [(None, target)] if kind == "result_date" else [("left", target["left"]), ("right", target["right"])]:
            ids = matched(selector)
            if not ids:
                finding(review, "target_unmatched", json.dumps(selector, ensure_ascii=False))
            db.executemany(
                "INSERT INTO review_result VALUES (?, ?, ?, ?, ?, ?)",
                [(review["review_id"], kind, side, review.get("field"), review["decision"], rid) for rid in ids],
            )
    return {f"reviews:{k}": str(v) for k, v in sorted(counts.items())}


def rejected_dates(db):
    """{(result_id, field): review_id} for rejected result dates."""
    return {
        (rid, field): review_id
        for review_id, rid, field in db.execute(
            "SELECT review_id, result_id, field FROM review_result WHERE target_kind = 'result_date' AND decision = 'reject'"
        )
    }
