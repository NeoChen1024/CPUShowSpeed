#!/usr/bin/env python3
"""Rebuild the curated SPEC89 tables from immutable compact inputs.

This is the historical v2.0.0 merge logic called through the project CLI.
Published observations stay separate from QA calculations and later reruns.
"""
from __future__ import annotations

import collections
import copy
import csv
import hashlib
import itertools
import json
import math
import re
from pathlib import Path

DATE = "2026-09-26"
METRICS = ("SPECmark89", "SPECint89", "SPECfp89")
TESTS = [
    "001.gcc",
    "008.espresso",
    "013.spice2g6",
    "015.doduc",
    "020.nasa7",
    "022.li",
    "023.eqntott",
    "030.matrix300",
    "042.fpppp",
    "047.tomcatv",
]
INT = ["001.gcc", "008.espresso", "022.li", "023.eqntott"]
FP = [t for t in TESTS if t not in INT]
QA_THRESHOLD = 0.02


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def dump(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def fields_of(rows):
    return list(dict.fromkeys(k for r in rows for k in r))


def write_csv(path: Path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields_of(rows))
        w.writeheader()
        w.writerows(rows)


def build_snapshot(source_root: Path, output_root: Path):
    """Build all canonical tables and validation reports without changing inputs."""
    source_root = source_root.resolve()
    output_root = output_root.resolve()
    inputs = source_root / "inputs"
    out = output_root / "csv"
    out.mkdir(parents=True, exist_ok=True)
    a = load(inputs / "original_dataset.json")
    u = load(inputs / "usenet_dataset.json")
    aliases = {r["raw_name"]: r["normalized_name"] for r in a["aliases"]}
    for r in a["aggregate89"]:
        aliases.setdefault(r["system_raw"], r["system_normalized"])
    # Only unambiguous label expansions. No RC/RX correction, inferred CPU,
    # merged workstation/server suffixes, or clock extraction from product names.
    additions = {
        "HP750": "HP 9000/750",
        "HP730": "HP 9000/730",
        "HP720": "HP 9000/720",
        "HP710": "HP 9000/710",
        "HP9000/730": "HP 9000/730",
        "HP9000/720": "HP 9000/720",
        "IBM550": "IBM RS/6000 550",
        "IBM530H": "IBM RS/6000 530H",
        "IBM320H": "IBM RS/6000 320H",
        "Sun IPX": "Sun SPARCstation IPX",
        "Sun ELC": "Sun SPARCstation ELC",
        "SPARCstation 330": "Sun SPARCstation 330",
        "DEC 5000/200": "DECstation 5000/200",
        "DEC DS5000/200": "DECstation 5000/200",
        "DEC DS5810": "DECsystem 5810",
        "DEC 6000/410": "DEC VAX 6000/410",
        "Apollo DN10010": "HP Apollo DN10010",
        "HP 425s": "HP 9000/425s",
        "Intel 486 50DX2": "Intel i486DX2-50",
        "Intel 486 50DX": "Intel i486DX-50",
        "Intel 486 66DX2": "Intel i486DX2-66",
        "Intel Star860": "Intel STAR860",
        "CDC 4680 (beta)": "CDC 4680 (Beta)",
        "DEC 3000 400S AXP": "DEC 3000/400S AXP",
        "DEC 3000 500S AXP": "DEC 3000/500S AXP",
        "DEC 4000 610 AXP": "DEC 4000/610 AXP",
        "DEC 7000 610 AXP": "DEC 7000/610 AXP",
        "DEC 10000 610 AXP": "DEC 10000/610 AXP",
        "DG Aviion 310": "Data General AV 310",
        "DG Aviion 410": "Data General AV 410",
        "DG Aviion 5010": "Data General 5010",
        "DG Aviion 6200": "Data General 6200",
        # Verified spelling-only changes across DiMarco's frozen score table.
        "Intel 486DX": "i486DX",
        "Intel 486DX2": "Intel i486DX2",
        "Intel 386/387": "i386/387",
        "Sun SS/IPC": "Sun SPARCstation IPC",
    }
    aliases.update(additions)
    for r in u["aggregates"]:
        m = re.fullmatch(r"IBM RS6000/(\w+)", r["system"])
        if m:
            aliases[r["system"]] = "IBM RS/6000 " + m.group(1)

    def norm(s):
        s = " ".join(s.split())
        if s.startswith("Sun SS/"):
            s = s.replace("Sun SS/", "Sun SS ", 1)
        return aliases.get(s, s)

    def key(s):
        return re.sub(r"[^a-z0-9+]", "", norm(s).lower())

    def vendor(s):
        for prefix, value in [
            ("DEC", "DEC"),
            ("VAX", "DEC"),
            ("HP", "HP/Apollo"),
            ("Apollo", "HP/Apollo"),
            ("Sun", "Sun"),
            ("IBM", "IBM"),
            ("Intel", "Intel"),
            ("i486", "Intel"),
            ("MIPS", "MIPS"),
            ("SGI", "SGI"),
            ("Motorola", "Motorola"),
            ("NeXT", "NeXT"),
            ("CDC", "CDC"),
            ("Data General", "Data General"),
            ("DG", "Data General"),
            ("Harris", "Harris"),
            ("Stardent", "Stardent"),
            ("Solbourne", "Solbourne"),
            ("Alacron", "Alacron"),
            ("AT&T", "AT&T"),
        ]:
            if s.startswith(prefix):
                return value
        return ""

    def u_prov(r):
        return {
            "source_date": r.get("publication_date", ""),
            "source_message_id": r.get("source_message_id", ""),
            "source_file": r.get("source_file", ""),
            "source_lines": r.get("source_lines", ""),
            "import_batch": "usenet_recovery",
            "original_record_id": r.get("record_id", ""),
        }

    def evidence(r):
        status = r.get("status", "")
        if "collector" in status or "reference" in status or "beta" in status:
            return "contemporary_collector"
        if "vendor-reported" in status:
            return "vendor_posting"
        if "DECUS" in status:
            return "contemporary_vendor_briefing_repost"
        if "development" in status:
            return "contemporary_development_report_repost"
        return "contemporary_report_repost"

    # Keep all existing record IDs and original observations. No lookup joins of
    # partial INT/FP observations are permitted.
    aggregate = copy.deepcopy(a["aggregate89"])
    for r in aggregate:
        r.update(
            source_message_id="",
            source_file="",
            source_lines="",
            import_batch="initial_web_recovery",
            original_record_id=r["record_id"],
            source_status_raw="",
        )
    quarantine = next(r for r in aggregate if r["record_id"] == "A0230")
    quarantine["measurement_type"] = "quarantined_possible_cpu_time_approximation"
    quarantine["notes"] += (
        " QUARANTINE: Convex C240 FP geometric mean 38.7 also occurs in explicit "
        "CPU-time, NOT-SPEC posts of 1992-06-14 and 1992-06-28. Exact lineage of the excerpt "
        "is not proved by matching score alone. See Noncompliant89 and audit_log.csv."
    )
    for src in u["aggregates"]:
        status = src["status"]
        mt = (
            "reference_definition"
            if "reference" in status
            else (
                "reported_beta"
                if "beta" in status
                else (
                    "reported_development"
                    if "development" in status
                    else "component_only" if "component-only" in status else "reported_native"
                )
            )
        )
        r = {k: None if k in METRICS else "" for k in a["aggregate89"][0]}
        r.update(
            record_id=src["record_id"],
            source_id=src["source_id"],
            vendor=vendor(norm(src["system"])),
            system_raw=src["system"],
            system_normalized=norm(src["system"]),
            **{k: src.get(k) for k in METRICS},
            clock_MHz_raw=str(src.get("clock_MHz", "")),
            operating_system=src.get("operating_system", ""),
            compiler=src.get("compiler", ""),
            suite="SPEC89 / Release 1",
            measurement_type=mt,
            evidence_class=evidence(src),
            source_url=src["source_url"],
            page_table="TXT lines " + src["source_lines"],
            notes=src.get("notes", ""),
            verification="archived_message_sha256_verified",
            source_status_raw=status,
            **u_prov(src),
        )
        if src["record_id"].startswith("UNEXT"):
            r["cpu_raw"] = "68040"
            r["cache_raw"] = "4K instruction + 4K data"
        aggregate.append(r)
    byid = {r["record_id"]: r for r in aggregate}
    if len(byid) != len(aggregate):
        raise ValueError("Duplicate record IDs")

    components = copy.deepcopy(a["components89"])
    for r in components:
        r.update(
            compiler="",
            flags="",
            raw_test=r["benchmark"],
            source_message_id="",
            source_file="",
            source_lines="",
            import_batch="initial_web_recovery",
            original_component_id=r["component_id"],
        )
    for i, src in enumerate(u["components"], start=len(components) + 1):
        p = byid[src["record_id"]]
        components.append(
            {
                "component_id": f"C{i:04}",
                "record_id": p["record_id"],
                "source_id": src["source_id"],
                "system_raw": src["system"],
                "system_normalized": p["system_normalized"],
                "benchmark": src["test"],
                "category": "INT" if src["test"] in INT else "FP",
                "SPECratio": src["ratio_published"],
                "runtime_seconds": src.get("time_seconds_published"),
                "source_url": src["source_url"],
                "page_table": "TXT lines " + src["source_lines"],
                "notes": "Published ratios; raw elapsed time retained only when printed.",
                "compiler": src.get("compiler", ""),
                "flags": src.get("flags", ""),
                "raw_test": src.get("raw_test", src["test"]),
                **u_prov(src),
                "original_component_id": f"{src['record_id']}:{src['test']}",
            }
        )
    vectors = collections.defaultdict(dict)
    for c in components:
        if c["benchmark"] in vectors[c["record_id"]]:
            raise ValueError("Duplicate component key")
        vectors[c["record_id"]][c["benchmark"]] = c["SPECratio"]

    # QA on every complete available category; never substitute calculated values
    # into published SPEC result fields. Threshold is a review hint, not SPEC rules.
    qa = []
    for r in aggregate:
        if r["record_id"] not in vectors:
            continue
        vals = vectors[r["record_id"]]
        q = {
            "record_id": r["record_id"],
            "source_id": r["source_id"],
            "system": r["system_normalized"],
            "reported_mark": r["SPECmark89"],
            "reported_int": r["SPECint89"],
            "reported_fp": r["SPECfp89"],
            **{t: vals.get(t) for t in TESTS},
        }
        deltas = []
        for kind, ts in [("mark", TESTS), ("int", INT), ("fp", FP)]:
            v = math.exp(sum(math.log(vals[t]) for t in ts) / len(ts)) if all(t in vals for t in ts) else None
            published = q["reported_" + kind]
            d = (v / published - 1) if v is not None and published not in (None, 0) else None
            q["calculated_" + kind] = v
            q["delta_" + kind] = d
            if d is not None:
                deltas.append(d)
        q["flag"] = "REVIEW" if any(abs(d) > QA_THRESHOLD for d in deltas) else "Within 2%" if deltas else "NO_COMPARABLE_AGGREGATE"
        q["notes"] = (
            "Calculated from rounded published ratios; missing/incomplete groups left blank. Never overwrites reported scores."
        )
        q["source_url"] = r["source_url"]
        q["source_file"] = r["source_file"]
        qa.append(q)
    qa_map = {r["record_id"]: r for r in qa}
    for r in aggregate:
        flags = []
        mt = r["measurement_type"]
        if mt != "reported_native":
            flags.append(mt)
        if "pending" in r["verification"] or "html" in r["verification"]:
            flags.append("inherited_verification_limit")
        if r["record_id"] in qa_map and qa_map[r["record_id"]]["flag"] == "REVIEW":
            flags.append("component_geomean_review")
        r.update(
            component_count=len(vectors[r["record_id"]]),
            has_reported_score=any(r[k] is not None for k in METRICS),
            review_flags=";".join(flags),
            score_overlap_group="",
        )

    groups = collections.defaultdict(list)
    for r in aggregate:
        if r["has_reported_score"]:
            groups[(key(r["system_normalized"]), tuple(r[k] for k in METRICS))].append(r["record_id"])
    og = 0
    for members in groups.values():
        if len(members) < 2:
            continue
        og += 1
        for rid in members:
            byid[rid]["score_overlap_group"] = f"OG{og:03}"
    overlaps = []
    for left, right in itertools.combinations(aggregate, 2):
        if key(left["system_normalized"]) != key(right["system_normalized"]):
            continue
        shared = [m for m in METRICS if left[m] is not None and right[m] is not None]
        if not shared or any(left[m] != right[m] for m in shared):
            continue
        va, vb = vectors[left["record_id"]], vectors[right["record_id"]]
        same_vector = bool(va and vb and va == vb)
        conflicts = [
            f
            for f in ["clock_MHz_raw", "operating_system", "compiler", "cache_raw"]
            if left.get(f) and right.get(f) and left[f] != right[f]
        ]
        overlaps.append(
            {
                "overlap_id": f"O{len(overlaps)+1:04}",
                "left_record_id": left["record_id"],
                "right_record_id": right["record_id"],
                "system": left["system_normalized"],
                "matching_published_metrics": ";".join(shared),
                "complete_available_vectors_equal": same_vector,
                "metadata_string_differences": ";".join(conflicts),
                "decision": "retain_both_not_proven_same_run",
                "left_source_id": left["source_id"],
                "right_source_id": right["source_id"],
                "left_source_url": left["source_url"],
                "right_source_url": right["source_url"],
                "notes": "Matching rounded scores or components do not establish independent executions or identical configurations.",
            }
        )

    bridges = copy.deepcopy(a["bridges89_92"])
    for r in bridges:
        r.update(
            bridge_type=(
                "full_INT_FP_89_92"
                if all(r.get(m) is not None for m in ["SPECint89", "SPECfp89", "SPECint92", "SPECfp92"])
                else "mark89_to_INT_FP_92"
            ),
            source_date=byid[r["record_id"]]["source_date"],
            source_message_id="",
            source_file="",
            source_lines="",
            import_batch="initial_web_recovery",
            original_record_id=r["record_id"],
            measurement_type=byid[r["record_id"]]["measurement_type"],
        )
    for i, src in enumerate(u["bridges"], start=len(bridges) + 1):
        p = byid[src["record_id"]]
        bridges.append(
            {
                "bridge_id": f"B{i:03}",
                "record_id": p["record_id"],
                "source_id": src["source_id"],
                "system": p["system_normalized"],
                "operating_system": p["operating_system"],
                **{m: src.get(m) for m in (*METRICS, "SPECint92", "SPECfp92")},
                "source_url": src["source_url"],
                "page_table": "TXT lines " + src["source_lines"],
                "notes": src.get("notes", ""),
                "bridge_type": (
                    "full_INT_FP_89_92"
                    if all(src.get(m) is not None for m in ["SPECint89", "SPECfp89", "SPECint92", "SPECfp92"])
                    else "mark89_to_INT_FP_92"
                ),
                **u_prov(src),
                "measurement_type": p["measurement_type"],
            }
        )
    throughput = copy.deepcopy(a["throughput89"])
    for r in throughput:
        r.update(
            source_message_id="",
            source_file="",
            source_lines="",
            import_batch="initial_web_recovery",
            original_record_id=r["record_id"],
        )
    for i, src in enumerate(u["throughput"], start=len(throughput) + 1):
        throughput.append(
            {
                "record_id": f"T{i:03}",
                "source_id": src["source_id"],
                "system": norm(src["system"]),
                "processor_count": src["cpu_count"],
                "SPECthruput89": src["SPECthruput89"],
                "operating_system": "Alpha OpenVMS",
                "source_url": src["source_url"],
                "page_table": "TXT lines " + src["source_lines"],
                "notes": "Throughput, not single-task speed. Source reports OpenVMS benchmark table.",
                **u_prov(src),
            }
        )
    runtime = []
    for i, src in enumerate(u["runtime"], 1):
        r = {"runtime_id": f"RT{i:03}", **src}
        r["system_normalized"] = norm(src["system"])
        r["notes"] = (
            "Published elapsed-time table; may contain times reconstructed from rounded ratios. printed_Mean is opaque, not SPECmark89."
        )
        runtime.append(r)
    nc = []
    nc_lookup = {}
    for i, src in enumerate(u["noncompliant"], 1):
        r = {"record_id": f"NC{i:03}", **src}
        r["measurement_type"] = "noncompliant_cpu_time_approximation"
        nc.append(r)
        nc_lookup[(r["source_id"], r["system"])] = r["record_id"]
    ncc = []
    for i, src in enumerate(u["noncompliant_components"], 1):
        r = {"component_id": f"NCC{i:03}", "record_id": nc_lookup[(src["source_id"], src["system"])], **src}
        r["source_url"] = "https://archive.org/download/usenet-comp/comp.benchmarks.mbox.zip"
        ncc.append(r)

    sources = copy.deepcopy(a["sources"])
    for r in sources:
        r.update(source_file="", source_message_id="", archive="", eml_sha256="", import_batch="initial_web_recovery")
    for src in u["sources"]:
        sources.append(
            {
                "source_id": src["source_id"],
                "title": src["subject"].strip(),
                "publisher": src["author"],
                "source_date": src["date"],
                "url": src["source_url"],
                "evidence_class": "archival_usenet_message",
                "extracted_scope": src["role"],
                "notes": "Local message bytes verified against supplied source manifest; referenced older reports not necessarily included.",
                "accessed": DATE,
                "source_file": src["extracted_file"],
                "source_message_id": src["message_id"],
                "archive": src["archive"],
                "eml_sha256": src["eml_sha256"],
                "import_batch": "usenet_recovery",
            }
        )
    source_ids = {r["source_id"] for r in sources}
    gaps = copy.deepcopy(a["gaps"])
    for r in gaps:
        r["updated"] = DATE
    g = next(r for r in gaps if r["gap_id"] == "G02")
    g.update(
        status="Partial content recovery; named FTP files not recovered",
        notes="75-row FP post (1992-09-26) and 11/19-row INT posts (1991) recovered. Not byte-identical FTP files. speccorr.tbl remains missing; correlations prose does not equal the full file.",
    )
    g = next(r for r in gaps if r["gap_id"] == "G07")
    g.update(
        status="Resolved for 17 recovered posts; 14 standalone tables parsed",
        notes="14 versions x 98 rows mapped to existing S02 observations without inflating the main table. Earliest 3 combined-format posts retained verbatim, not fully transcribed.",
    )
    for gid, item, status, notes in [
        (
            "G11",
            "Aburto bench.tar.gz",
            "Historical path evidenced; tarball not recovered",
            "README lists all programs/results in ftp.nosc.mil:/pub/aburto/bench.tar.gz.",
        ),
        (
            "G12",
            "McCalpin spec.sc / spec.print",
            "Historical announcements recovered; files not recovered",
            "Path variants retained in recovery_leads.csv; spec.print is a formatted subset.",
        ),
        (
            "G13",
            "Remaining Usenet result extraction",
            "Full keyword scan completed; manual/result extraction not exhaustive",
            "11,930 broad keyword candidates retained in archive_metadata; not 11,930 SPEC89 results.",
        ),
        (
            "G14",
            "Convex C240 38.7 exact provenance",
            "A0230 quarantined pending exact lineage",
            "Primary CPU-time approximation posts match model/score; this is not proof of the excerpt lineage.",
        ),
    ]:
        gaps.append(
            {
                "gap_id": gid,
                "item": item,
                "status": status,
                "lead_url": "https://archive.org/download/usenet-comp/",
                "notes": notes,
                "updated": DATE,
            }
        )

    # DiMarco's 1,372 versioned rows remain separately accessible, each mapped to
    # an existing observation. They are not 1,372 additional benchmark runs.
    dimrows = read_csv(inputs / "dimarco_14_versions_all_rows.csv")
    idx = collections.defaultdict(list)
    for r in a["aggregate89"]:
        if r["source_id"] == "S02":
            idx[(key(r["system_normalized"]), r["SPECmark89"])].append(r["record_id"])
    unmatched = []
    for i, r in enumerate(dimrows, 1):
        r["SPECmark89"] = float(r["SPECmark89"])
        hits = idx[(key(r["system"]), r["SPECmark89"])]
        r["version_row_id"] = f"DV{i:04}"
        r["linked_record_id"] = hits[0] if len(hits) == 1 else ""
        r["link_basis"] = "same_normalized_label_and_published_mark_in_frozen_collector_table"
        r["relationship"] = "collector_republication_not_added_to_main"
        if len(hits) != 1:
            unmatched.append({"row": r["version_row_id"], "name": r["system"], "score": r["SPECmark89"], "hits": hits})
    if unmatched:
        raise ValueError("Ambiguous/unmapped DiMarco rows: " + str(unmatched[:10]))

    audit = [
        {
            "audit_id": "AUD001",
            "record_id": "A0230",
            "field": "measurement_type",
            "old_value": "reported_native",
            "new_value": quarantine["measurement_type"],
            "reason": u["audit"][0]["evidence"],
            "supporting_source_ids": u["audit"][0]["source_ids"],
            "effective_date": DATE,
        },
        {
            "audit_id": "AUD002",
            "record_id": "",
            "field": "DiMarco version rows",
            "old_value": "separate addendum table",
            "new_value": "1372 version rows linked to 98 existing S02 observations; not appended to main",
            "reason": "Preserve version metadata without implying additional independent executions.",
            "supporting_source_ids": "S02;" + ";".join(r["source_id"] for r in u["snapshots"]),
            "effective_date": DATE,
        },
    ]
    mapping = [
        {
            "import_batch": r["import_batch"],
            "original_record_id": r["original_record_id"],
            "record_id": r["record_id"],
            "source_id": r["source_id"],
            "action": "preserved_and_flagged" if r["record_id"] == "A0230" else "preserved",
        }
        for r in aggregate
    ]
    tables = {
        "aggregate89": aggregate,
        "components89": components,
        "bridges89_92": bridges,
        "throughput89": throughput,
        "reruns": copy.deepcopy(a["reruns"]),
        "rerun_components": copy.deepcopy(a["rerun_components"]),
        "simulations": copy.deepcopy(a["simulations"]),
        "supplemental_claims": copy.deepcopy(a["supplemental_claims"]),
        "runtime89": runtime,
        "noncompliant89": nc,
        "noncompliant_components": ncc,
        "qa_components": qa,
        "quarantine": [copy.deepcopy(quarantine)],
        "overlap_candidates": overlaps,
        "record_map": mapping,
        "sources": sources,
        "source_manifest": copy.deepcopy(u["sources"]),
        "gaps": gaps,
        "benchmarks": copy.deepcopy(a["benchmarks"]),
        "aliases": [
            {"raw_name": s, "normalized_name": n, "rule": "label_expansion_only_not_configuration_identity"}
            for s, n in sorted(aliases.items())
            if s != n
        ],
        "dimarco_versions": copy.deepcopy(u["snapshots"]),
        "dimarco_version_rows": dimrows,
        "recovery_leads": copy.deepcopy(u["leads"]),
        "audit_log": audit,
    }
    # Detailed machine-readable dictionary: every column of every exported table.
    meanings = {r["field"]: r["meaning"] for r in a["dictionary"]}
    meanings.update(
        {
            "source_file": "Package-relative path to the unmodified saved Usenet message; blank for sources not bundled.",
            "source_lines": "1-based lines in source_file; may be non-contiguous. Not MBOX line numbers.",
            "source_message_id": "Original Usenet Message-ID; not a SPEC submission ID.",
            "import_batch": "initial_web_recovery or usenet_recovery; does not indicate independent measurement.",
            "original_record_id": "Record ID in the originating dataset; blank if the original table supplied no ID.",
            "source_status_raw": "Status annotation inherited verbatim from the Usenet addendum.",
            "component_count": "Count of linked published SPECratio rows, not number of tests or independent runs.",
            "has_reported_score": "True when at least one published SPEC89 aggregate metric is present.",
            "review_flags": "Semicolon-separated caution tags; absence is not official SPEC certification.",
            "score_overlap_group": "Exact same normalized label and three-field published score tuple, including null positions. Not proof of same run.",
            "measurement_type": "Reference, reported_native, beta, development, component_only, quarantine, rerun, simulation etc. Keep distinct.",
            "bridge_type": "full_INT_FP_89_92 versus mark89_to_INT_FP_92. Pairing is within the cited source only.",
            "printed_Mean": "Opaque value printed in the elapsed-time table; never imported as SPECmark89.",
            "decision": "Conservative overlap handling; matching scores do not justify deleting source observations.",
            "mbox_start": "Zero-based start byte offset in uncompressed MBOX, including envelope record.",
            "mbox_end": "Exclusive end byte offset in uncompressed MBOX.",
            "eml_sha256": "SHA-256 of source message bytes, without numeric MBOX envelope.",
            "linked_record_id": "Existing Aggregate89 record receiving a version-history link; no new measurement implied.",
            "SPECratio": "Published reference-runtime/test-runtime ratio; noncompliant CPU-time approximations are elsewhere.",
            "runtime_seconds": "Published elapsed seconds only; not reconstructed from ratios.",
            "calculated_mark": "QA geometric mean of all 10 published rounded ratios; not an original reported score.",
            "calculated_int": "QA geometric mean of all 4 published integer ratios; blank if incomplete.",
            "calculated_fp": "QA geometric mean of all 6 published floating-point ratios; blank if incomplete.",
            "delta_mark": "calculated_mark / reported_mark - 1; blank without a comparable reported aggregate.",
            "delta_int": "calculated_int / reported_int - 1; blank without a comparable reported aggregate.",
            "delta_fp": "calculated_fp / reported_fp - 1; blank without a comparable reported aggregate.",
            "flag": "REVIEW if any comparable aggregate differs by >2%; otherwise Within 2% or NO_COMPARABLE_AGGREGATE.",
        }
    )
    dictionary = []
    for name, rows in tables.items():
        for field in fields_of(rows):
            vals = [r[field] for r in rows if r.get(field) is not None and r.get(field) != ""]
            types = sorted({type(v).__name__ for v in vals})
            dictionary.append(
                {
                    "table": name,
                    "field": field,
                    "type": "|".join(types) or "empty",
                    "meaning": meanings.get(
                        field,
                        (
                            "Published benchmark column; see benchmarks."
                            if field in TESTS
                            else "Source/record attribute retained from originating dataset; see table notes and raw source."
                        ),
                    ),
                    "missing": "CSV empty cell; JSON null for missing numerics (legacy empty text retained).",
                }
            )
    tables["dictionary"] = dictionary

    stats = {
        "observation_rows": len(aggregate),
        "reported_aggregate_rows": sum(r["has_reported_score"] for r in aggregate),
        "component_only_rows": sum(not r["has_reported_score"] for r in aggregate),
        "nonquarantined_reported_aggregate_rows": sum(
            r["has_reported_score"] and not r["measurement_type"].startswith("quarantined") for r in aggregate
        ),
        **{"reported_" + m: sum(r[m] is not None for r in aggregate) for m in METRICS},
        "component_ratios": len(components),
        "component_profiles": len(qa),
        "complete_ten_test_profiles": sum(len(v) == 10 for v in vectors.values()),
        "INT_only_profiles": sum(set(v) == set(INT) for v in vectors.values()),
        "FP_only_profiles": sum(set(v) == set(FP) for v in vectors.values()),
        "bridges89_92": len(bridges),
        "full_INT_FP_bridges": sum(r["bridge_type"] == "full_INT_FP_89_92" for r in bridges),
        "throughput_rows": len(throughput),
        "runtime_vectors": len(runtime),
        "runtime_table_values": len(runtime) * len(TESTS),
        "rerun_rows": len(tables["reruns"]),
        "rerun_components": len(tables["rerun_components"]),
        "simulation_rows": len(tables["simulations"]),
        "supplemental_claim_rows": len(tables["supplemental_claims"]),
        "noncompliant_rows": len(nc),
        "noncompliant_components": len(ncc),
        "quarantined_rows": len(tables["quarantine"]),
        "source_records": len(sources),
        "saved_usenet_messages": len(u["sources"]),
        "dimarco_post_versions": len(u["snapshots"]),
        "dimarco_version_rows_not_added_to_main": len(dimrows),
        "score_overlap_pairs_not_proven_duplicates": len(overlaps),
        "score_overlap_groups": og,
        "QA_REVIEW_profiles": sum(q["flag"] == "REVIEW" for q in qa),
        "measurement_type_counts": dict(collections.Counter(r["measurement_type"] for r in aggregate)),
        "qa_review_record_ids": [q["record_id"] for q in qa if q["flag"] == "REVIEW"],
    }

    checks = []

    def check(name, ok, detail=""):
        checks.append({"check": name, "passed": bool(ok), "detail": detail})
        if not ok:
            raise AssertionError(name + ": " + detail)

    check("observation_count", len(aggregate) == 245 + 136)
    check(
        "published_scores_unchanged",
        all(all(byid[r["record_id"]][m] == r[m] for m in METRICS) for r in a["aggregate89"])
        and all(all(byid[r["record_id"]][m] == r.get(m) for m in METRICS) for r in u["aggregates"]),
    )
    check("component_count", len(components) == 290 + 650)
    check(
        "component_foreign_keys",
        all(c["record_id"] in byid and c["source_id"] == byid[c["record_id"]]["source_id"] for c in components),
    )
    check("positive_components", all(isinstance(c["SPECratio"], (float, int)) and c["SPECratio"] > 0 for c in components))
    check(
        "component_values_unchanged",
        all(c["SPECratio"] == o["SPECratio"] for c, o in zip(components[:290], a["components89"]))
        and all(c["SPECratio"] == o["ratio_published"] for c, o in zip(components[290:], u["components"])),
    )
    check(
        "bridge_foreign_keys_and_scores",
        all(r["record_id"] in byid and all(r.get(m) == byid[r["record_id"]].get(m) for m in METRICS) for r in bridges),
    )
    check("known_source_ids", all(r["source_id"] in source_ids for name, rows in tables.items() for r in rows if "source_id" in r))
    check("quarantine_applied", byid["A0230"]["measurement_type"].startswith("quarantined") and byid["A0230"]["SPECfp89"] == 38.7)
    check("no_missing_reported_score_filled", len([r for r in aggregate if not r["has_reported_score"]]) == 2)
    check("all_dimarco_rows_linked", all(r["linked_record_id"] in byid for r in dimrows))
    check("unique_source_ids", len(source_ids) == len(sources))
    for src in u["sources"]:
        path = source_root / src["extracted_file"]
        check(
            "source_sha256:" + src["source_id"],
            path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == src["eml_sha256"],
        )
    check(
        "source_paths_exist",
        all(not r.get("source_file") or (source_root / r["source_file"]).is_file() for rows in tables.values() for r in rows),
    )
    check(
        "source_line_bounds",
        all(
            all(
                1 <= int(x) <= len((source_root / r["source_file"]).read_bytes().splitlines())
                for x in re.findall(r"\d+", str(r.get("source_lines", "")))
            )
            for name in ["aggregate89", "components89"]
            for r in tables[name]
            if r.get("source_file")
        ),
    )
    for name, rows in tables.items():
        write_csv(out / (name + ".csv"), rows)
    data = {
        "schema_version": "2.0.0",
        "as_of": DATE,
        "qa_threshold": QA_THRESHOLD,
        "observation_semantics": "One row per recovered publication observation, not one independent execution. Known DiMarco republications are linked as history only.",
        "statistics": stats,
        **tables,
    }
    dump(output_root / "spec89_dataset.json", data)
    dump(output_root / "summary.json", stats)
    dump(
        output_root / "validation_report.json",
        {
            "as_of": DATE,
            "all_passed": all(x["passed"] for x in checks),
            "checks": checks,
            "scope": "Input integration, numeric preservation, IDs, lineage, component completeness, source file checksums. Not a new verification of original web/PDF sources.",
        },
    )
    return data
