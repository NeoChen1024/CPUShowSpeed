"""CLI for the curated SPEC89 research snapshot."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

import click
from cpushowspeed.spec89_build import build_snapshot
from cpushowspeed.spec89_sources import recover_messages

DEFAULT_SNAPSHOT = Path("research/data/spec89/v2.0.0")
ARCHIVE_ONLY_CHECK = "all_37_messages_reextracted_from_uploaded_mbox_zips"


def verify_snapshot(snapshot: Path) -> dict[str, object]:
    """Check the tracked snapshot and rebuild its tables in a temporary directory."""
    snapshot = snapshot.resolve()
    checksums = snapshot / "SHA256SUMS.txt"
    seen: set[str] = set()
    for line in checksums.read_text().splitlines():
        digest, separator, name = line.partition("  ")
        if not separator or not name or len(digest) != 64:
            raise ValueError(f"invalid checksum line: {line}")
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or name in seen:
            raise ValueError(f"invalid or duplicate checksum path: {name}")
        seen.add(name)
        actual = hashlib.sha256((snapshot / relative).read_bytes()).hexdigest()
        if actual != digest:
            raise ValueError(f"snapshot checksum mismatch: {name}")
    expected_files = {str(path.relative_to(snapshot)) for path in snapshot.rglob("*") if path.is_file() and path != checksums}
    if seen != expected_files:
        raise ValueError(
            f"checksum manifest coverage differs: missing={sorted(expected_files - seen)}, extra={sorted(seen - expected_files)}"
        )

    with tempfile.TemporaryDirectory(prefix="cpushowspeed-spec89-") as temporary:
        output = Path(temporary)
        rebuilt = build_snapshot(snapshot, output)
        tables = sorted((snapshot / "csv").glob("*.csv"))
        for expected in [*tables, snapshot / "summary.json"]:
            actual = output / expected.relative_to(snapshot)
            if expected.read_bytes() != actual.read_bytes():
                raise ValueError(f"rebuild differs from tracked snapshot: {expected.relative_to(snapshot)}")
        original_report = json.loads((snapshot / "validation_report.json").read_text())
        rebuilt_report = json.loads((output / "validation_report.json").read_text())
        original_checks = {item["check"]: item for item in original_report["checks"]}
        rebuilt_checks = {item["check"]: item for item in rebuilt_report["checks"]}
        if not original_report.get("all_passed") or not rebuilt_report.get("all_passed"):
            raise ValueError("snapshot validation report has a failed check")
        if rebuilt_checks != {name: value for name, value in original_checks.items() if name != ARCHIVE_ONLY_CHECK}:
            raise ValueError("rebuild validation checks differ from the tracked report")
        if original_checks.get(ARCHIVE_ONLY_CHECK, {}).get("passed") is not True:
            raise ValueError("historical MBOX recovery check is missing or failed")
        return {
            "snapshot": str(snapshot),
            "checksummed_files": len(seen),
            "reproduced_csv_tables": len(tables),
            "reproduced_validation_checks": len(rebuilt_checks),
            "historical_mbox_check": "recorded but not rerun; original ZIPs are not included",
            "observation_rows": rebuilt["statistics"]["observation_rows"],
            "bridges89_92": rebuilt["statistics"]["bridges89_92"],
        }


@click.group()
def spec89() -> None:
    """Rebuild and verify the curated historical SPEC89 dataset."""


@spec89.command("verify")
@click.option("--snapshot", type=click.Path(path_type=Path), default=DEFAULT_SNAPSHOT, show_default=True)
def verify_command(snapshot: Path) -> None:
    """Verify checksums, source links, and byte-for-byte CSV reconstruction."""
    try:
        result = verify_snapshot(snapshot)
    except (OSError, ValueError, AssertionError, KeyError, json.JSONDecodeError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, sort_keys=True))


@spec89.command("rebuild")
@click.option("--snapshot", type=click.Path(path_type=Path), default=DEFAULT_SNAPSHOT, show_default=True)
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("data/derived/spec89/v2.0.0"), show_default=True)
def rebuild_command(snapshot: Path, output_dir: Path) -> None:
    """Generate all CSV/JSON outputs from the preserved compact inputs."""
    try:
        data = build_snapshot(snapshot, output_dir)
    except (OSError, ValueError, AssertionError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps({"output_dir": str(output_dir), "statistics": data["statistics"]}, sort_keys=True))


@spec89.command("recover-sources")
@click.option(
    "--archive-dir", type=click.Path(path_type=Path), required=True, help="Directory containing the original Usenet MBOX ZIPs."
)
@click.option(
    "--manifest", type=click.Path(path_type=Path), default=DEFAULT_SNAPSHOT / "csv" / "source_manifest.csv", show_default=True
)
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("data/raw/spec89/recovered"), show_default=True)
def recover_command(archive_dir: Path, manifest: Path, output_dir: Path) -> None:
    """Recover original message bytes at recorded MBOX offsets and verify hashes."""
    try:
        count = recover_messages(archive_dir, manifest, output_dir)
    except (OSError, ValueError, KeyError, AssertionError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps({"recovered_messages": count, "output_dir": str(output_dir)}, sort_keys=True))
