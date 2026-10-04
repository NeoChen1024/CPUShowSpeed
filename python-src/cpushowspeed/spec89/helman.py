"""Reproducible union of the immutable SPEC89 snapshot and Helman's 1991 worksheet post."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import zipfile
from pathlib import Path

import click

DEFAULT_AGGREGATE = Path("research/data/spec89/v2.0.0/csv/aggregate89.csv")
DEFAULT_SUPPLEMENT = Path("research/data/spec89/helman-1991")
DEFAULT_OUTPUT = Path("research/data/spec89/aggregate89-plus-helman.csv")

SYSTEM_NAMES = {
    "IBM_RS/6000-320": "IBM RS/6000 320",
    "IBM_RS/6000-520": "IBM RS/6000 520",
    "IBM_RS/6000-530": "IBM RS/6000 530",
    "IBM_RS/6000-540": "IBM RS/6000 540",
    "IBM_RS/6000-550": "IBM RS/6000 550",
    "IBM_RS/6000-730": "IBM RS/6000 730",
    "IBM_RS/6000-930": "IBM RS/6000 930",
    "HP_9000/720": "HP 9000/720",
    "HP_9000/730": "HP 9000/730",
    "DEC_DS2100": "DECstation 2100",
    "DEC_DS3100": "DECstation 3100",
    "DEC_DS5000/200": "DECstation 5000/200",
    "DEC_DS5400": "DECsystem 5400",
    "DEC_DS5810": "DECsystem 5810",
    "MIPS_6280_Beta": "MIPS 6280 (beta)",
    "MIPS_M/120-5": "MIPS M/120-5",
    "MIPS_M/2000": "MIPS M/2000",
    "MIPS_RC2030": "MIPS RC2030",
    "MIPS_RC3240": "MIPS RC3240",
    "MIPS_RC3260": "MIPS RC3260",
    "MIPS_Rx2030": "MIPS RX2030",
    "MIPS_Rx3230": "MIPS RX3230",
    "SGI_4D/210S": "SGI 4D/210S",
    "SGI_4D/25S": "SGI 4D/25S",
    "SGI_4D/320S": "SGI 4D/320S",
    "Solbourne_5/801": "Solbourne 5/801",
    "Sun_4/260": "Sun 4/260",
    "Sun_SS_SLC_est": "Sun SPARCstation SLC",
    "Sun_SS1": "Sun SPARCstation 1",
    "Sun_SS1+": "Sun SPARCstation 1+",
    "Sun_IPC": "Sun SPARCstation IPC",
    "Sun_SS330": "Sun SPARCstation 330",
    "Sun_SS490": "Sun SPARCstation 490",
    "Sun SS/2": "Sun SPARCstation 2",
}

EXTRA_FIELDS = [
    "worksheet_source_note_refs",
    "worksheet_clock_uncertain",
    "worksheet_is_estimate",
    "worksheet_is_beta",
    "worksheet_note7_calculated_from_mashey",
    "worksheet_specmark89_per_mhz_raw",
    "worksheet_specint89_per_mhz_raw",
    "worksheet_specfp89_per_mhz_raw",
    "worksheet_source_row_raw",
]


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError(f"empty CSV: {path}")
        return reader.fieldnames, list(reader)


def _verify_original_mbox(mbox_zip: Path, manifest: dict[str, str], source: bytes) -> None:
    if mbox_zip.name != manifest["archive"]:
        raise ValueError(f"unexpected original MBOX archive: {mbox_zip}")
    with zipfile.ZipFile(mbox_zip) as zipped, zipped.open(manifest["member"]) as stream:
        remaining = int(manifest["start"])
        while remaining:
            block = stream.read(min(remaining, 1024 * 1024))
            if not block:
                raise ValueError("MBOX ends before Helman's source offset")
            remaining -= len(block)
        raw = stream.read(int(manifest["end"]) - int(manifest["start"]))
    if not re.match(rb"^From -?\d+\r?\n", raw):
        raise ValueError("unexpected MBOX envelope")
    if raw.split(b"\n", 1)[1] != source:
        raise ValueError("preserved message differs from original MBOX bytes")


def build_helman_merge(aggregate: Path, supplement: Path, output: Path, mbox_zip: Path | None = None) -> dict[str, object]:
    source_fields, original = _read_csv(aggregate)
    _, worksheet = _read_csv(supplement / "observations.csv")
    _, notes = _read_csv(supplement / "source-notes.csv")
    _, manifests = _read_csv(supplement / "source-manifest.csv")
    if len(manifests) != 1 or len(worksheet) != 40 or len(notes) != 11:
        raise ValueError("unexpected Helman supplement shape")
    manifest = manifests[0]
    source = (supplement / "source.txt").read_bytes()
    if hashlib.sha256(source).hexdigest() != manifest["sha256"]:
        raise ValueError("Helman source message checksum mismatch")
    if mbox_zip is not None:
        _verify_original_mbox(mbox_zip, manifest, source)
    source_lines = source.decode("utf-8").splitlines()
    note_ids = {item["source_note"] for item in notes}
    if note_ids != {str(i) for i in range(1, 12)}:
        raise ValueError("incomplete source note definitions")
    if len({row["record_id"] for row in original}) != len(original):
        raise ValueError("duplicate original record IDs")
    known_names = {row["system_normalized"] for row in original}
    vendor_by_name = {row["system_normalized"]: row["vendor"] for row in original}
    if set(SYSTEM_NAMES) != {row["system_raw"] for row in worksheet} or not set(SYSTEM_NAMES.values()) <= known_names:
        raise ValueError("unreviewed or unknown worksheet system label")
    if len({row["record_id"] for row in worksheet}) != 40 or {row["record_id"] for row in worksheet} & {
        row["record_id"] for row in original
    }:
        raise ValueError("duplicate worksheet record IDs")
    merged = [{**row, **{field: "" for field in EXTRA_FIELDS}} for row in original]
    for item in worksheet:
        line = int(item["source_line"])
        if source_lines[line - 1] != item["source_row_raw"] or item["source_message_id"] != manifest["message_id"]:
            raise ValueError(f"source line mismatch: {item['record_id']}")
        decimals = re.findall(r"\d+\.\d+", item["source_row_raw"])
        expected = [
            item["clock_mhz_raw"],
            item["specmark89_raw"],
            item["specint89_raw"],
            item["specfp89_raw"],
            item["specmark89_per_mhz_raw"],
            item["specint89_per_mhz_raw"],
            item["specfp89_per_mhz_raw"],
        ]
        if decimals != expected or any(
            float(item[key]) != float(item[key + "_raw"]) for key in ("specmark89", "specint89", "specfp89")
        ):
            raise ValueError(f"score transcription mismatch: {item['record_id']}")
        refs = set(item["source_note_refs"].split(","))
        if not refs <= note_ids or ("7" in refs) != (item["note7_calculated_from_mashey"] == "True"):
            raise ValueError(f"source note mismatch: {item['record_id']}")
        if any(item[key] not in {"True", "False"} for key in ("clock_uncertain", "is_estimate", "is_beta")):
            raise ValueError(f"invalid worksheet flag: {item['record_id']}")
        system = SYSTEM_NAMES[item["system_raw"]]
        flags = ["worksheet_derivative"]
        if item["clock_uncertain"] == "True":
            flags.append("clock_uncertain")
        if item["is_estimate"] == "True":
            flags.append("published_estimate")
        if item["is_beta"] == "True":
            flags.append("beta_system")
        if item["note7_calculated_from_mashey"] == "True":
            flags.append("calculated_from_mashey")
        merged.append(
            {
                **{field: "" for field in source_fields},
                "record_id": item["record_id"],
                "source_id": item["source_id"],
                "vendor": vendor_by_name[system],
                "system_raw": item["system_raw"],
                "system_normalized": system,
                "SPECmark89": item["specmark89_raw"],
                "SPECint89": item["specint89_raw"],
                "SPECfp89": item["specfp89_raw"],
                "clock_MHz_raw": item["clock_mhz_raw"],
                "source_date": item["source_date"],
                "suite": "SPEC89 (worksheet version unspecified)",
                "measurement_type": item["measurement_type"],
                "evidence_class": "contemporary_collector",
                "source_url": item["source_archive_url"],
                "page_table": f"Usenet post line {line}",
                "original_provenance": f"James Helman's modified spec.sc worksheet; source note(s) {item['source_note_refs']}",
                "notes": "Published worksheet output; original spec.sc and underlying run disclosures not recovered. Per-MHz values are not IPC.",
                "verification": "archived_message_sha256_verified",
                "source_message_id": item["source_message_id"],
                "source_file": "research/data/spec89/helman-1991/source.txt",
                "source_lines": str(line),
                "import_batch": "helman_1991_supplement",
                "original_record_id": item["record_id"],
                "source_status_raw": "published worksheet derivative; not certified result",
                "component_count": "0",
                "has_reported_score": "True",
                "review_flags": ";".join(flags),
                "worksheet_source_note_refs": item["source_note_refs"],
                "worksheet_clock_uncertain": item["clock_uncertain"],
                "worksheet_is_estimate": item["is_estimate"],
                "worksheet_is_beta": item["is_beta"],
                "worksheet_note7_calculated_from_mashey": item["note7_calculated_from_mashey"],
                "worksheet_specmark89_per_mhz_raw": item["specmark89_per_mhz_raw"],
                "worksheet_specint89_per_mhz_raw": item["specint89_per_mhz_raw"],
                "worksheet_specfp89_per_mhz_raw": item["specfp89_per_mhz_raw"],
                "worksheet_source_row_raw": item["source_row_raw"],
            }
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=[*source_fields, *EXTRA_FIELDS])
        writer.writeheader()
        writer.writerows(merged)
    return {
        "output": str(output),
        "original_observations": len(original),
        "supplement_observations": len(worksheet),
        "total_observations": len(merged),
        "original_mbox_verified": mbox_zip is not None,
    }


@click.command("merge-helman")
@click.option("--aggregate", type=click.Path(path_type=Path), default=DEFAULT_AGGREGATE, show_default=True)
@click.option("--supplement", type=click.Path(path_type=Path), default=DEFAULT_SUPPLEMENT, show_default=True)
@click.option("--output", type=click.Path(path_type=Path), default=DEFAULT_OUTPUT, show_default=True)
@click.option(
    "--mbox-zip", type=click.Path(path_type=Path), help="Optional original comp.benchmarks.mbox.zip for byte verification."
)
def merge_helman_command(aggregate: Path, supplement: Path, output: Path, mbox_zip: Path | None) -> None:
    """Verify Helman's 40 source rows and rebuild the combined SPEC89 CSV."""
    try:
        result = build_helman_merge(aggregate, supplement, output, mbox_zip)
    except (OSError, ValueError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, sort_keys=True))
