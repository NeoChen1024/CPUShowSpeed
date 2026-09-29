"""Source-preserving adapters for a common single-node/system VAXen timeline."""

import hashlib
import json
import math
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

import click
from cpushowspeed.annual_rate import collect_annual_records
from cpushowspeed.mix_timeline import mix_records
from cpushowspeed.rate_convert import convert_rate
from cpushowspeed.research_io import code_hashes, read_csv, write_csv
from cpushowspeed.spec_inputs import collect_cpu92_rate, collect_integer
from cpushowspeed.spec_overlap import _checked_bulk, _frequency, _source_url
from cpushowspeed.timeline_calculator import calculator_payload, rate_edge_metadata
from cpushowspeed.timeline_dates import CPUChronology, candidate, select_date
from cpushowspeed.timeline_estimates import extend_estimates
from cpushowspeed.timeline_html import render_html
from cpushowspeed.timeline_lineage import build_lineage
from cpushowspeed.timeline_resources import resource_fields

SCHEMA = "vaxen-timeline-v2"
HISTORICAL = Path("data/derived/classic/historical-timeline")
RAW = Path("data/raw/spec")
CPU92 = Path("data/derived/spec/cpu92-rate/cpu92-rate-records.csv")
CALIBRATION = Path("research/data/spec/fitting")
FIT = Path("data/derived/spec/fitting")
SUBMISSION_REVIEWS = Path("research/data/historical/submission-date-reviews.csv")
PROXIES = Path("research/data/historical/cpu-release-proxies.csv")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def historical_records(chronology):
    audit = json.loads((HISTORICAL / "audit.json").read_text())
    for name, digest in audit["input_sha256"].items():
        if sha(Path(name)) != digest:
            raise ValueError("stale historical input; regenerate classic historical-timeline: " + name)
    observations = defaultdict(list)
    for r in read_csv(HISTORICAL / "observations.csv"):
        observations[r["configuration_id"]].append(r)
    rows = []
    for original in read_csv(HISTORICAL / "configurations.csv"):
        row = dict(original)
        for key in ("vaxen", "ci95_low", "ci95_high"):
            row[key] = float(row[key])
        obs = observations[row["configuration_id"]]
        dates = chronology.lookup(row)
        if original.get("date_candidates"):
            dates.extend(json.loads(original["date_candidates"]))
        else:
            kind = "cpu" if original["date_method"] == "reviewed_cpu_release_year_proxy" else "hardware"
            dates.append(
                candidate(
                    kind,
                    original["year"],
                    original["date_sources"],
                    original["date_method"],
                    original["date_notes"],
                    original["year_low"],
                    original["year_high"],
                )
            )
        row["scores"] = json.loads(row["scores"])
        row["observation_count"] = int(row["observation_count"])
        counts = set()
        for ob in obs:
            raw = json.loads(ob["provenance"])
            n = raw.get("reported_processor_count") or raw.get("cpu_count")
            if n is not None:
                counts.add(str(n))
            # Explicit result-publication metadata only, never source document/download dates.
            payload = raw.get("raw_record", {})
            if isinstance(payload, dict):
                d = payload.get("publication_month") or payload.get("submission_date")
                dates.append(candidate("submission", d, ob["source_url"], "reported_submission_date"))
        row.update(
            schema_version=SCHEMA,
            record_id="historical:" + row["configuration_id"],
            generation="classical" if row["route"] == "classical" else "cpu89",
            mode="peak_proxy",
            reported_score=None,
            benchmark_id="classical composite" if row["route"] == "classical" else "SPECint89",
            calibration_route=(
                "classical network → CPU92 rate" if row["route"] == "classical" else "SPEC89 → SPEC92 speed → SPEC92 rate"
            ),
            calibration_scenario="historical_saved_model",
            measurement_scope="historical_one_processor_proxy",
            chips=";".join(sorted(counts)),
            cores="",
            threads_per_core="",
            copies_min="",
            copies_max="",
            nodes="",
            source_record_ids=sorted({r["observation_id"] for r in obs}),
            benchmark_sources=sorted({r["source_url"] for r in obs}),
            limitation="Historical proxy; CPU count may be unknown.",
        )
        row.update(select_date(dates))
        rows.append(row)
    return rows


