"""One single-node/system VAXen timeline from the built database, in two parallel quantities.

Rate rows (`quantity="rate"`, rate-VAXen) are SPEC92–2026 integer-rate results
through the saved rate chain. Speed rows (`quantity="speed"`, speed-VAXen, one
SPECint92 point each) are SPEC92–2026 integer-speed results through the saved
speed chain, classical results (saved classical network), SPEC89 results (saved
bridge estimates) and instruction-mix ratings (saved mix network). The two
quantities are never combined. Every row takes its year from
`result_chronology`; nothing here selects or overrides a date.
"""

import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import click
from cpushowspeed.classical.predict import predict_scores
from cpushowspeed.classical.result_store import results as classical_results
from cpushowspeed.database.curated_tables import DATABASE
from cpushowspeed.database.observation_store import connect, inputs_digest, spec_results
from cpushowspeed.research_io import code_hashes, read_csv
from cpushowspeed.spec.rate_convert import convert_rate
from cpushowspeed.spec.rate_fit import GENERATIONS
from cpushowspeed.spec.speed_chain import DERIVED as SPEED_DERIVED
from cpushowspeed.spec.speed_chain import INTERVALS as SPEED_INTERVALS
from cpushowspeed.spec.speed_chain import convert_speed
from cpushowspeed.timeline.calculator import calculator_payload
from cpushowspeed.timeline.html import render_html
from cpushowspeed.timeline.lineage import build_lineage
from cpushowspeed.timeline.mix_estimates import MIX_OUTPUT, fresh_audit, mix_rows

SCHEMA = "vaxen-timeline-v4"
CALIBRATION = Path("research/data/spec/fitting")
NETWORK = Path("data/derived/classic/network-fit")
SPEC89_ESTIMATES = Path("research/data/classic/spec89-estimates.csv")


def _month(value: str) -> str:
    """Keep the source's month precision and refuse guessed dates."""
    value = value.strip()
    if not value:
        return ""
    if re.fullmatch(r"\d{4}-\d{2}", value):
        datetime.strptime(value, "%Y-%m")
        return value
    return datetime.strptime(value, "%b-%Y").strftime("%Y-%m")


