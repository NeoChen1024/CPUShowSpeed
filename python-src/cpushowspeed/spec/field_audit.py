"""Inventory all SPEC source fields, their consumers, and declared resource evidence."""

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import click
from cpushowspeed.research_io import code_hashes, write_csv
from cpushowspeed.spec.collect import GENERATIONS, collect_disclosures, get_cached
from cpushowspeed.spec.execution_resources import canonical, integer, load_disclosure, parse_disclosure
from cpushowspeed.spec.result_pairing import disclosure_url, positive, read_checked_bulk
from cpushowspeed.spec.source_fields import collect_speed92


def field_use(field):
    key = canonical(field)
    if key == "benchmark":
        return "metric selection", "integer/floating-point and speed/rate must remain distinct"
    if key in ("result", "baseline", "peakresult", "baseresult"):
        return "score selection; fitting; plotting", "positive aggregate only; base and peak remain separate"
    if key in ("cores", "chips", "threadspercore", "enabledthreadspercore"):
        return "matching; timeline hardware", "enabled resources; not runtime copies/threads"
    if key == "coresperchip":
        return (
            "timeline context; audit; not a matching guard",
            "chip capacity may exceed enabled cores/chip; not a consistency equality",
        )
    if key in ("system", "processor", "cpu", "processormhz", "memory"):
        return "matching; chronology; timeline", "memory parsing keeps capacity only; clock nominal/fallback; raw text retained"
    if key in ("opsys", "operatingsystem"):
        return "CPU92/95 same-OS admission; pair provenance; timeline", "later-generation OS equality not required"
    if key == "compiler":
        return "pair provenance only", "version/flags/PGO/auto-parallel can change score; not a matching guard"
    if key in ("hwavail", "swavail", "testdate", "published", "updated"):
        return "date handling (HW/test/publication); SW/update metadata only", "availability != release; date priority documented"
    if key in ("disclosure", "disclosures"):
        return "identity; acquisition; citations", "full details required for runtime resources"
    if "cache" in key or key in ("storage", "filesystem", "processorcharacteristics"):
        return "raw preserved; not a matching guard", "cache topology/sharing, memory subsystem and platform differences can matter"
    if key in ("parallel", "autoparallelization", "basepointersize", "peakpointersize", "compilercategory"):
        return (
            "raw preserved; not a matching guard",
            "parallel capability is not a runtime thread count; pointer size/optimization differ",
        )
    if key == "cpusorderable":
        return "raw preserved; not used as enabled count", "sales options are not tested chip/core counts"
    if "energy" in key:
        return "outside current performance target", "energy metrics are separate from speed/rate"
    return "identity/context retained in raw export", "not used numerically in current fitting"


def valid_score(row):
    return bool(positive(row.get("Result") or row.get("Peak Result")) or positive(row.get("Baseline") or row.get("Base Result")))


def bulk_resources(row):
    def first(*keys):
        return next((row[k] for k in keys if row.get(k, "") != ""), "")

    return dict(
        enabled_cores=integer(first("# Cores", "# cores")),
        enabled_chips=integer(first("# Chips", "# chips")),
        cores_per_chip=integer(first("# Cores Per Chip", "# cores per chip")),
        threads_per_core=integer(first("# Enabled Threads Per Core", "# Threads Per Core")),
    )


@click.command("audit-fields")
@click.option("--raw-dir", type=click.Path(path_type=Path), default=Path("data/raw/spec"), show_default=True)
@click.option("--output", type=click.Path(path_type=Path), default=Path("data/derived/spec/field-audit"), show_default=True)
@click.option(
    "--research-output", type=click.Path(path_type=Path), default=Path("research/data/spec/field-audit"), show_default=True
)
@click.option("--fetch-samples", is_flag=True, help="Resume the reviewed sample manifest; no full-archive download.")
def audit_fields(raw_dir, output, research_output, fetch_samples):
    """Audit all bulk columns/rows and cached integer disclosures without changing scores."""
    output.mkdir(parents=True, exist_ok=True)
    research_output.mkdir(parents=True, exist_ok=True)
    if fetch_samples:
        manifest = json.loads((research_output / "sample-manifest.json").read_text())
        for row in manifest:
            path = Path(row["path"])
            get_cached(row["document_url"], path, refresh=False, delay=0.2)
    inventory, anomalies, summaries, details, reviews, coverage = [], [], [], [], [], []
    hashes = {}
    for gen in GENERATIONS:
        path = raw_dir / gen / "bulk.csv"
        rows, digest = read_checked_bulk(path)
        hashes[str(path)] = digest
        ints = [r for r in rows if r["Benchmark"] in ("CINT" + gen[3:], "CINT" + gen[3:] + "rate")]
        for field in rows[0]:
            use, qualification = field_use(field)
            inventory.append(
                dict(
                    source=str(path),
                    generation=gen,
                    field=field,
                    total_rows=len(rows),
                    nonempty=sum(bool(r[field]) for r in rows),
                    integer_rows=len(ints),
                    integer_nonempty=sum(bool(r[field]) for r in ints),
                    current_use=use,
                    qualification=qualification,
                    source_sha256=digest,
                )
            )
        stats = Counter()
        for row in ints:
            track = "rate" if row["Benchmark"].endswith("rate") else "speed"
            source = disclosure_url(row["Disclosure"])
            resources = bulk_resources(row)
            usable = valid_score(row)
            stats[track + "_rows"] += 1
            stats[track + "_positive_aggregate"] += usable
            context = dict(
                generation=gen,
                track=track,
                source_url=source,
                system=row["System"],
                processor=row.get("Processor") or row.get("CPU"),
                positive_aggregate=usable,
                **resources,
            )
            for key in ("enabled_cores", "enabled_chips", "threads_per_core"):
                raw_field = {
                    "enabled_cores": ("# Cores", "# cores"),
                    "enabled_chips": ("# Chips", "# chips"),
                    "threads_per_core": ("# Enabled Threads Per Core", "# Threads Per Core"),
                }[key]
                value = next((row[k] for k in raw_field if k in row), "")
                if value and resources[key] is None:
                    anomalies.append(
                        dict(
                            context,
                            finding="invalid_resource_integer",
                            field=key,
                            raw_value=value,
                            interpretation="Review source status; never turn zero into enabled capacity.",
                        )
                    )
            cores, chips, per = [resources[k] for k in ("enabled_cores", "enabled_chips", "cores_per_chip")]
            if cores and chips and per and cores != chips * per:
                anomalies.append(
                    dict(
                        context,
                        finding="enabled_vs_chip_capacity",
                        field="cores_per_chip",
                        raw_value=per,
                        interpretation="Review disabled cores/partitions; not automatically an error.",
                    )
                )
            detail = load_disclosure(raw_dir, source, gen, track)
            if detail["status"] == "parsed":
                details.append(detail)
                hashes[detail["source_path"]] = detail["source_sha256"]
                for key, value in detail["hardware"].items():
                    if key in resources and resources[key] is not None:
                        reviews.append(
                            dict(
                                generation=gen,
                                source_url=source,
                                field=key,
                                bulk_value=resources[key],
                                detail_value=value,
                                agrees=resources[key] == value,
                                detail_sha256=detail["source_sha256"],
                                locator="Hardware: enabled",
                            )
                        )
                # Check independently rendered HTML against CSV where both are cached.
                html_path = Path(detail["source_path"]).with_suffix(".html")
                if detail["source_path"].endswith(".csv") and html_path.exists():
                    body = html_path.read_bytes()
                    html = parse_disclosure(body, ".html", gen, track)
                    for key, value in html["hardware"].items():
                        if key in detail["hardware"]:
                            reviews.append(
                                dict(
                                    generation=gen,
                                    source_url=source,
                                    field="csv_vs_html:" + key,
                                    bulk_value=detail["hardware"][key],
                                    detail_value=value,
                                    agrees=detail["hardware"][key] == value,
                                    detail_sha256=hashlib.sha256(body).hexdigest(),
                                    locator="Hardware: enabled",
                                )
                            )
                for mode, m in detail["modes"].items():
                    coverage.append(
                        dict(
                            generation=gen,
                            track=track,
                            mode=mode,
                            source_url=source,
                            status=m["status"],
                            minimum=m["minimum"],
                            maximum=m["maximum"],
                            document_url=detail["document_url"],
                            source_sha256=detail["source_sha256"],
                        )
                    )
                stats[track + "_cached_details"] += 1
                stats[track + "_details_with_runtime_count"] += bool(detail["execution"])
        summaries.append(dict(generation=gen, bulk_rows=len(rows), integer_rows=len(ints), **stats))

    # Inventory pre-bulk sources too. Their count semantics are reviewed separately.
    legacy = [
        Path("research/data/spec89/aggregate89-plus-helman.csv"),
        Path("research/data/spec89/v2.0.0/csv/bridges89_92.csv"),
        Path("research/data/spec89/v2.0.0/csv/throughput89.csv"),
        Path("research/data/spec/cpu92-dec-alpha-openvms-1992.csv"),
        Path("data/derived/spec/cpu92-rate/cpu92-rate-records.csv"),
        Path("data/derived/spec/cpu92-rate/cpu92-rate-benchmarks.csv"),
    ]
    for path in legacy:
        with path.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes[str(path)] = digest
        for field in rows[0] if rows else []:
            inventory.append(
                dict(
                    source=str(path),
                    generation="cpu89" if "spec89" in str(path) else "cpu92",
                    field=field,
                    total_rows=len(rows),
                    nonempty=sum(bool(r[field]) for r in rows),
                    current_use="legacy evidence adapter; see source contract",
                    qualification="Copies retained for CPU92 rate; legacy CPU count is not a verified socket count.",
                    source_sha256=digest,
                )
            )
    speed92, speed92_audit = collect_speed92(raw_dir)
    write_csv(research_output / "cpu92-speed-coverage.csv", speed92_audit)
    for field, usage in {
        "SPECint92 / SPECbase_int92": "speed ratios checked against six benchmark ratios; independent speed chain",
        "Number of CPUs": "stored in matching chips as legacy CPU-count proxy; physical chip equivalence not established",
        "CPU": "processor identity / clock text fallback",
        "Memory": "capacity normalized for matching; topology retained only in source",
        "OS / Compiler": "context, not general equality constraints",
        "copies / runtime threads": "no structured extraction from these speed disclosures; never inferred from CPU count",
    }.items():
        inventory.append(
            dict(
                source="data/raw/spec/cpu92/netlib/details/*.cint92.*.html",
                generation="cpu92",
                field=field,
                total_rows=len(speed92),
                current_use=usage,
                qualification="Existing speed adapter audited; see cpu92-speed-coverage.csv for each source hash",
            )
        )
    for name, rows in (
        ("field-inventory", inventory),
        ("generation-summary", summaries),
        ("resource-anomalies", anomalies),
        ("detail-crosschecks", reviews),
        ("execution-coverage", coverage),
    ):
        write_csv(research_output / (name + ".csv"), rows)
    (output / "disclosures.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in details))
    audit = dict(
        method_version="spec-resource-field-audit-v1",
        code_sha256=code_hashes(__file__),
        source_sha256=hashes,
        bulk_rows=sum(r["bulk_rows"] for r in summaries),
        cached_integer_disclosures=len(details),
        detail_crosschecks=len(reviews),
        contradictions=sum(not r["agrees"] for r in reviews),
        resource_flags=len(anomalies),
        scope="Full bulk inventory; cached integer detail extraction and bounded source review, not a census of all disclosures.",
    )
    (research_output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    click.echo(json.dumps({k: v for k, v in audit.items() if k not in ("source_sha256", "code_sha256")}))


@click.command("fetch-resources")
@click.option("--generation", "generations", type=click.Choice(GENERATIONS), multiple=True)
@click.option(
    "--track",
    type=click.Choice(("integer-speed", "integer-rate", "floating-point-speed", "floating-point-rate")),
    default="integer-rate",
    show_default=True,
)
@click.option("--raw-dir", type=click.Path(path_type=Path), default=Path("data/raw/spec"), show_default=True)
@click.option(
    "--manifest", type=click.Path(path_type=Path), default=Path("data/derived/spec/result-links.jsonl"), show_default=True
)
@click.option("--period")
@click.option("--limit", type=click.IntRange(min=1))
@click.option("--delay", type=click.FloatRange(min=0), default=0.5, show_default=True)
def fetch_resources(generations, track, raw_dir, manifest, period, limit, delay):
    """Resume speed or rate full disclosures for runtime-resource extraction."""
    collect_disclosures(manifest, raw_dir, generations or GENERATIONS, track, period, limit, delay)
