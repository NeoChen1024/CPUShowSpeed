"""Reproduce bitsavers hardware-year candidate selection from local inventory."""

import csv
import hashlib
import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

import click


@click.command("year-candidates")
@click.option(
    "--targets",
    "target_path",
    type=click.Path(path_type=Path),
    default=Path("data/derived/classic/historical-timeline/undated.csv"),
)
def year_candidates(target_path):
    """List broad family candidates and select the first 80-document OCR batch."""
    c = sqlite3.connect("file:data/derived/documents/inventory.sqlite?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    rules = {
        "DEC VAX": (r"vax", r"(?:datapro/datapro_reports_70s-90s/DEC/.*(?:VAX|Micro)|dec/brochures/.*VAX)"),
        "DEC Alpha": (
            r"alpha|DEC (?:3000|4000|7000|10000)",
            r"dec/(?:brochures|alpha)/.*(?:Alpha|DEC[-_]?(?:3000|4000|7000|10000)|AXP)",
        ),
        "DEC PDP": (r"PDP|DECsystem|DECSYSTEM", r"datapro/datapro_reports_70s-90s/DEC/.*(?:PDP|system)"),
        "IBM": (r"IBM", r"datapro/datapro_reports_70s-90s/IBM/.*(?:370|303|308|309|430|433|434|438|6000)"),
        "HP": (r"HP|Hewlett", r"datapro/datapro_reports_70s-90s/HP/.*(?:9000|3000|1000|2100)"),
        "Apollo": (r"Apollo", r"datapro/datapro_reports_70s-90s/Apollo/"),
        "Sun": (r"Sun|SPARC", r"(?:datapro/datapro_reports_70s-90s/Sun/|sun/(?:brochures|.*[Pp]roduct.*))"),
        "Amdahl": (r"Amdahl", r"datapro/datapro_reports_70s-90s/Amdahl/"),
        "CDC": (r"CDC|Control Data|Cyber", r"datapro/datapro_reports_70s-90s/.*(?:CDC|Control_Data)/"),
        "Unisys": (r"Univac|Sperry|Unisys|Burroughs", r"datapro/datapro_reports_70s-90s/(?:Univac|Burroughs|Sperry|Unisys)/"),
        "Gould": (r"Gould|SEL", r"(?:datapro/datapro_reports_70s-90s/Gould/|gould/brochures/)"),
        "Prime": (r"Prime", r"datapro/datapro_reports_70s-90s/Prime/"),
        "Cray": (r"Cray", r"cray/brochures/"),
        "SGI": (r"SGI|Silicon", r"(?:sgi/.*(?:[Bb]rochure|[Pp]roduct)|datapro/datapro_reports_70s-90s/Silicon.*)"),
        "Alliant": (r"Alliant", r"alliant/.*(?:[Bb]rochure|[Oo]verview|[Pp]roduct)"),
        "Pyramid": (r"Pyramid", r"(?:pyramid/|datapro/datapro_reports_70s-90s/Pyramid/)"),
        "ICL": (r"ICL", r"datapro/datapro_reports_70s-90s/ICL/"),
    }
    with target_path.open() as stream:
        targets = list(csv.DictReader(stream))
    files = [dict(r) for r in c.execute('select relative_path,pages,blake3 from files where status="ok"')]
    c.close()
    rows = []
    for group, (target_pat, path_pat) in rules.items():
        names = sorted({r["system"] for r in targets if re.search(target_pat, r["system"], re.I)})
        if not names:
            continue
        for f in files:
            if re.search(path_pat, f["relative_path"], re.I):
                rows.append(
                    dict(
                        group=group,
                        **f,
                        target_systems=json.dumps(names),
                        reason="Family/vendor discovery lead; inspect introduction/first-delivery/model tables; filename date is not launch evidence",
                        selected="false",
                    )
                )
    buckets = defaultdict(list)
    for r in rows:
        if 4 <= r["pages"] <= 30:
            buckets[r["group"]].append(r)

    def relevance(r):
        terms = {m for n in json.loads(r["target_systems"]) for m in re.findall(r"(?<!\d)\d{3,5}(?!\d)", n)}
        matched = sum(bool(re.search(r"(?<!\d)" + m + r"(?!\d)", Path(r["relative_path"]).stem)) for m in terms)
        return (-matched, 0 if "datapro" in r["relative_path"] else 1, abs(r["pages"] - 12), r["relative_path"])

    for g in buckets:
        buckets[g].sort(key=relevance)
    selected = []
    seen = set()
    for i in range(8):
        for g, b in buckets.items():
            remaining = [r for r in b if r["blake3"] not in seen]
            if remaining and len(selected) < 80:
                r = remaining[0]
                seen.add(r["blake3"])
                r["selected"] = "true"
                selected.append(r)
    p = Path("inventories/hardware-year-candidates.csv")
    with p.open("w") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    Path("inventories/hardware-year-ocr.txt").write_text("".join(r["relative_path"] + "\n" for r in selected))
    Path("inventories/hardware-year-search.json").write_text(
        json.dumps(
            dict(
                reviewed_on="2026-09-27",
                rules=rules,
                selection="Round-robin groups; 4..30 pages; prefer target model-number hits then Datapro and approximately 12-page reports; distinct BLAKE3; 80-document first batch",
                target_file=str(target_path),
                target_sha256=hashlib.sha256(target_path.read_bytes()).hexdigest(),
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            dict(
                candidates=len(rows),
                selected=len(selected),
                pages=sum(r["pages"] for r in selected),
                groups={g: sum(r["group"] == g for r in selected) for g in buckets},
            )
        )
    )


@click.command("year-evidence")
@click.option("--file-list", type=click.Path(path_type=Path), default=Path("inventories/hardware-year-ocr.txt"))
@click.option("--output", type=click.Path(path_type=Path), default=Path("data/derived/documents/year-evidence"))
def year_evidence(file_list, output):
    """Find unreviewed date passages in source text layers and completed DocIR."""
    import subprocess
    from concurrent.futures import ThreadPoolExecutor

    conn = sqlite3.connect("file:data/derived/documents/inventory.sqlite?mode=ro", uri=True)
    root = Path(conn.execute("select value from metadata where key='root'").fetchone()[0])
    inventory = {p: h for p, h in conn.execute("select relative_path,blake3 from files where status='ok'")}
    conn.close()
    paths = file_list.read_text().splitlines()
    if any(p not in inventory for p in paths):
        raise click.ClickException("File list contains a path absent from the successful PDF inventory")
    pattern = re.compile(r"first (?:deliver|install|ship)|date (?:of )?(?:announc|first)|introduc(?:ed|tion)|announced in", re.I)
    output.mkdir(parents=True, exist_ok=True)

    def extract(rel):
        result = subprocess.run(["pdftotext", "-layout", str(root / rel), "-"], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(f"pdftotext failed for {rel}: {result.stderr}")
        dest = output / "text" / Path(rel).with_suffix(".txt")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(result.stdout)
        hits = []
        for page, text in enumerate(result.stdout.split("\f"), 1):
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if pattern.search(line):
                    hits.append(
                        dict(
                            path=rel,
                            source_blake3=inventory[rel],
                            pdf_page=page,
                            text="\n".join(lines[max(0, i - 2) : i + 5]),
                            verification="unreviewed_text_layer",
                        )
                    )
        docir = Path("data/derived/documents/chandra-ocr") / Path(rel).with_suffix(".docir.jsonl")
        if docir.exists():
            for line in docir.read_text().splitlines():
                page = json.loads(line)
                for block in page.get("blocks", []):
                    text = json.dumps(block, ensure_ascii=False)
                    if pattern.search(text):
                        hits.append(
                            dict(
                                path=rel,
                                source_blake3=inventory[rel],
                                pdf_page=page["page"],
                                text=text,
                                verification="unreviewed_DocIR_block",
                            )
                        )
        return hits

    with ThreadPoolExecutor(8) as pool:
        hits = [h for batch in pool.map(extract, paths) for h in batch]
    (output / "date-hits.jsonl").write_text("".join(json.dumps(h, ensure_ascii=False) + "\n" for h in hits))
    manifest = dict(
        file_list=str(file_list),
        file_list_sha256=hashlib.sha256(file_list.read_bytes()).hexdigest(),
        source_blake3={p: inventory[p] for p in paths},
        pattern=pattern.pattern,
        verification="discovery_only_original_pages_require_review",
        hits=len(hits),
    )
    (output / "search-audit.json").write_text(json.dumps(manifest, indent=2) + "\n")
    # A completed OCR run is distinct from a completed source review.
    from cpushowspeed.research_io import read_csv, write_csv

    events = read_csv(Path("research/data/historical/hardware-date-evidence.csv"))
    review_path = Path("research/data/historical/year-document-reviews.csv")
    reviews = {r["source_path"]: r for r in read_csv(review_path)} if review_path.exists() else {}
    index = []
    for rel in paths:
        docir = Path("data/derived/documents/chandra-ocr") / Path(rel).with_suffix(".docir.jsonl")
        pages = [json.loads(line) for line in docir.read_text().splitlines()] if docir.exists() else []
        found = [h for h in hits if h["path"] == rel]
        reviewed = [e for e in events if e["source_path"] == rel]
        review = reviews.get(rel, {})
        # A manual disposition applies only to the exact reviewed PDF and page coverage.
        complete = (
            review.get("source_blake3") == inventory[rel]
            and review.get("review_status") == "date_scope_review_complete"
            and review.get("text_pages_screened") == str(len(pages))
            and review.get("total_pages") == str(len(pages))
            and bool(review.get("original_pdf_pages_checked"))
        )
        index.append(
            dict(
                source_path=rel,
                source_blake3=inventory[rel],
                published_docir_pages=len(pages),
                docir_sha256=hashlib.sha256(docir.read_bytes()).hexdigest() if docir.exists() else "",
                candidate_hits=len(found),
                candidate_pages=";".join(map(str, sorted({h["pdf_page"] for h in found}))),
                reviewed_event_count=len(reviewed),
                reviewed_pdf_pages=";".join(sorted({e["pdf_page"] for e in reviewed})),
                review_status=(
                    "date_scope_review_complete"
                    if complete
                    else (
                        "partly_source_checked"
                        if reviewed
                        else "unreviewed_candidates" if found else "no_keyword_hit_not_proof_of_absence"
                    )
                ),
                review_disposition=review.get("disposition", "") if complete else "",
                original_pdf_pages_checked=review.get("original_pdf_pages_checked", "") if complete else "",
            )
        )
    write_csv(output / "review-index.csv", index)
    click.echo(json.dumps(dict(documents=len(paths), hits=len(hits), output=str(output))))
