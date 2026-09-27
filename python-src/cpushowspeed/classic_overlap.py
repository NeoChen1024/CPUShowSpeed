"""Reproducible hardware-overlap discovery, not cross-workload calibration."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import blake3
import click
from bs4 import BeautifulSoup
from cpushowspeed.research_io import read_csv as shared_read_csv
from cpushowspeed.research_io import write_csv as shared_write_csv

METHOD = "classic-hardware-overlap-v1"


def read_csv(path):
    return shared_read_csv(path, encoding="utf-8-sig")


def number(text):
    text = str(text).strip()
    return float(text) if re.fullmatch(r"\d+(?:\.\d*)?", text) else None


def vendor_name(s):
    s = s.strip()
    lower = s.lower()
    for prefix, canonical in [
        ("digital equipment", "DEC"),
        ("hewlett-packard", "HP"),
        ("hewlett packard", "HP"),
        ("silicon graphics", "SGI"),
        ("sun microsystems", "Sun"),
        ("ibm corporation", "IBM"),
        ("dell computer", "Dell"),
        ("compaq computer", "Compaq"),
        ("data general", "Data General"),
    ]:
        if lower.startswith(prefix):
            return canonical
    return {"digital": "DEC"}.get(lower, s)


def full_name(vendor, model):
    vendor = vendor_name(vendor)
    model = re.sub(r"^Digital\b", "DEC", model, flags=re.I)
    model = re.sub(r"^Hewlett[- ]Packard(?: Company)?\b", "HP", model, flags=re.I)
    if not vendor or model.lower().startswith(vendor.lower()):
        return model.strip()
    return vendor + " " + model.strip()


@lru_cache(maxsize=10000)
def model_key(name):
    """Typographic/model syntax normalization; preserve numeric suffixes/variants."""
    s = name.lower().strip().replace("+", " plus ")
    s = s.replace("hewlett-packard", "hp").replace("hewlett packard", "hp").replace("silicon graphics", "sgi")
    s = re.sub(r"^digital\b", "dec", s)
    s = re.sub(r"\bvaxstn\b", "vaxstation", s)
    s = re.sub(r"\bdecstn\b", "decstation", s)
    s = re.sub(r"^dec\s+(decstation|decsystem|alphaserver)", r"\1", s)
    s = re.sub(r"^(vax|microvax)\b", r"dec \1", s)
    s = re.sub(r"^sparcstation", "sun sparcstation", s)
    s = re.sub(r"\bsparc\s+station\b", "sparcstation", s)
    s = re.sub(r"\bmodel\b|\baxp\b", " ", s)
    s = re.sub(r"\bsgi\s+iris\b", "sgi", s)
    s = re.sub(r"\bhp\s+9000\s+series\s+\d+\s*", "hp 9000 ", s)
    s = re.sub(r"\bibm\s+(?:rs\s*/?\s*)?6000\b", "ibm rs6000", s)
    # Options stay in source conditions; dropping them only permits model candidates.
    s = re.sub(r"\b(?:fpa|nof|fpu|fpp|eae|eau)\b", " ", s)
    s = re.sub(r"\b\d+\s*(?:cp|cpu|cpus)\b", " ", s)
    return re.sub(r"[^a-z0-9]", "", s)


@lru_cache(maxsize=10000)
def relaxed_key(name, clock):
    """One explicit relaxation: HP /clock suffix when corroborated by MHz."""
    s = name
    parenthesized = re.search(r"\s+\((\d+(?:\.\d+)?)\)\s*$", s)
    if parenthesized and clock is not None and abs(float(parenthesized[1]) - clock) < 0.01:
        s = s[: parenthesized.start()]
    if re.search(r"\bhp\b", s, re.I):
        m = re.search(r"(\d{3})/(\d+(?:\.\d+)?)\s*$", s)
        if m and clock is not None and abs(float(m[2]) - clock) < 0.01:
            s = s[: m.start()] + m[1]
    return model_key(s)


def source_pre(source):
    return {b["pre_index"]: b["text"] for b in source["blocks"] if b["kind"] == "preformatted"}


def base_record(source, family, locator, raw, model, vendor="", scope="system"):
    meta = source["source"]
    identity = f"{meta['source_id']}:{locator}"
    return dict(
        id=identity,
        source_id=meta["source_id"],
        source_url=meta["url"],
        source_blake3=meta["blake3"],
        lineage=meta["lineage"],
        benchmark=family,
        locator=locator,
        raw_record=raw,
        model_raw=model,
        system=full_name(vendor, model),
        identity_scope=scope,
        clock_mhz=None,
        processor_raw="",
        os_raw="",
        configuration_raw="",
        metrics_raw={},
        verification="source_layout_checked_not_individually_verified",
        fit_eligible=False,
    )


def parse_dhrystone(source):
    records = []
    rejected = []
    text = source_pre(source)[0]
    for line_number, line in enumerate(text.splitlines(), 1):
        if not re.match(r"^\d{3}\s", line):
            continue
        r = base_record(source, "Dhrystone", f"pre:0:line:{line_number}", line, line[4:26].strip())
        tail = line[51:].split()
        if len(tail) != 4:
            rejected.append(
                {"source_id": r["source_id"], "locator": r["locator"], "raw": line, "reason": "unexpected numeric tail"}
            )
            continue
        r.update(
            os_raw=line[26:39].strip(),
            processor_raw=line[39:51].strip(),
            clock_mhz=number(tail[0]),
            metrics_raw={"v1.1_DMIPS": tail[1], "v2.1_DMIPS": tail[2]},
            configuration_raw="reference " + tail[3],
            source_row_id=line[:3],
            reference_raw=tail[3],
        )
        if re.match(r"^(?:Pentium|Mac PowerPC|AMD|Cyrix)\b", r["model_raw"], re.I):
            r["identity_scope"] = "cpu_only"
        if not any(number(v.rstrip("*")) is not None for v in r["metrics_raw"].values()):
            rejected.append(
                {"source_id": r["source_id"], "locator": r["locator"], "raw": line, "reason": "score columns not understood"}
            )
        else:
            records.append(r)
    return records, rejected


def parse_whetstone(source):
    records = []
    rejected = []
    vendor = ""
    text = source_pre(source)[2]
    for n, line in enumerate(text.splitlines(), 1):
        if line.startswith("PCs (Precision"):
            break
        if line.strip().startswith("Then "):
            continue
        name = line[:15].strip()
        mw = line[34:42].strip()
        dp = line[58:66].strip()
        if not name or name in {"Supplier or", "System", "To Index"}:
            continue
        if number(mw) is None and number(dp) is None:
            tail = line[15:].strip()
            if not tail or re.fullmatch(r"P\d+", tail):
                vendor = name
            elif name and number(line[28:34]) is not None:
                rejected.append(
                    {
                        "source_id": source["source"]["source_id"],
                        "locator": f"pre:2:line:{n}",
                        "raw": line,
                        "reason": "no recognized MWIPS field",
                    }
                )
            continue
        if not vendor:
            raise ValueError("Whetstone data before supplier heading")
        r = base_record(source, "Whetstone", f"pre:2:line:{n}", line, name, vendor)
        if re.match(r"^(?:Pentium|AMD|Cyrix|Intel|Athlon|Celeron|Core|80486)\b", name, re.I):
            r["identity_scope"] = "cpu_only"
        r.update(
            clock_mhz=number(line[28:34]),
            processor_raw=line[15:28].strip(),
            configuration_raw=" | ".join([line[15:28].strip(), line[66:73].strip(), line[73:78].strip()]),
            metrics_raw={"MWIPS": mw, "MWIPS_DP": dp, "MFLOPS_aux": line[42:50].strip(), "VAX_MIPS_aux": line[50:58].strip()},
            language_raw=line[66:73].strip(),
            optimization_raw=line[73:78].strip(),
            introduction_year_raw=line[84:].strip(),
        )
        records.append(r)
    return records, rejected


def parse_mixes(source):
    records = []
    # Raw HTML preserves every source row, even rows without any score.
    soup = BeautifulSoup(source["blocks"][0]["html"], "html.parser")
    for index, row in enumerate(soup.find_all("tr")):
        cells = row.find_all(["td", "th"], recursive=False)
        if len(cells) != 8 or any(c.find("table") for c in cells):
            continue
        v = [c.get_text(" ", strip=True) for c in cells]
        if v[0] == "Manufacturer" or not v[0] or not v[1]:
            continue
        for family, score in [("Gibson Mix", v[5]), ("ADP Mix", v[6])]:
            r = base_record(source, family, f"table:0:tr:{index}:{family}", v, v[1], v[0])
            r.update(
                configuration_raw=" | ".join(v[2:5]),
                metrics_raw={"KIPS": score},
                introduction_year_raw=v[7],
                evidence_kind="instruction_mix_estimate",
                has_reported_score=bool(score and score != "-"),
            )
            records.append(r)
    return records, []


def parse_pc(source, family):
    records = []
    # The pages primarily identify CPUs, not complete tested systems.
    names = r"(?:AMD|Intel|Pentium|Core|Cyrix|IBM|80486|Athlon|Duron|Celeron|Atom|Cray|ARM|Raspberry|Opteron|Phenom|Turion|Apple|PIII|P4|Samsung|Tegra)\b"
    for pi, text in source_pre(source).items():
        for n, line in enumerate(text.splitlines(), 1):
            if not re.match(names, line.strip(), re.I):
                continue
            m = re.match(r"^(.+?)\s{2,}(\d+(?:\.\d+)?|[@#$&*]+\d*)\s+([\d.].*)$", line)
            if not m:
                continue
            r = base_record(source, family, f"pre:{pi}:line:{n}", line, m[1].strip(), scope="cpu_only")
            r.update(processor_raw=m[1].strip(), clock_mhz=number(m[2]), metrics_raw={"uninterpreted_columns": m[3]})
            records.append(r)
    return records, []


def parse_linpack_pdf(meta):
    data = Path(meta["blob_path"]).read_bytes()
    if blake3.blake3(data).hexdigest() != meta["blake3"]:
        raise ValueError("LINPACK PDF hash mismatch")
    result = subprocess.run(["pdftotext", "-layout", meta["blob_path"], "-"], check=True, capture_output=True)
    text = result.stdout.decode("utf-8")
    source = {"source": meta}
    records = []
    active = False
    for page_number, page in enumerate(text.split("\f"), 1):
        if re.search(r"^\s*Table 2:", page, re.M):
            break
        if re.search(r"^\s*Table 1:", page, re.M):
            active = True
        if not active:
            continue
        for line_number, line in enumerate(page.splitlines(), 1):
            fields = re.split(r"\s{2,}", line.strip())
            if len(fields) < 2 or not re.match(r"[A-Za-z]", fields[0]) or not re.search(r"\d", fields[0]):
                continue
            # At least one separated numeric result; no interpretation of n=100/n=1000/peak.
            if not any(re.fullmatch(r"(?:\d+(?:\.\d*)?|\.\d+)", f) for f in fields[1:]):
                continue
            model = fields[0]
            clock = re.search(r"(\d+(?:\.\d+)?)\s*MHz", model, re.I)
            count = re.search(r"(\d+)\s*proc", model, re.I)
            clean = re.sub(r"\([^)]*\)", lambda m: " " if re.search(r"MHz|\bns\b|\bproc", m[0], re.I) else m[0], model)
            clean = re.sub(r"\b\d+(?:\.\d+)?\s*(?:MHz|ns)\b", " ", clean, flags=re.I)
            clean = re.sub(r"\bAlpha AXP\b", "AXP", clean, flags=re.I)
            r = base_record(source, "LINPACK", f"pdf:page:{page_number}:line:{line_number}", line, clean.strip())
            r.update(
                clock_mhz=float(clock[1]) if clock else None,
                configuration_raw=model,
                metrics_raw={"table1_uninterpreted_columns": fields[1:]},
                verification="unreviewed_pdf_layout_candidate",
                text_extraction_sha256=hashlib.sha256(result.stdout).hexdigest(),
                reported_processor_count=int(count[1]) if count else None,
            )
            records.append(r)
    return records, []


def parse_classics(acquisition):
    parsers = {
        "netlib-dhrystone-results": parse_dhrystone,
        "longbottom-whetstone-history": parse_whetstone,
        "longbottom-cpumix": parse_mixes,
    }
    pc = {
        "longbottom-whetstone-results": "Whetstone",
        "longbottom-dhrystone-results": "Dhrystone",
        "longbottom-linpack-results": "LINPACK",
        "longbottom-livermore-results": "Livermore",
    }
    records = []
    rejected = []
    coverage = []
    for meta in read_csv(acquisition):
        sid = meta["source_id"]
        entry = {
            "source_id": sid,
            "role": meta["role"],
            "status": "not_parsed_for_hardware",
            "records": 0,
            "section_scope": "not yet parsed",
        }
        if sid == "netlib-linpack-report":
            rs, es = parse_linpack_pdf(meta)
            records += rs
            rejected += es
            entry.update(
                status="pdf_machine_candidate_rows",
                records=len(rs),
                section_scope="Table 1 lines with a separated numeric result; no multiline reconstruction or score interpretation",
            )
        elif sid in parsers or sid in pc:
            data = Path(meta["blob_path"]).read_bytes()
            if blake3.blake3(data).hexdigest() != meta["blake3"]:
                raise ValueError(f"source hash mismatch: {sid}")
            source = json.loads(Path(meta["extraction_path"]).read_text())
            if source["source"]["blake3"] != meta["blake3"]:
                raise ValueError("derived source hash mismatch")
            rs, es = parsers[sid](source) if sid in parsers else parse_pc(source, pc[sid])
            records += rs
            rejected += es
            entry.update(
                status="system_rows_parsed" if sid in parsers else "cpu_only_rows_parsed",
                records=len(rs),
                section_scope=(
                    "pre 2 historical supplier table; stops at PCs (Precision)"
                    if sid == "longbottom-whetstone-history"
                    else (
                        "explicit PRE row grammar"
                        if sid in pc or sid == "netlib-dhrystone-results"
                        else "eight-column instruction-mix rows"
                    )
                ),
            )
        elif meta["role"] in {
            "source_code",
            "source_or_executable_archive",
            "index",
            "result_index",
            "result_and_method_index",
            "original_suite_description",
        }:
            entry["status"] = "program_or_navigation_not_result_population"
        coverage.append(entry)
    return records, rejected, coverage


def load_specs():
    records = []
    for r in read_csv("research/data/spec89/aggregate89-plus-helman.csv"):
        records.append(
            dict(
                id="spec89:" + r["record_id"],
                cohort="SPEC89 aggregate",
                system=r["system_normalized"],
                source_url=r["source_url"],
                clock_mhz=number(r["clock_MHz_raw"]),
                processor_raw=r["cpu_raw"],
                os_raw=r["operating_system"],
                cpu_count=None,
                evidence_class=r["evidence_class"],
                metrics_raw={k: r[k] for k in ["SPECmark89", "SPECint89", "SPECfp89"]},
                raw_record=r,
            )
        )
    for r in read_csv("research/data/spec89/v2.0.0/csv/throughput89.csv"):
        records.append(
            dict(
                id="spec89-throughput:" + r["record_id"],
                cohort="SPEC89 throughput archive",
                system=r["system"],
                source_url=r["source_url"],
                clock_mhz=None,
                processor_raw="",
                os_raw=r["operating_system"],
                cpu_count=number(r["processor_count"]),
                evidence_class="archived_report",
                metrics_raw={"SPECthruput89": r["SPECthruput89"]},
                raw_record=r,
            )
        )
    for i, r in enumerate(read_csv("data/derived/spec/cpu92-rate/cpu92-rate-records.csv")):
        mhz = re.search(r"(\d+(?:\.\d+)?)\s*MHz", r["processor"], re.I)
        records.append(
            dict(
                id="spec92-netlib:" + str(i),
                cohort="SPEC92 rate Netlib",
                system=full_name(r["company"], r["system"]),
                source_url=r["source_url"],
                clock_mhz=float(mhz[1]) if mhz else None,
                processor_raw=r["processor"],
                os_raw=r["os"],
                cpu_count=number(r["cpu_count"]),
                evidence_class=r["evidence_class"],
                metrics_raw={r["peak_metric"]: r["peak_score"], r["base_metric"]: r["base_score"]},
                raw_record=r,
            )
        )
    for r in read_csv("research/data/spec/cpu92-dec-alpha-openvms-1992.csv"):
        if r["metric"] != "SPECrate_int92":
            continue
        records.append(
            dict(
                id="spec92-dec:" + r["record_id"],
                cohort="SPEC92 rate manufacturer",
                system=r["system"],
                source_url=r["source_url"],
                clock_mhz=None,
                processor_raw="",
                os_raw=r["operating_system"],
                cpu_count=number(r["configured_cpu_count"]),
                evidence_class=r["evidence_class"],
                metrics_raw={r["metric"]: r["reported_score"]},
                raw_record=r,
            )
        )
    return records


def compare(records, specs):
    pairs = []
    for c in records:
        if c["identity_scope"] != "system":
            continue
        key = model_key(c["system"])
        loose = relaxed_key(c["system"], c["clock_mhz"])
        for s in specs:
            skey = model_key(s["system"])
            sl = relaxed_key(s["system"], s["clock_mhz"])
            if key != skey and loose != sl:
                continue
            ca, cb = c["clock_mhz"], s["clock_mhz"]
            clock = (
                "unknown" if ca is None or cb is None else ("compatible_1pct" if abs(ca - cb) <= 0.01 * max(ca, cb) else "conflict")
            )
            pairs.append(
                dict(
                    classic_id=c["id"],
                    spec_id=s["id"],
                    benchmark=c["benchmark"],
                    spec_cohort=s["cohort"],
                    model_key=loose,
                    classic_system=c["system"],
                    spec_system=s["system"],
                    match_rule="normalized_model" if key == skey else "corroborated_clock_suffix",
                    clock_check=clock,
                    classic_clock_mhz=ca,
                    spec_clock_mhz=cb,
                    classic_config=c["configuration_raw"],
                    classic_os=c["os_raw"],
                    spec_os=s["os_raw"],
                    spec_cpu_count=s["cpu_count"],
                    review_status="candidate_not_configuration_verified",
                    fit_eligible=False,
                    spec_evidence_class=s["evidence_class"],
                    classic_processor=c["processor_raw"],
                    spec_processor=s["processor_raw"],
                    classic_locator=c["locator"],
                    classic_url=c["source_url"],
                    spec_url=s["source_url"],
                )
            )
    return pairs


def write_csv(path, rows):
    return shared_write_csv(path, rows, fields=list(rows[0]) if rows else [], lineterminator="\n", empty_text="")


@click.command("overlap-spec")
@click.option(
    "--acquisition",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    default=Path("research/data/classic/acquisition.csv"),
    show_default=True,
)
@click.option(
    "--output-root", type=click.Path(path_type=Path), default=Path("data/derived/classic/overlap-spec"), show_default=True
)
def overlap_spec(acquisition, output_root):
    """Parse supported classical rows and enumerate SPEC89/92 model candidates."""
    try:
        records, rejected, coverage = parse_classics(acquisition)
        specs = load_specs()
        pairs = compare(records, specs)
        output_root.mkdir(parents=True, exist_ok=True)
        for name, rows in [("classical-records", records), ("spec-records", specs), ("rejected-rows", rejected)]:
            (output_root / (name + ".jsonl")).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        write_csv(output_root / "candidate-pairs.csv", pairs)
        write_csv(output_root / "source-coverage.csv", coverage)
        summary = []
        for family in sorted({r["benchmark"] for r in records}):
            cr = [r for r in records if r["benchmark"] == family]
            for cohort in sorted({r["cohort"] for r in specs}):
                ps = [p for p in pairs if p["benchmark"] == family and p["spec_cohort"] == cohort]
                summary.append(
                    dict(
                        benchmark=family,
                        spec_cohort=cohort,
                        parsed_classic_rows=len(cr),
                        system_rows=sum(r["identity_scope"] == "system" for r in cr),
                        cpu_only_rows=sum(r["identity_scope"] == "cpu_only" for r in cr),
                        candidate_models=len({p["model_key"] for p in ps}),
                        matched_classic_rows=len({p["classic_id"] for p in ps}),
                        matched_spec_records=len({p["spec_id"] for p in ps}),
                        candidate_pairs=len(ps),
                        clock_conflict_pairs=sum(p["clock_check"] == "conflict" for p in ps),
                        verified_configurations=0,
                    )
                )
        write_csv(output_root / "summary.csv", summary)
        groups = defaultdict(list)
        for pair in pairs:
            groups[(pair["benchmark"], pair["spec_cohort"], pair["model_key"])].append(pair)
        models = []
        for (benchmark, cohort, key), members in sorted(groups.items()):
            models.append(
                dict(
                    benchmark=benchmark,
                    spec_cohort=cohort,
                    model_key=key,
                    classic_systems=" | ".join(sorted({p["classic_system"] for p in members})),
                    spec_systems=" | ".join(sorted({p["spec_system"] for p in members})),
                    candidate_pairs=len(members),
                    classic_rows=len({p["classic_id"] for p in members}),
                    spec_rows=len({p["spec_id"] for p in members}),
                    clock_compatible_pairs=sum(p["clock_check"] == "compatible_1pct" for p in members),
                    clock_conflict_pairs=sum(p["clock_check"] == "conflict" for p in members),
                    clock_unknown_pairs=sum(p["clock_check"] == "unknown" for p in members),
                    review_status="pending_configuration_review",
                )
            )
        write_csv(output_root / "model-summary.csv", models)

        inputs = [
            Path(acquisition),
            Path("research/data/spec89/aggregate89-plus-helman.csv"),
            Path("research/data/spec89/v2.0.0/csv/throughput89.csv"),
            Path("data/derived/spec/cpu92-rate/cpu92-rate-records.csv"),
            Path("research/data/spec/cpu92-dec-alpha-openvms-1992.csv"),
        ]
        audit = {
            "method": METHOD,
            "parsed_classic_rows": len(records),
            "spec_records": len(specs),
            "candidate_pairs": len(pairs),
            "rejected_rows": len(rejected),
            "inputs": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
            "pdf_text_extractions": {r["source_id"]: r["text_extraction_sha256"] for r in records if "text_extraction_sha256" in r},
            "pdftotext_version": subprocess.run(["pdftotext", "-v"], capture_output=True, check=True)
            .stderr.decode()
            .splitlines()[0],
            "parser_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "derived_inputs": {
                r["extraction_path"]: hashlib.sha256(Path(r["extraction_path"]).read_bytes()).hexdigest()
                for r in read_csv(acquisition)
                if r["source_id"] in {x["source_id"] for x in records} and r["extraction_path"]
            },
            "caution": "Model-name candidates only. Repeated source rows retained. No score fitting or configuration equivalence established.",
        }
        (output_root / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
        click.echo(json.dumps(audit))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        raise click.ClickException(str(exc)) from exc
