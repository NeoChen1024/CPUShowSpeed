"""Source-linked exploratory plots for historical benchmark results."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import re
from dataclasses import asdict, dataclass
from dataclasses import replace as dataclass_replace
from datetime import datetime
from pathlib import Path

import click

REPORT_PATTERN = "*.cint92.*.notes.html"
ISSUE_PATTERN = re.compile(r"<H2>SPECint92 \(Volume \d+, Issue \d+, ([A-Za-z]+) (\d{4})\)</H2>", re.I)
TEST_PATTERN = re.compile(r"<DT>Tested\s*:\s*([A-Za-z]+-\d{2})", re.I)
CPU_COUNT_PATTERN = re.compile(r"Number of CPUs:\s*(\d+)", re.I)
SCORE_PATTERN = re.compile(r"(?:Geometric Mean \(SPECint92\):|\bSPECint92:)\s*([0-9]+(?:\.[0-9]+)?)", re.I)
PROCESSOR_PATTERN = re.compile(r"<DD>CPU:\s*([^<\r\n]+)", re.I)
SYSTEM_PATTERN = re.compile(r"<H3>(.*?)</H3>", re.I | re.S)


@dataclass(frozen=True)
class Cpu92Record:
    publication_year: int
    publication_month: str
    tested_month: str
    metric: str
    score: float
    unit: str
    company: str
    system: str
    processor: str
    cpu_count: int
    source_url: str
    source_sha256: str
    summary_url: str
    summary_sha256: str


def _clean(value: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())


def parse_cpu92_report(path: Path) -> tuple[Cpu92Record | None, str | None]:
    """Read one Netlib detail page, preserving its original metric and issue date."""
    body = path.read_bytes()
    metadata_path = path.with_name(path.name + ".meta.json")
    if not metadata_path.exists():
        raise ValueError(f"missing source metadata: {metadata_path}")
    metadata = json.loads(metadata_path.read_text())
    digest = hashlib.sha256(body).hexdigest()
    if digest != metadata.get("sha256"):
        raise ValueError(f"source hash mismatch: {path}")
    source_url = metadata.get("source_url")
    if not isinstance(source_url, str) or not source_url.startswith("https://www.netlib.org/performance/html/"):
        raise ValueError(f"unexpected source URL: {path}")

    document = body.decode("utf-8", errors="replace")
    issue = ISSUE_PATTERN.search(document)
    tested = TEST_PATTERN.search(document)
    cpu_count = CPU_COUNT_PATTERN.search(document)
    systems = SYSTEM_PATTERN.findall(document)
    processor = PROCESSOR_PATTERN.search(document)
    if not all((issue, tested, cpu_count, processor)) or len(systems) != 2:
        raise ValueError(f"unrecognized CPU92 disclosure structure: {path}")

    issue_month = datetime.strptime(f"{issue.group(1)} {issue.group(2)}", "%B %Y")
    tested_month = datetime.strptime(tested.group(1), "%b-%y")
    if tested_month > issue_month:
        return None, "test_after_issue_month"
    score_match = SCORE_PATTERN.search(document)
    if score_match is None:
        return None, "missing_specint92_score"
    score = float(score_match.group(1))
    if not 0 < score < float("inf"):
        return None, "invalid_score"
    return (
        Cpu92Record(
            publication_year=issue_month.year,
            publication_month=issue_month.strftime("%Y-%m"),
            tested_month=tested_month.strftime("%Y-%m"),
            metric="SPECint92",
            score=score,
            unit="VAXen (CINT92)",
            company=_clean(systems[0]),
            system=_clean(systems[1]),
            processor=_clean(processor.group(1)),
            cpu_count=int(cpu_count.group(1)),
            source_url=source_url,
            source_sha256=digest,
            summary_url="",
            summary_sha256="",
        ),
        None,
    )


def validate_cpu92_summary(path: Path, score: float) -> tuple[str, str]:
    """Check a detailed score against the separate Netlib issue summary."""
    match = re.search(r"\.cint92\.(\d+_\d+)\.notes\.html$", path.name, re.I)
    if match is None:
        raise ValueError(f"unrecognized CPU92 report filename: {path}")
    summary_path = path.parent.parent / f"spec.cint92.{match.group(1)}.col0.html"
    body = summary_path.read_bytes()
    metadata = json.loads(summary_path.with_name(summary_path.name + ".meta.json").read_text())
    digest = hashlib.sha256(body).hexdigest()
    if digest != metadata.get("sha256"):
        raise ValueError(f"summary hash mismatch: {summary_path}")
    summary_url = metadata.get("source_url")
    if not isinstance(summary_url, str) or not summary_url.startswith("https://www.netlib.org/performance/html/"):
        raise ValueError(f"unexpected summary URL: {summary_path}")
    row_pattern = re.compile(re.escape(path.name) + r"[^>]*>.*?</A>\s*([0-9]+(?:\.[0-9]+)?)", re.I | re.S)
    published = row_pattern.search(body.decode("utf-8", errors="replace"))
    if published is None or float(published.group(1)) != score:
        raise ValueError(f"CPU92 detail and issue summary disagree: {path}")
    return summary_url, digest


def collect_cpu92(raw_dir: Path) -> tuple[list[Cpu92Record], list[dict[str, str]]]:
    details_dir = raw_dir / "cpu92" / "netlib" / "details"
    paths = sorted(details_dir.glob(REPORT_PATTERN))
    if not paths:
        raise ValueError(f"no CPU92 integer disclosures found in {details_dir}")
    records: list[Cpu92Record] = []
    exclusions: list[dict[str, str]] = []
    seen: set[str] = set()
    for path in paths:
        record, reason = parse_cpu92_report(path)
        source_url = json.loads(path.with_name(path.name + ".meta.json").read_text())["source_url"]
        if source_url in seen:
            raise ValueError(f"duplicate source disclosure: {source_url}")
        seen.add(source_url)
        if record is None:
            exclusions.append({"source_url": source_url, "reason": reason or "unknown"})
        else:
            summary_url, summary_digest = validate_cpu92_summary(path, record.score)
            records.append(dataclass_replace(record, summary_url=summary_url, summary_sha256=summary_digest))
    records.sort(key=lambda record: (record.publication_year, record.score, record.source_url))
    return records, exclusions


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_cpu92_outputs(records: list[Cpu92Record], exclusions: list[dict[str, str]], output_dir: Path) -> dict[str, object]:
    """Write reviewable records, annual statistics, and a two-format figure."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    output_dir.mkdir(parents=True, exist_ok=True)
    record_path = output_dir / "spec92-int-records.csv"
    exclusion_path = output_dir / "spec92-int-exclusions.csv"
    summary_path = output_dir / "spec92-int-annual.csv"
    _write_csv(record_path, list(Cpu92Record.__dataclass_fields__), [asdict(record) for record in records])
    _write_csv(exclusion_path, ["source_url", "reason"], exclusions)

    years = sorted({record.publication_year for record in records})
    annual: list[dict[str, object]] = []
    for year in years:
        cohort = [record for record in records if record.publication_year == year]
        values = np.asarray([record.score for record in cohort], dtype=float)
        top = max(cohort, key=lambda record: (record.score, record.source_url))
        annual.append(
            {
                "publication_year": year,
                "submissions": len(cohort),
                "minimum_vaxen": float(values.min()),
                "q1_vaxen": round(float(np.percentile(values, 25)), 3),
                "median_vaxen": round(float(np.median(values)), 3),
                "q3_vaxen": round(float(np.percentile(values, 75)), 3),
                "maximum_vaxen": float(values.max()),
                "top_processor": top.processor,
                "top_system": top.system,
                "top_source_url": top.source_url,
            }
        )
    _write_csv(summary_path, list(annual[0]), annual)

    figure, axis = plt.subplots(figsize=(10, 6.6))
    figure.subplots_adjust(left=0.10, right=0.98, top=0.90, bottom=0.23)
    distributions = [[record.score for record in records if record.publication_year == year] for year in years]
    boxes = axis.boxplot(distributions, positions=years, widths=0.55, patch_artist=True, whis=(0, 100), showfliers=False)
    for patch in boxes["boxes"]:
        patch.set_facecolor("#a9c9dd")
        patch.set_edgecolor("#315a72")
    for median in boxes["medians"]:
        median.set_color("#153849")
        median.set_linewidth(2)
    maxima = [float(row["maximum_vaxen"]) for row in annual]
    axis.plot(years, maxima, color="#a94424", marker="o", linewidth=2, label="Highest eligible submission")
    for row in annual:
        axis.annotate(
            f"{row['top_processor']}\n{row['maximum_vaxen']:.1f}",
            (row["publication_year"], row["maximum_vaxen"]),
            xytext=(0, 9),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            color="#80351d",
        )
    axis.set_xticks(years, [f"{row['publication_year']}\nn={row['submissions']}" for row in annual])
    axis.set_yscale("log")
    axis.set_ylabel("SPECint92 score (VAXen; VAX-11/780 = 1)")
    axis.set_xlabel("SPEC Newsletter issue year")
    axis.set_title("SPEC CPU92 integer speed: published system results")
    axis.grid(axis="y", which="both", alpha=0.25)
    axis.legend(loc="upper left")
    axis.margins(x=0.12, y=0.2)
    figure.text(
        0.5,
        0.025,
        "Netlib detailed disclosures; CINT92 only. Box = all eligible submissions; line = published maximum.\n"
        "1992 issues are not in this archive; 1996 has only 10 eligible reports.",
        ha="center",
        va="bottom",
        fontsize=8,
        color="#555555",
    )
    png_path = output_dir / "spec92-int-vaxen.png"
    svg_path = output_dir / "spec92-int-vaxen.svg"
    figure.savefig(png_path, dpi=180)
    figure.savefig(svg_path)
    plt.close(figure)
    return {
        "records": str(record_path),
        "exclusions": str(exclusion_path),
        "annual": str(summary_path),
        "png": str(png_path),
        "svg": str(svg_path),
        "source_disclosures": len(records) + len(exclusions),
        "eligible_records": len(records),
        "excluded_records": len(exclusions),
        "years": years,
    }


@click.group()
def plot() -> None:
    """Generate source-linked exploratory figures."""


@plot.command("spec92")
@click.option("--raw-dir", type=click.Path(path_type=Path), default=Path("data/raw/spec"), show_default=True)
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("data/derived/figures"), show_default=True)
def spec92_command(raw_dir: Path, output_dir: Path) -> None:
    """Plot yearly CINT92 submissions in VAXen from cached Netlib reports."""
    try:
        records, exclusions = collect_cpu92(raw_dir)
        result = write_cpu92_outputs(records, exclusions, output_dir)
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, sort_keys=True))