def spec_records(chronology):
    records, provenance = collect_annual_records(RAW, CPU92, CALIBRATION, FIT)
    normalized = {(item.generation, item.source_url): item for group in collect_integer(RAW, "rate").values() for item in group}
    normalized.update({("cpu92", item.source_url): item for item in collect_cpu92_rate(CPU92, RAW)})

    @lru_cache(None)
    def unit(gen, mode):
        return convert_rate(gen, mode, 1, "same_os", CALIBRATION)

    rows = []
    for r in records:
        gen, mode = r["generation"], r["mode"]
        source_record = normalized[gen, r["source_url"]]
        src = source_record.raw_fields
        u = unit(gen, mode)
        v = float(r["reported_score"]) * u["vaxen"]
        if not math.isclose(v, float(r["vaxen_same_os"]), rel_tol=1e-12):
            raise ValueError("annual and saved rate calibration disagree")
        cid = "spec:" + gen + ":" + r["result_id"] + ":" + mode
        row = dict(
            schema_version=SCHEMA,
            record_id=cid,
            configuration_id=cid,
            route=gen.upper(),
            generation=gen,
            mode=mode,
            system=r["system"],
            cpu=r["processor"],
            clock_mhz=source_record.clock_mhz or "",
            os=source_record.os,
            configuration="",
            scores={r["benchmark_id"]: r["reported_score"]},
            reported_score=r["reported_score"],
            benchmark_id=r["benchmark_id"],
            observation_count=1,
            source_record_ids=[r["result_id"]],
            source_url=r["source_url"],
            benchmark_sources=[r["source_url"]],
            source_container_sha256=r["source_container_sha256"],
            vaxen=v,
            ci95_low=float(r["reported_score"]) * u["ci95"]["low"],
            ci95_high=float(r["reported_score"]) * u["ci95"]["high"],
            evidence_class="reported_rate_normalized_estimate",
            uncertainty_scope=u["uncertainty_scope"],
            calibration_route=gen.upper() + " integer-rate chain → CPU92 rate",
            calibration_scenario="same_os",
            measurement_scope="reported_system_rate",
            chips=r["chips"],
            cores=source_record.cores or "",
            threads_per_core=source_record.enabled_threads_per_core or "",
            copies_min=src.get(mode + "_copies_min", ""),
            copies_max=src.get(mode + "_copies_max", ""),
            nodes="",
            limitation="Experimental CPU2026 calibration; sparse overlap." if gen == "cpu2026" else "",
            hardware_date=r["hardware_availability_month"],
            submission_date=r["publication_month"],
            test_date=r["test_month"],
        )
        row.update(resource_fields(row, src, "rate"))
        # Do not equate socket/core/thread/copy counts; bulk exports usually omit copies.
        row.update(
            select_date(
                chronology.lookup(row)
                + [
                    candidate("hardware", r["hardware_availability_month"], r["source_url"], "reported_hardware_availability"),
                    candidate(
                        "submission",
                        r["publication_month"],
                        r["source_url"],
                        "reported_result_publication",
                        "Publication date used as submission-era proxy; submission receipt date is unavailable.",
                    ),
                ]
            )
        )
        rows.append(row)
    return rows, provenance