CLASSICAL_SCOPES = ("classical:%", "reviewed-vector:%")
CONTEXT_KEYS = (
    "Memory",
    "Processor Characteristics",
    "CPU(s) Orderable",
    "Parallel",
    "Auto Parallelization",
    "Base Pointer Size",
    "Peak Pointer Size",
    "Compiler",
    "Compiler Category",
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def chronology(db):
    """result_id -> the selected year, its range and every candidate, with event sources resolved to URLs."""
    urls = dict(
        db.execute(
            "SELECT e.event_id, COALESCE(s.url, '') FROM date_event e LEFT JOIN source s ON s.source_id = e.source_id"
        ).fetchall()
    )
    out = {}
    query = "SELECT result_id, date_kind, year, year_low, year_high, basis, candidates FROM result_chronology"
    for rid, kind, year, low, high, basis, candidates in db.execute(query):
        candidates = json.loads(candidates)
        known = year is not None
        out[rid] = dict(
            year=year if known else "",
            year_low=low if known else "",
            year_high=high if known else "",
            date_status="estimated" if known else "unknown",
            date_kind=kind if known else "unknown",
            date_method=basis or "unknown",
            date_sources=";".join(sorted({urls[c["event_id"]] for c in candidates if urls.get(c.get("event_id"))})),
            date_notes="",
            date_candidates=candidates,
        )
    return out


def runtime(result, mode, raw, track):
    """Declared rate copies or speed threads and hardware context; topology is never inferred."""
    detail = dict(track=track, quantity="copies" if track == "rate" else "threads", status="not_collected")
    fields = dict(
        cores_per_chip=raw.get("# Cores Per Chip") or raw.get("# cores per chip") or "",
        resource_basis="reported enabled hardware; not benchmark concurrency",
        hardware_context={k: v for k, v in raw.items() if v and ("Cache" in k or k in CONTEXT_KEYS)},
    )
    if result.generation == "cpu92" and track == "rate":
        lo, hi = raw.get(mode + "_copies_min"), raw.get(mode + "_copies_max")
        fields.update(
            resource_basis="legacy reported CPU count; chip equivalence unverified", reported_cpu_count=raw.get("cpu_count")
        )
        detail.update(status="reported" if lo else "not_reported_in_parsed_table", minimum=lo, maximum=hi)
    elif result.generation == "cpu92":
        fields.update(
            resource_basis="legacy reported CPU count; chip equivalence unverified", reported_cpu_count=raw.get("cpu_count")
        )
    elif mode in result.execution.get("modes", {}):
        detail.update(
            result.execution["modes"][mode],
            source_url=result.execution.get("document_url"),
            source_sha256=result.execution.get("source_sha256"),
            benchmarks=[b for b in result.execution.get("execution", []) if b.get("mode") == mode],
        )
    try:
        if int(result.cores or 0) > int(result.chips or 0) * int(fields["cores_per_chip"]):
            fields["resource_warning"] = "Source reports more enabled cores than chip capacity; topology requires review."
    except (ValueError, TypeError):
        pass
    fields["runtime_resources"] = detail
    if detail["status"] == "reported":
        fields.update(copies_min=detail.get("minimum") or "", copies_max=detail.get("maximum") or "")
    return fields


def spec_rows(db, dates, digest):
    """Every SPEC92–2026 integer result: rate through the rate chain, speed through the speed chain."""
    fresh_audit(
        SPEED_DERIVED / "integer-speed-chain.json", digest, "database_inputs_sha256", {str(SPEED_INTERVALS): sha(SPEED_INTERVALS)}
    )

    @lru_cache(None)
    def unit(track, generation, mode):
        if track == "speed":
            u = convert_speed(generation, mode, 1)
            return dict(vaxen=u["vaxen"], ci95=u["ci95"], uncertainty_scope=u["scope"])
        return convert_rate(generation, mode, 1, "same_os", CALIBRATION)

    rows = []
    for track in ("rate", "speed"):
        chain = "integer-rate chain → CPU92 rate" if track == "rate" else "integer-speed chain → SPECint92 speed"
        for generation in ("cpu92", *GENERATIONS):
            for result in spec_results(db, generation, track):
                raw = result.raw_fields
                rid = f"spec:{generation}:{track}:{result.result_id}"
                for mode in ("base", "peak"):
                    score = result.base if mode == "base" else result.peak
                    if score is None:
                        continue
                    u = unit(track, generation, mode)
                    benchmark = raw.get(f"{mode}_metric") or raw.get("Benchmark", "")
                    if generation == "cpu92" and track == "speed":
                        benchmark = "SPECint92" if mode == "peak" else "SPECbase_int92"
                    cid = (
                        f"spec:{generation}:{result.result_id}:{mode}"
                        if track == "rate"
                        else f"spec:{generation}:speed:{result.result_id}:{mode}"
                    )
                    defined = generation == "cpu92" and track == "speed"
                    row = dict(
                        record_id=cid,
                        configuration_id=cid,
                        result_id=rid,
                        route=generation.upper(),
                        generation=generation,
                        mode=mode,
                        quantity=track,
                        system=result.system,
                        system_id=result.system_key,
                        cpu=result.processor,
                        clock_mhz=result.clock_mhz or "",
                        os=result.os,
                        configuration="",
                        scores={benchmark: score},
                        reported_score=score,
                        benchmark_id=benchmark,
                        observation_count=1,
                        source_record_ids=[rid],
                        source_url=result.source_url,
                        benchmark_sources=[result.source_url],
                        source_container_sha256=result.source_container_sha256,
                        vaxen=score * u["vaxen"],
                        ci95_low=score * u["ci95"]["low"],
                        ci95_high=score * u["ci95"]["high"],
                        evidence_class=("reported_speed_defined_scale" if defined else f"reported_{track}_normalized_estimate"),
                        uncertainty_scope=u["uncertainty_scope"],
                        calibration_route="SPECint92 speed = speed-VAXen" if defined else generation.upper() + " " + chain,
                        calibration_scenario="same_os" if track == "rate" else "hardware_near",
                        measurement_scope="reported_system_rate" if track == "rate" else "reported_single_job_speed",
                        chips=result.chips or "",
                        cores=result.cores or "",
                        threads_per_core=result.enabled_threads_per_core or "",
                        copies_min="",
                        copies_max="",
                        nodes="",
                        limitation="Experimental CPU2026 calibration; sparse overlap." if generation == "cpu2026" else "",
                        hardware_date=_month(raw.get("HW Avail") or raw.get("hardware_availability_month") or ""),
                        submission_date=_month(raw.get("Published") or raw.get("publication_month") or ""),
                        test_date=_month(raw.get("Test Date") or raw.get("test_month") or ""),
                    )
                    row.update(runtime(result, mode, raw, track))
                    row.update(dates[rid])
                    rows.append(row)
    return rows


def classical_rows(db, dates):
    """Each classical result with one reported (or unreported) CPU, predicted from all its classical scores."""
    rows = []
    for r in classical_results(db, CLASSICAL_SCOPES):
        if not r.classical or r.cpu_count not in (None, 1):
            continue
        p = predict_scores(r.classical, NETWORK)
        raw = r.raw.get("raw_record") if isinstance(r.raw.get("raw_record"), dict) else r.raw
        rows.append(
            dict(
                record_id=r.result_id,
                configuration_id=r.result_id,
                result_id=r.result_id,
                route="classical",
                generation="classical",
                mode="peak_proxy",
                quantity="speed",
                system=r.system,
                system_id=r.system_id,
                cpu=str(raw.get("processor_raw") or ""),
                clock_mhz=r.clock_mhz or "",
                os=r.os,
                configuration=str(raw.get("configuration_raw") or ""),
                scores=dict(r.classical),
                reported_score=None,
                benchmark_id="classical composite",
                observation_count=len(r.classical),
                source_record_ids=sorted(r.observation_ids.values()),
                source_url=r.source_url,
                benchmark_sources=[r.source_url],
                vaxen=p["vaxen"],
                ci95_low=p["vaxen_ci95"]["low"],
                ci95_high=p["vaxen_ci95"]["high"],
                evidence_class="model_prediction_not_reported_SPEC_result",
                uncertainty_scope="conditional_calibration_CI95_not_machine_prediction_interval",
                calibration_route="classical network → SPECint92 speed",
                calibration_scenario="linear_clock / with_spec89",
                measurement_scope="historical_one_processor_proxy",
                chips=r.cpu_count or "",
                limitation="Historical proxy; CPU count may be unknown.",
                **dates[r.result_id],
            )
        )
    return rows


def spec89_rows(dates):
    rows = []
    for r in read_csv(SPEC89_ESTIMATES):
        rows.append(
            dict(
                record_id=r["spec_id"],
                configuration_id=r["spec_id"],
                result_id=r["spec_id"],
                route="SPEC89",
                generation="cpu89",
                mode="peak_proxy",
                quantity="speed",
                system=r["system"],
                system_id=r["system_id"],
                cpu="",
                clock_mhz="",
                os="",
                configuration="",
                scores={"SPECint89": float(r["raw_specint89"])},
                reported_score=float(r["raw_specint89"]),
                benchmark_id="SPECint89",
                observation_count=1,
                source_record_ids=[r["spec_id"]],
                source_url=r["source_url"],
                benchmark_sources=[r["source_url"]],
                vaxen=float(r["estimated_speed_vaxen"]),
                ci95_low=float(r["factor_ci95_target_low"]),
                ci95_high=float(r["factor_ci95_target_high"]),
                evidence_class=r["evidence_class"],
                uncertainty_scope="conditional_bridge_factor_CI95_not_machine_prediction_interval",
                calibration_route="SPECint89 → SPECint92 speed",
                calibration_scenario="int89_to_int92 bridge",
                measurement_scope="historical_one_processor_proxy",
                limitation="Bridge estimate, not a SPECint92 measurement.",
                **dates[r["spec_id"]],
            )
        )
    return rows


@click.command("timeline")
@click.option("--database", type=click.Path(path_type=Path, dir_okay=False), default=DATABASE, show_default=True)
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("data/derived/figures/timeline"), show_default=True)
def timeline_command(database, output_dir):
    """Combine SPEC92–2026 rate and speed results, classical, SPEC89 and mix estimates, dated by result_chronology."""
    try:
        with connect(database) as db:
            digest = inputs_digest(db)
            dates = chronology(db)
            modern = spec_rows(db, dates, digest)
            classical = classical_rows(db, dates)
        historical = spec89_rows(dates)
        mixes, mix_audit = mix_rows(dates, digest)
        rows = modern + classical + historical + mixes
        for row in rows:
            row["schema_version"] = SCHEMA
            row.setdefault("estimate_kind", "baseline")
        if len({r["record_id"] for r in rows}) != len(rows):
            raise ValueError("duplicate timeline record")
        output_dir.mkdir(parents=True, exist_ok=True)
        lineage = build_lineage(output_dir / "vaxen-timeline.html")
        calculator, calculator_hashes = calculator_payload()
        lineage["input_sha256"].update(calculator_hashes)
        render_html(rows, output_dir / "vaxen-timeline.html", lineage=lineage, calculator=calculator)
        audit = dict(
            schema_version=SCHEMA,
            database=str(database),
            inputs_sha256=digest,
            web_manifest_sha256=sha(output_dir / "manifest.json"),
            lineage_inputs_sha256=lineage["input_sha256"],
            records=len(rows),
            spec_rate=sum(r["quantity"] == "rate" for r in modern),
            spec_speed=sum(r["quantity"] == "speed" for r in modern),
            classical=len(classical),
            spec89=len(historical),
            estimates=dict(Counter(r["estimate_kind"] for r in rows)),
            dates=dict(Counter(r["date_kind"] for r in rows)),
            routes=dict(Counter(r["route"] for r in rows)),
            quantities=dict(Counter(r["quantity"] for r in rows)),
            modes=dict(Counter(r["mode"] for r in rows)),
            chronology="result_chronology: CPU release → hardware → reviewed fallback → publication",
            cpu92_anchor_software_policy="same_os",
            scope="single node/system; rate-VAXen is throughput (all copies), speed-VAXen is one job; no per-core normalization",
            units=dict(
                rate="rate-VAXen: SPECrate_int92 x 25500/604800 (VAX-11/780 = 1)",
                speed="speed-VAXen: SPECint92 speed (VAX-11/780 = 1, SPEC92 reference machine)",
            ),
            limitations=[
                "Rate and speed are parallel quantities; neither is converted into the other.",
                "Classical, SPEC89 and mix rows are speed estimates, not SPECint92 measurements.",
                "Reported cluster submissions retained; node count is not inferred from system name or chip count.",
                "Copies missing from bulk exports remain blank.",
                "Mix rows are model predictions correlated with the classical route, not extra evidence.",
            ],
            estimate_bundles=dict(mix_network=mix_audit["method"]),
            inputs_file_sha256={
                str(p): sha(p)
                for p in [
                    SPEC89_ESTIMATES,
                    NETWORK / "prediction-calibration.json",
                    MIX_OUTPUT / "mix-estimates.csv",
                    SPEED_INTERVALS,
                    CALIBRATION / "integer-rate-chain-intervals.csv",
                    CALIBRATION / "integer-rate-cpu92-vaxen-chain.csv",
                ]
            },
            code_sha256=code_hashes(Path(__file__)),
        )
        (output_dir / "audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n")
        click.echo(
            json.dumps({k: audit[k] for k in ["records", "spec_rate", "spec_speed", "classical", "spec89", "estimates", "dates"]})
        )
    except (OSError, ValueError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc
