"""Search published instruction-mix OCR without promoting OCR hits to evidence."""

import hashlib
import json
import re
import sqlite3
from pathlib import Path

import click

BATCHES = (
    ("bitsavers", "inventory.sqlite", "chandra-ocr", "instruction-mix-bitsavers-ocr.txt"),
    ("external", "mix-external-inventory.sqlite", "mix-external-ocr", "instruction-mix-external-ocr.txt"),
)
PATTERN = r"gibson|\badp\b|instruction[ -]+mix|whetstone|dhrystone|drystone|linpack"


def text_fields(value):
    """Include canonical table cells, not only prose markdown."""
    if isinstance(value, dict):
        for key, child in value.items():
            if key in ("markdown", "text", "caption", "alt") and isinstance(child, str):
                yield child
            elif isinstance(child, (dict, list)):
                yield from text_fields(child)
    elif isinstance(value, list):
        for child in value:
            yield from text_fields(child)


@click.command("evidence")
@click.option(
    "--output-dir", type=click.Path(path_type=Path), default=Path("data/derived/documents/mix-evidence"), show_default=True
)
def mix_evidence(output_dir):
    """Index keyword hits in the eight selected mix PDFs' published DocIR pages."""
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        documents, hits = [], []
        regex = re.compile(PATTERN, re.I)
        for collection, database, directory, selection in BATCHES:
            with sqlite3.connect(f"file:data/derived/documents/{database}?mode=ro", uri=True) as db:
                source_root = db.execute("SELECT value FROM metadata WHERE key='root'").fetchone()[0]
                for relative in Path("inventories", selection).read_text().splitlines():
                    if not relative.strip():
                        continue
                    digest, pages = db.execute("SELECT blake3,pages FROM files WHERE relative_path=?", (relative,)).fetchone()
                    docir = Path("data/derived/documents", directory, str(Path(relative).with_suffix(".docir.jsonl")))
                    entry = dict(
                        collection=collection,
                        source_path=relative,
                        source_root=source_root,
                        source_blake3=digest,
                        expected_pages=pages,
                        docir_path=str(docir),
                        published=docir.is_file(),
                        scanned_pages=0,
                        hit_pages=[],
                    )
                    if docir.is_file():
                        content = docir.read_bytes()
                        entry["docir_sha256"] = hashlib.sha256(content).hexdigest()
                        page_ids = []
                        for line in content.splitlines():
                            page = json.loads(line)
                            page_ids.append(page["page"])
                            text = "\n".join(text_fields(page["blocks"]))
                            matches = list(regex.finditer(text))
                            if matches:
                                entry["hit_pages"].append(page["page"])
                                hits.append(
                                    dict(
                                        collection=collection,
                                        source_path=relative,
                                        source_blake3=digest,
                                        pdf_page=page["page"],
                                        review_status="unverified_ocr_hit",
                                        terms=sorted({m.group().lower() for m in matches}),
                                        excerpts=[text[max(0, m.start() - 160) : m.end() + 260] for m in matches],
                                    )
                                )
                        if page_ids != list(range(1, pages + 1)):
                            raise ValueError(f"incomplete or unordered DocIR: {docir}")
                        entry["scanned_pages"] = len(page_ids)
                    documents.append(entry)
        (output_dir / "hits.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in hits))
        manifest = dict(
            pattern=PATTERN,
            fields="markdown/text/caption/alt recursively, including table cells",
            documents=documents,
            hit_pages=len(hits),
            missing_documents=sum(not d["published"] for d in documents),
        )
        (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
        click.echo(
            json.dumps(
                dict(
                    documents=len(documents),
                    scanned_pages=sum(d["scanned_pages"] for d in documents),
                    hit_pages=len(hits),
                    missing_documents=manifest["missing_documents"],
                )
            )
        )
    except (OSError, ValueError, sqlite3.Error, TypeError) as exc:
        raise click.ClickException(str(exc)) from exc