@click.command("timeline")
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("data/derived/figures/timeline"), show_default=True)
def timeline_command(output_dir):
    """Combine historical proxies and every available SPEC92–2026 rate submission; no fitting."""
    try:
        chronology = CPUChronology(read_csv(PROXIES))
        historical = historical_records(chronology)
        modern, provenance = spec_records(chronology)
        mixes, mix_provenance = mix_records(chronology, SCHEMA)
        rows = historical + modern + mixes
        reviews = read_csv(SUBMISSION_REVIEWS)
        by_id = {r["record_id"]: r for r in rows}
        if len({r["record_id"] for r in reviews}) != len(reviews):
            raise ValueError("duplicate submission date review")
        for review in reviews:
            if not review["reason"] or not review["source_url"] or not review["reviewed_on"]:
                raise ValueError("submission date review needs reason, source and review date")
            if review["record_id"] not in by_id:
                raise ValueError("unknown submission review record: " + review["record_id"])
            row = by_id[review["record_id"]]
            row.update(select_date(row["date_candidates"], review))

        estimates, estimate_provenance, estimate_bundles = extend_estimates(modern, chronology, SCHEMA)
        rows += estimates
        assert len({r["record_id"] for r in rows}) == len(rows)
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "records.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False, allow_nan=False) + "\n" for r in rows))
        write_csv(
            output_dir / "records.csv",
            [{k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in r.items()} for r in rows],
        )

        lineage = build_lineage(output_dir / "vaxen-timeline.html")
        lineage["rate_edges"], edge_hashes = rate_edge_metadata(estimate_bundles)
        lineage["input_sha256"].update(edge_hashes)
        calculator, calculator_hashes = calculator_payload(estimate_bundles)
        lineage["input_sha256"].update(calculator_hashes)
        lineage["experiments"] = {}
        plot_fields = ("new_generation", "mode", "model_key", "speed_score", "rate_score", "target_rate")
        for policy, b in estimate_bundles.items():
            # Coincident tuples share a mark, with multiplicity; all raw tuples remain in the evidence CSV.
            counts = Counter(tuple(r[k] for k in plot_fields) for r in b[2])
            lineage["experiments"][policy] = dict(
                fits=list(b[0].values()),
                triples=[dict(zip(plot_fields, values), count=count) for values, count in counts.items()],
            )
        render_html(rows, output_dir / "vaxen-timeline.html", lineage=lineage, calculator=calculator)
        audit = dict(
            schema_version=SCHEMA,
            lineage_inputs_sha256=lineage["input_sha256"],
            records=len(rows),
            experimental_estimates=len(estimates),
            estimate_inputs_sha256=estimate_provenance,
            historical=len(historical),
            spec_rate=len(modern),
            instruction_mix=len(mixes),
            mix_provenance=mix_provenance,
            dates=dict(Counter(r["date_kind"] for r in rows)),
            routes=dict(Counter(r["route"] for r in rows)),
            modes=dict(Counter(r["mode"] for r in rows)),
            year_priority=["cpu", "hardware", "submission", "unknown"],
            submission_date_reviews=len(reviews),
            rejected_submission_dates=sum(r["decision"] == "reject" for r in reviews),
            scenario="ram-aliases",
            cpu92_anchor_software_policy="same_os",
            scope="single-node/system throughput; no per-core normalization",
            limitations=[
                "Historical calibration remains one-processor-conditioned; excluded multi-processor historical scores were not synthesized.",
                "Reported cluster submissions retained; node count is not inferred from system name or chip count.",
                "CPU chronology coverage is limited to reviewed identities. Copies missing from bulk remain blank.",
            ],
            source_provenance=provenance,
            inputs_sha256={
                str(p): sha(p)
                for p in [
                    PROXIES,
                    SUBMISSION_REVIEWS,
                    HISTORICAL / "configurations.csv",
                    HISTORICAL / "observations.csv",
                    CALIBRATION / "integer-rate-chain-intervals.csv",
                    CALIBRATION / "integer-rate-cpu92-vaxen-chain.csv",
                ]
            },
            code_sha256=code_hashes(Path(__file__)),
        )
        (output_dir / "audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n")
        click.echo(
            json.dumps(
                {k: audit[k] for k in ["records", "historical", "spec_rate", "instruction_mix", "dates", "modes"]},
                ensure_ascii=False,
            )
        )
    except (OSError, ValueError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc
