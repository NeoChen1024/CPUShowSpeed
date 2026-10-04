"""Recover and authenticate archived SPEC89 Usenet source messages."""

from __future__ import annotations

import csv
import hashlib
import re
import zipfile
from collections import defaultdict
from pathlib import Path


def _skip(stream, length: int) -> None:
    while length:
        block = stream.read(min(length, 1024 * 1024))
        if not block:
            raise ValueError("MBOX ended before the requested source offset")
        length -= len(block)


def recover_messages(archive_dir: Path, manifest_path: Path, output_dir: Path) -> int:
    """Verify exact MBOX ranges and write original message bytes after all checks pass."""
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    with manifest_path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            groups[row["archive"]].append(row)
    if not groups:
        raise ValueError(f"no source messages in {manifest_path}")

    recovered: dict[str, bytes] = {}
    for archive, rows in sorted(groups.items()):
        zip_path = archive_dir / Path(archive).name
        with zipfile.ZipFile(zip_path) as zipped:
            entries = [entry for entry in zipped.infolist() if entry.filename.endswith(".mbox") and not entry.is_dir()]
            if len(entries) != 1:
                raise ValueError(f"{zip_path}: expected one .mbox, found {len(entries)}")
            entry = entries[0]
            with zipped.open(entry) as stream:
                cursor = 0
                for row in sorted(rows, key=lambda item: int(item["mbox_start"])):
                    start, end = int(row["mbox_start"]), int(row["mbox_end"])
                    if not cursor <= start < end <= entry.file_size:
                        raise ValueError(f"invalid or overlapping MBOX offsets: {row['source_id']}")
                    _skip(stream, start - cursor)
                    raw = stream.read(end - start)
                    if len(raw) != end - start or hashlib.sha256(raw).hexdigest() != row["envelope_record_sha256"]:
                        raise ValueError(f"MBOX record checksum mismatch: {row['source_id']}")
                    if not re.match(rb"^From -?\d+\r?\n", raw):
                        raise ValueError(f"unexpected MBOX envelope: {row['source_id']}")
                    message = raw[raw.index(b"\n") + 1 :]
                    if hashlib.sha256(message).hexdigest() != row["eml_sha256"]:
                        raise ValueError(f"message checksum mismatch: {row['source_id']}")
                    filename = Path(row["extracted_file"]).name
                    if filename in recovered:
                        raise ValueError(f"duplicate recovered source filename: {filename}")
                    recovered[filename] = message
                    cursor = end

    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, message in recovered.items():
        (output_dir / filename).write_bytes(message)
    return len(recovered)
