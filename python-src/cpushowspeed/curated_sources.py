"""Migrate the legacy source registries into data/curated/source.jsonl (schema step 1).

Every legacy row becomes a claim. Claims merge when they share a content hash; a
claim without a hash joins the single hash group that has its URL, otherwise it
groups by URL alone. Different hashes for one URL stay separate snapshots.
Conflicting field values are reported, never silently resolved.
"""

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

import click
from cpushowspeed.curated import CURATED, load_schema, validate, write_jsonl

LEGACY = {
    "classic/acquisition": Path("research/data/classic/acquisition.csv"),
    "classic/pdf-acquisition": Path("research/data/classic/pdf-acquisition.jsonl"),
    "classic/literature-sources": Path("research/data/classic/literature-sources.jsonl"),
    "docs/early-benchmark-sources": Path("docs/data/early-benchmark-sources.csv"),
    "docs/classic-benchmark-sources": Path("docs/data/classic-benchmark-sources.csv"),
    "historical/cpu-sku-sources": Path("research/data/historical/cpu-sku-sources.json"),
    "historical/hardware-date-evidence": Path("research/data/historical/hardware-date-evidence.csv"),
    "historical/year-document-reviews": Path("research/data/historical/year-document-reviews.csv"),
    "historical/observations": Path("research/data/historical/observations.jsonl"),
    "archive/year-wikipedia-sources": Path("research/data/archive/date-passes/wikipedia/year-wikipedia-sources.json"),
    "archive/year-expansion-web-sources": Path("research/data/archive/date-passes/expansion/year-expansion-web-sources.json"),
}
# Curated slugs win as the new ID, in this order; derived IDs are used otherwise.
ID_PRIORITY = [
    "classic/acquisition",
    "classic/pdf-acquisition",
    "classic/literature-sources",
    "docs/early-benchmark-sources",
    "docs/classic-benchmark-sources",
]
PROVENANCE = {
    "secondary_historical_catalog": "modern_secondary",
    "secondary_encyclopedia": "modern_secondary",
    "contemporary_report": "contemporary_secondary",
    "historical_museum": "historical_museum",
    "vendor_SPEC_disclosure": "vendor",
    "vendor_history": "vendor",
    "vendor_fact_sheet": "vendor",
    "vendor_news_index": "vendor",
    "vendor_release_reprint": "vendor",
}
VERIFICATION = {
    "original_page_visual_check": "selected_pages_verified",
    "web_text_checked": "text_reviewed",
    "web_page_checked_secondary_source": "text_reviewed",
}
FIELDS = [
    "source_id",
    "kind",
    "title",
    "url",
    "final_url",
    "alternate_urls",
    "store",
    "local_path",
    "hash_algo",
    "hash",
    "revision",
    "size_bytes",
    "retrieved_on",
    "date",
    "date_precision",
    "provenance_class",
    "provider",
    "work_id",
    "families",
    "role",
    "acquisition_status",
    "reviews",
    "note",
    "legacy_ids",
]
SINGLE = [
    "kind",
    "title",
    "url",
    "final_url",
    "store",
    "local_path",
    "revision",
    "size_bytes",
    "retrieved_on",
    "provider",
    "work_id",
    "role",
]


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def norm_url(url):
    """Scheme- and www-insensitive identity; the original URL is kept on the row."""
    if not url:
        return None
    parts = urlsplit(url.strip())
    host = parts.netloc.lower().removeprefix("www.")
    return host + parts.path.rstrip("/") + ("?" + parts.query if parts.query else "")


def slug(text):
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9._/@+-]", "-", text.lower())).strip("-/")


def split_list(value):
    return [v.strip() for v in re.split(r"[;,]", value or "") if v.strip()]


def kind_of(url, path=""):
    target = (path or url or "").lower()
    host = urlsplit(url or "").netloc.lower()
    if "wikipedia.org" in host:
        return "wiki_revision"
    if "spec.org" in host and "/results/" in target:
        return "spec_result"
    ext = target.rsplit(".", 1)[-1] if "." in target.rsplit("/", 1)[-1] else ""
    return {
        "pdf": "pdf",
        "ps": "postscript",
        "zip": "archive_file",
        "c": "program_source",
        "for": "program_source",
        "f": "program_source",
        "txt": "text_file",
    }.get(ext, "web_page")


def claim(origin, key, **fields):
    return dict(origin=origin, legacy=f"{origin}:{key}", **{k: v for k, v in fields.items() if v not in (None, "", [])})


def acquisition_claims(origin, rows):
    for r in rows:
        yield claim(
            origin,
            r["source_id"],
            curated_id=r["source_id"],
            url=r["url"],
            final_url=r.get("final_url"),
            provider=r.get("provider"),
            work_id=r.get("lineage"),
            families=split_list(r.get("family")),
            role=r.get("role"),
            retrieved_on=r.get("retrieved_date"),
            hash=("blake3", r["blake3"]) if r.get("blake3") else None,
            size_bytes=int(r["bytes"]) if r.get("bytes") else None,
            store="repo" if r.get("blob_path") else None,
            local_path=r.get("blob_path"),
            acquired=r.get("status") == "downloaded",
            kind=kind_of(r.get("final_url") or r["url"]) if "pdf" not in (r.get("content_type") or "") else "pdf",
        )


def spec_bulk_index(root=Path("data/raw/spec")):
    """SPEC bulk exports by SHA-256; date evidence cites the export, with a per-row disclosure URL."""
    index = {}
    for meta in sorted(root.glob("*/bulk.csv.meta.json")):
        m = json.loads(meta.read_text())
        index[m["sha256"]] = dict(m, path=str(meta.with_name("bulk.csv")), generation=meta.parent.name)
    return index


def legacy_claims():
    bulk = spec_bulk_index()
    yield from acquisition_claims("classic/acquisition", read_csv(LEGACY["classic/acquisition"]))
    yield from acquisition_claims("classic/pdf-acquisition", read_jsonl(LEGACY["classic/pdf-acquisition"]))
    for r in read_csv(LEGACY["docs/classic-benchmark-sources"]):
        yield claim("docs/classic-benchmark-sources", r["source_id"], curated_id=r["source_id"], url=r["url"])
    for r in read_jsonl(LEGACY["classic/literature-sources"]):
        yield claim(
            "classic/literature-sources",
            r["source_id"],
            curated_id=r["source_id"],
            url=r["url"],
            role=r.get("role"),
            families=split_list(r.get("metrics")),
            review=dict(status=r["review_status"], scope=r.get("locator") or "literature review", reviewed_on=r.get("review_date")),
            note="Limitation: " + r["limitation"] if r.get("limitation") else None,
        )
    for r in read_csv(LEGACY["docs/early-benchmark-sources"]):
        yield claim(
            "docs/early-benchmark-sources",
            r["source_id"],
            curated_id=r["source_id"],
            url=r["url"],
            title=r.get("title"),
            families=split_list(r.get("family")),
            review=dict(status=r["status"], scope=r.get("locator") or "lead discovery", reviewed_on=r.get("review_date")),
            note="Next step: " + r["next_step"] if r.get("next_step") else None,
        )
    for r in json.loads(LEGACY["historical/cpu-sku-sources"].read_text()):
        yield claim(
            "historical/cpu-sku-sources",
            r["title"] + "@" + r["revision_id"],
            url=r["url"],
            title=r["title"],
            revision=r["revision_id"],
            hash=("sha256", r["sha256"]),
            retrieved_on=r["retrieved_on"],
            store="repo",
            local_path="data/derived/documents/cpu-chronology/"
            + re.sub(r"[^A-Za-z0-9]+", "_", r["requested_title"]).strip("_")
            + ".html",
            acquired=True,
            provenance="modern_secondary",
            review=dict(status="machine_parsed_unreviewed", scope="SKU release-date tables", reviewed_on=r["retrieved_on"]),
        )
    # Archived manifests enrich cited web snapshots with revision and cache path only.
    for r in json.loads(LEGACY["archive/year-wikipedia-sources"].read_text()):
        if r.get("sha256"):
            yield claim(
                "archive/year-wikipedia-sources",
                r["url"] + "@" + r["sha256"][:12],
                url=r["url"],
                title=r.get("title", "").replace("_", " "),
                revision=r.get("revision_id"),
                hash=("sha256", r["sha256"]),
                retrieved_on=r.get("reviewed_on"),
                store="repo" if r.get("path") else None,
                local_path=r.get("path"),
                acquired=True,
                enrich_only=True,
            )
    for r in json.loads(LEGACY["archive/year-expansion-web-sources"].read_text()):
        if r.get("sha256"):
            yield claim(
                "archive/year-expansion-web-sources",
                r["url"] + "@" + r["sha256"][:12],
                url=r["url"],
                hash=("sha256", r["sha256"]),
                retrieved_on=r.get("accessed_on"),
                store="repo" if r.get("path") else None,
                local_path=r.get("path"),
                acquired=True,
                enrich_only=True,
            )
    for r in read_csv(LEGACY["historical/hardware-date-evidence"]):
        common = dict(
            provenance=PROVENANCE.get(r.get("source_kind")),
            review=dict(
                status=VERIFICATION[r["verification"]],
                scope="date evidence"
                + (f", physical PDF page {r['pdf_page']}" if r.get("pdf_page") else "")
                + (f", {r['source_locator']}" if r.get("source_locator") else ""),
                reviewed_on=r.get("reviewed_on"),
            ),
        )
        if r.get("source_path"):
            yield claim(
                "historical/hardware-date-evidence",
                r["id"],
                url=r.get("source_url"),
                hash=("blake3", r["source_blake3"]) if r.get("source_blake3") else None,
                store="bitsavers_mirror",
                local_path=r["source_path"],
                acquired=True,
                kind="pdf",
                **common,
            )
        elif r.get("snapshot_sha256") in bulk:
            b = bulk[r["snapshot_sha256"]]
            yield claim(
                "historical/hardware-date-evidence",
                r["id"],
                url=b["source_url"],
                title=f"SPEC {b['generation'].upper()} results bulk export",
                kind="dataset",
                hash=("sha256", r["snapshot_sha256"]),
                retrieved_on=b["retrieved_on"],
                store="repo",
                local_path=b["path"],
                acquired=True,
                note="Published by SPEC; hardware availability and other result fields are submitter-reported. "
                "Date events cite individual disclosure URLs as locators.",
                **dict(common, provenance="benchmark_org"),
            )
        else:
            yield claim(
                "historical/hardware-date-evidence",
                r["id"],
                url=r["source_url"],
                hash=("sha256", r["snapshot_sha256"]) if r.get("snapshot_sha256") else None,
                **common,
            )
    for r in read_csv(LEGACY["historical/year-document-reviews"]):
        pages = r.get("original_pdf_pages_checked")
        yield claim(
            "historical/year-document-reviews",
            r["source_path"],
            hash=("blake3", r["source_blake3"]),
            store="bitsavers_mirror",
            local_path=r["source_path"],
            acquired=True,
            kind="pdf",
            review=dict(
                status=r["review_status"],
                scope="date scope" + (f", original pages {pages}" if pages else "") + f"; {r['disposition']}",
                reviewed_on=r.get("reviewed_on"),
            ),
        )
    for r in read_jsonl(LEGACY["historical/observations"]):
        s = r["source"]
        yield claim(
            "historical/observations",
            r["id"],
            url=s.get("url"),
            hash=("blake3", s["pdf_blake3"]) if s.get("pdf_blake3") else None,
            store="bitsavers_mirror" if s.get("relative_pdf") else None,
            local_path=s.get("relative_pdf"),
            acquired=bool(s.get("relative_pdf")),
            kind="pdf" if s.get("relative_pdf") else None,
            review=dict(
                status="selected_pages_verified" if r.get("verification") == "original_page_visual_check" else "text_reviewed",
                scope=f"observation, physical PDF page {r['pdf_page']}" if r.get("pdf_page") else "observation",
                reviewed_on=r.get("review_date"),
            ),
        )


def group_claims(claims):
    """Union claims sharing a hash or a legacy curated ID, then attach hashless claims by URL."""
    parent = list(range(len(claims)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(keyed):
        first = {}
        for i, key in keyed:
            if key in first:
                parent[find(i)] = find(first[key])
            else:
                first[key] = i

    union((i, c["hash"]) for i, c in enumerate(claims) if "hash" in c)
    # Legacy registries share one source_id namespace; equal IDs name one source.
    union((i, c["curated_id"]) for i, c in enumerate(claims) if "curated_id" in c)
    groups = defaultdict(list)
    for i in range(len(claims)):
        groups[find(i)].append(i)
    hashed = {g for g, members in groups.items() if any("hash" in claims[i] for i in members)}
    url_groups = defaultdict(set)
    for g in hashed:
        for i in groups[g]:
            if norm_url(claims[i].get("url")):
                url_groups[norm_url(claims[i]["url"])].add(g)
    for g in [g for g in groups if g not in hashed]:
        urls = {norm_url(claims[i].get("url")) for i in groups[g]} - {None}
        targets = set().union(*(url_groups.get(u, set()) for u in urls)) if urls else set()
        if not urls:
            raise ValueError("legacy source without URL or hash: " + claims[groups[g][0]]["legacy"])
        if len(targets) == 1:
            parent[find(g)] = find(next(iter(targets)))
    final = defaultdict(list)
    for i in range(len(claims)):
        final[find(i)].append(claims[i])
    # Remaining hashless groups that share a URL describe the same unsnapshotted page.
    merged, by_url = [], {}
    for members in final.values():
        if any("hash" in c for c in members):
            merged.append(members)
            continue
        u = min(norm_url(c.get("url")) for c in members if c.get("url"))
        by_url.setdefault(u, []).extend(members)
    merged += list(by_url.values())
    # Enrichment-only manifests never create a source by themselves.
    return [g for g in merged if not all(c.get("enrich_only") for c in g)]


def derived_id(row):
    if row.get("store") == "bitsavers_mirror":
        return "src:bitsavers/" + slug(row["local_path"])
    url = row.get("url", "")
    parts = urlsplit(url)
    base = slug(parts.netloc.removeprefix("www.") + parts.path)[:96].strip("-/")
    conf = re.search(r"conf=([a-z0-9]+)", parts.query)
    if row["kind"] == "dataset" and "spec.org" in parts.netloc and conf:
        return f"src:spec/{conf[1]}-bulk@" + row["hash"][:12]
    if row["kind"] == "wiki_revision":
        base = "wikipedia/" + slug(parts.path.rsplit("/", 1)[-1])
        return "src:" + base + "@" + (row.get("revision") or "sha-" + row["hash"][:12])
    return "src:web/" + base + ("@" + row["hash"][:12] if row.get("hash") else "")


def merge(group, conflicts):
    priority = {o: i for i, o in enumerate(ID_PRIORITY)}
    group = sorted(group, key=lambda c: (priority.get(c["origin"], 99), c["legacy"]))
    row = {}
    for field in SINGLE:
        values = list(dict.fromkeys(c[field] for c in group if field in c))
        if values:
            row[field] = values[0]
            if len(values) > 1 and field not in ("url", "kind", "retrieved_on", "title", "role"):
                conflicts.append(dict(legacy=[c["legacy"] for c in group], field=field, values=values))
    hashes = list(dict.fromkeys(c["hash"] for c in group if "hash" in c))
    if hashes:
        row["hash_algo"], row["hash"] = hashes[0]
    https = [c["url"] for c in group if c.get("url", "").startswith("https://")]
    if https:
        row["url"] = https[0]
    alternates = [
        u for u in dict.fromkeys(c["url"] for c in group if c.get("url")) if u not in (row.get("url"), row.get("final_url"))
    ]
    if alternates:
        row["alternate_urls"] = alternates
    row.setdefault("kind", kind_of(row.get("url"), row.get("local_path", "")))
    if row["kind"] == "web_page" and "wikipedia.org" in (row.get("url") or ""):
        row["kind"] = "wiki_revision"
    provenance = list(dict.fromkeys(c["provenance"] for c in group if c.get("provenance")))
    if len(provenance) > 1:
        conflicts.append(dict(legacy=[c["legacy"] for c in group], field="provenance_class", values=provenance))
    row["provenance_class"] = (
        provenance[0] if provenance else ("modern_secondary" if row["kind"] == "wiki_revision" else "unclassified")
    )
    families = list(dict.fromkeys(f for c in group for f in c.get("families", [])))
    if families:
        row["families"] = families
    row["acquisition_status"] = "acquired" if any(c.get("acquired") for c in group) else "not_acquired"
    reviews = {}
    for c in group:
        if "review" in c:
            r = dict(c["review"], origin=c["origin"])
            reviews[tuple(sorted(r.items()))] = {k: v for k, v in r.items() if v}
    row["reviews"] = sorted(reviews.values(), key=lambda r: (r.get("reviewed_on", ""), r["status"], r["scope"]))
    notes = list(dict.fromkeys(c["note"] for c in group if c.get("note")))
    if notes:
        row["note"] = " | ".join(notes)
    curated = next((c["curated_id"] for c in group if c.get("curated_id")), None)
    row["source_id"] = "src:" + slug(curated) if curated else derived_id(row)
    row["legacy_ids"] = sorted({c["legacy"] for c in group})
    return {k: row[k] for k in FIELDS if k in row}


@click.command("migrate-sources")
@click.option("--root", type=click.Path(path_type=Path, file_okay=False), default=CURATED, show_default=True)
@click.option("--force", is_flag=True, help="Overwrite an existing source.jsonl, discarding curated edits made since.")
def migrate_sources_command(root, force):
    """One-time migration: build data/curated/source.jsonl from the legacy registries and report merges."""
    try:
        if (root / "source.jsonl").exists() and not force:
            raise click.ClickException(
                "source.jsonl exists and is now curated data; pass --force to rebuild it from legacy registries"
            )
        load_schema(root)
        claims = list(legacy_claims())
        conflicts = []
        rows = [merge(g, conflicts) for g in group_claims(claims)]
        ids = defaultdict(int)
        for r in sorted(rows, key=lambda r: (r["source_id"], r["legacy_ids"])):
            ids[r["source_id"]] += 1
            if ids[r["source_id"]] > 1:
                r["source_id"] += f"~{ids[r['source_id']]}"
        rows.sort(key=lambda r: r["source_id"])
        write_jsonl(root / "source.jsonl", rows)
        _, tables, errors, _ = validate(root)
        for e in errors:
            click.echo(e, err=True)
        by_origin = defaultdict(int)
        for c in claims:
            by_origin[c["origin"]] += 1
        report = dict(
            claims=len(claims),
            claims_by_origin=dict(sorted(by_origin.items())),
            sources=len(rows),
            sources_by_kind=dict(sorted(_count(r["kind"] for r in rows).items())),
            sources_by_provenance=dict(sorted(_count(r["provenance_class"] for r in rows).items())),
            id_suffixed=sorted(r["source_id"] for r in rows if "~" in r["source_id"]),
            conflicts=conflicts,
            validation_errors=len(errors),
        )
        json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
        click.echo()
        if errors:
            sys.exit(1)
    except (OSError, ValueError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc


def _count(values):
    out = defaultdict(int)
    for v in values:
        out[v] += 1
    return out
