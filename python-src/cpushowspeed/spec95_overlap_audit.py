"""Source-linked eligibility audit for the CPU95/CPU2000 joint bridge."""

import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict
from functools import cache
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

import click
from cpushowspeed.research_io import code_hashes, write_csv
from cpushowspeed.spec import get_cached
from cpushowspeed.spec_overlap import (
    _checked_bulk,
    _frequency,
    _memory_mib,
    _normalized,
    _positive,
    _source_url,
)
from cpushowspeed.spec_rate_fit import collect_integer

MEMORY = {"memory_unknown", "memory_mismatch"}
ALIASES = {"system_name", "processor_label"}
RESOURCES = {"chips", "cores", "threads_per_core"}
SCENARIOS = {
    "current_strict": set(),
    "memory_relaxed": MEMORY,
    "candidate_aliases_only": ALIASES,
    "memory_and_candidate_aliases": MEMORY | ALIASES,
    "ignore_system_memory_diagnostic": MEMORY | {"system_name", "unresolved_system", "processor_label"},
    "ignore_resources_diagnostic": RESOURCES,
    "memory_aliases_ignore_resources_diagnostic": MEMORY | ALIASES | RESOURCES,
}


@cache
def candidate_system_key(item):
    """Review-only lexical/brand candidates; never a production identity mapping."""
    value = re.sub(r"\b(?:compaq|model)\b", " ", item.system, flags=re.I)
    value = re.sub(r"\b(?:alphastation|professional\s+workstation)\s+xp1000\b", "XP1000", value, flags=re.I)
    # A declared 6/clock model suffix is redundant only when its clock agrees.
    match = re.search(r"\b6/(\d+)\s*$", value)
    if match and item.clock_mhz and abs(float(match[1]) / item.clock_mhz - 1) <= 0.01:
        value = value[: match.start()]
    return _normalized(value)


@cache
def candidate_processor_key(item):
    return re.sub(r"^mips(?=r\d)", "", item.processor_key)


def blockers(a, b):
    reasons = set()
    if a.system_key != b.system_key:
        reasons.add("system_name")
        if candidate_system_key(a) != candidate_system_key(b):
            reasons.add("unresolved_system")
    if a.processor_key != b.processor_key:
        reasons.add("processor_label")
        if candidate_processor_key(a) != candidate_processor_key(b):
            reasons.add("unresolved_processor")
    if a.chips != b.chips:
        reasons.add("chips")
    if not a.clock_mhz or not b.clock_mhz:
        reasons.add("clock_unknown")
    elif abs(a.clock_mhz / b.clock_mhz - 1) > 0.01:
        reasons.add("clock_mismatch")
    if not a.memory_mib or not b.memory_mib:
        reasons.add("memory_unknown")
    elif a.memory_mib != b.memory_mib:
        reasons.add("memory_mismatch")
    if a.cores is not None and b.cores is not None and a.cores != b.cores:
        reasons.add("cores")
    if (
        a.enabled_threads_per_core is not None
        and b.enabled_threads_per_core is not None
        and a.enabled_threads_per_core != b.enabled_threads_per_core
    ):
        reasons.add("threads_per_core")
    return reasons


def candidates(left, right):
    out = []
    for a in left:
        for b in right:
            same_platform = a.system_key == b.system_key or candidate_system_key(a) == candidate_system_key(b)
            cpu_clock = (
                candidate_processor_key(a) == candidate_processor_key(b)
                and a.clock_mhz
                and b.clock_mhz
                and abs(a.clock_mhz / b.clock_mhz - 1) <= 0.01
            )
            if same_platform or cpu_clock:
                out.append((a, b, blockers(a, b)))
    return out


def pair_record(a, b, flags, edge):
    row = dict(
        edge=edge,
        left_id=a.result_id,
        right_id=b.result_id,
        left_url=a.source_url,
        right_url=b.source_url,
        left_system=a.system,
        right_system=b.system,
        blockers=json.dumps(sorted(flags)),
        left_sha256=a.source_container_sha256,
        right_sha256=b.source_container_sha256,
    )
    for role, item in (("left", a), ("right", b)):
        for field in ("processor", "processor_key", "chips", "cores", "clock_mhz", "memory_mib", "peak", "base"):
            row[role + "_" + field] = getattr(item, field)
    return row


def disclosure_fields(document):
    def plain(value):
        return " ".join(unescape(re.sub("<[^>]+>", " ", value)).split())

    cells = re.findall(r"<TH\b[^>]*>(.*?)\s*(?:</TH>)?\s*<TD\b[^>]*>(.*?)(?=</TD>|<TR\b|</TR|</TABLE)", document, re.I | re.S)
    fields = {plain(label): plain(value) for label, value in cells}
    return fields


def review_disclosures(urls, records, raw, fetch_missing):
    rows = []
    for url in sorted(urls):
        parts = urlparse(url).path.strip("/").split("/")
        if len(parts) != 4 or parts[1] != "results" or parts[0] not in ("cpu95", "cpu2000"):
            raise ValueError("unexpected disclosure URL: " + url)
        path = raw / parts[0] / parts[2] / parts[3]
        if not path.exists() and not fetch_missing:
            rows.append(dict(source_url=url, status="not_cached"))
            continue
        body = get_cached(url, path, refresh=False, delay=0.2)
        meta = json.loads(path.with_name(path.name + ".meta.json").read_text())
        digest = hashlib.sha256(body).hexdigest()
        if meta["sha256"] != digest or meta["source_url"] != url:
            raise ValueError("disclosure identity mismatch: " + str(path))
        document = body.decode("latin1")
        f = disclosure_fields(document)
        fields = {
            key: f.get(key, "")
            for key in (
                "Model Name:",
                "CPU:",
                "CPU MHz:",
                "Number of CPU(s):",
                "CPU(s) enabled:",
                "CPU(s) orderable:",
                "Memory:",
                "Secondary Cache:",
            )
        }
        row = dict(
            source_url=url,
            source_sha256=digest,
            source_file=str(path),
            status="fields_extracted",
            source_locator="Hardware table, named TH/TD fields",
            fields_json=json.dumps(fields, sort_keys=True),
        )
        text = " ".join(unescape(re.sub("<[^>]+>", " ", document)).split())
        row["result_status"] = "NC" if re.search(r"SPECint(?:_base)?2000\s*=\s*NC", text) else "not_classified"
        if row["result_status"] == "NC" and "3 month availability" in text:
            row["qualification"] = "SPEC withdrawal: three-month availability requirement; numeric aggregates unavailable"
        if url in records:
            record = records[url]
            raw_chips = fields["Number of CPU(s):"]
            if not raw_chips:
                m = re.search(r"(\d+)\s+chips?", fields["CPU(s) enabled:"])
                raw_chips = m[1] if m else ""
            row["parsed_chips"] = int(raw_chips) if raw_chips.isdigit() else None
            row["parsed_memory_mib"] = _memory_mib(fields["Memory:"])
            row["parsed_clock_mhz"] = _frequency(
                {"System": fields["Model Name:"], "Processor MHz": fields["CPU MHz:"]}, fields["CPU:"]
            )
            row["model_matches_bulk"] = _normalized(fields["Model Name:"]) == record.system_key
            row["cpu_text_matches_bulk"] = _normalized(fields["CPU:"]) == _normalized(record.processor)
            row["chips_match_bulk"] = row["parsed_chips"] == record.chips
            row["memory_matches_bulk"] = row["parsed_memory_mib"] == record.memory_mib
            row["clock_matches_bulk"] = row["parsed_clock_mhz"] == record.clock_mhz
            row["status"] = (
                "source_fields_match_bulk"
                if all(
                    row[k]
                    for k in (
                        "model_matches_bulk",
                        "cpu_text_matches_bulk",
                        "chips_match_bulk",
                        "memory_matches_bulk",
                        "clock_matches_bulk",
                    )
                )
                else "field_difference_needs_review"
            )
        rows.append(row)
    return rows


def analyze(raw, output, research, fetch_review=False):
    output.mkdir(parents=True, exist_ok=True)
    research.mkdir(parents=True, exist_ok=True)
    bulk_rows = {g: _checked_bulk(raw / g / "bulk.csv")[0] for g in ("cpu95", "cpu2000")}
    exclusions = []
    for generation, rows in bulk_rows.items():
        for row in rows:
            if row["Benchmark"] not in ("CINT" + generation[3:], "CINT" + generation[3:] + "rate"):
                continue
            reasons = []
            if (
                _positive(row.get("Result") or row.get("Peak Result")) is None
                and _positive(row.get("Baseline") or row.get("Base Result")) is None
            ):
                reasons.append("no_positive_score")
            if not (row.get("Processor") or row.get("CPU")):
                reasons.append("missing_processor")
            if not (row.get("# chips") or row.get("# Chips") or "").isdigit():
                reasons.append("unparsed_chip_count")
            if reasons:
                exclusions.append(
                    dict(
                        generation=generation,
                        benchmark=row["Benchmark"],
                        system=row["System"],
                        raw_result=row.get("Result") or row.get("Peak Result"),
                        raw_base=row.get("Baseline") or row.get("Base Result"),
                        reason=";".join(reasons),
                        source_url=_source_url(row["Disclosure"]),
                    )
                )
    write_csv(research / "collection-exclusions.csv", exclusions)
    speed, rate = collect_integer(raw, "speed"), collect_integer(raw, "rate")
    old, speeds, rates = rate["cpu95"], speed["cpu2000"], rate["cpu2000"]
    a, b = candidates(old, speeds), candidates(old, rates)
    edge_pairs = {"95rate_2000speed": a, "95rate_2000rate": b}
    records = {r.source_url: r for r in [*old, *speeds, *rates]}
    counts, triples, exports, flags_rows = [], [], [], []
    for edge, pairs in edge_pairs.items():
        exports.extend(pair_record(*p, edge) for p in pairs)
        # Blocker counts at the old exact-name/CPU/chips candidate boundary.
        exact = [
            p
            for p in pairs
            if p[0].system_key == p[1].system_key and p[0].processor_key == p[1].processor_key and p[0].chips == p[1].chips
        ]
        counter = Counter(flag for _, _, flags in exact for flag in flags)
        flags_rows.extend(
            dict(edge=edge, candidate_boundary="exact_system_cpu_chips", flag=flag, pair_count=n, nonexclusive=True)
            for flag, n in sorted(counter.items())
        )
    for scenario, allowed in SCENARIOS.items():
        sa, ra = defaultdict(list), defaultdict(list)
        for pairs, index in ((a, sa), (b, ra)):
            for left, right, flags in pairs:
                if flags <= allowed:
                    index[left.source_url].append(right)
        accepted = []
        for url in sorted(sa.keys() & ra.keys()):
            target = records[url]
            for s in sa[url]:
                for r in ra[url]:
                    if blockers(r, s) <= allowed and len({url, s.source_url, r.source_url}) == 3:
                        accepted.append((target, s, r))
        for mode in ("base", "peak"):
            complete = [(t, s, r) for t, s, r in accepted if all(getattr(v, mode) is not None for v in (t, s, r))]
            counts.append(
                dict(
                    scenario=scenario,
                    mode=mode,
                    target_speed_pairs=sum(map(len, sa.values())),
                    target_rate_pairs=sum(map(len, ra.values())),
                    triples=len(complete),
                    systems=len({t.system_key for t, s, r in complete}),
                    processor_models=len({candidate_processor_key(t) for t, s, r in complete}),
                    processor_configurations=len({(candidate_processor_key(t), t.chips, t.clock_mhz) for t, s, r in complete}),
                    processor_keys=";".join(sorted({candidate_processor_key(t) for t, s, r in complete})),
                    policy="baseline" if scenario == "current_strict" else "sensitivity_only_not_fit_eligible",
                )
            )
            for t, s, r in complete:
                triples.append(
                    dict(
                        scenario=scenario,
                        mode=mode,
                        target_url=t.source_url,
                        speed_url=s.source_url,
                        rate_url=r.source_url,
                        target_system=t.system,
                        speed_system=s.system,
                        rate_system=r.system,
                        processor_key=candidate_processor_key(t),
                        target_chips=t.chips,
                        speed_chips=s.chips,
                        rate_chips=r.chips,
                        target_clock=t.clock_mhz,
                        speed_clock=s.clock_mhz,
                        rate_clock=r.clock_mhz,
                        target_memory=t.memory_mib,
                        speed_memory=s.memory_mib,
                        rate_memory=r.memory_mib,
                        target_score=getattr(t, mode),
                        speed_score=getattr(s, mode),
                        rate_score=getattr(r, mode),
                        relaxed_blockers=json.dumps(sorted(blockers(t, s) | blockers(t, r) | blockers(r, s))),
                    )
                )
    # Per-old-system census distinguishes absence under this name from physical nonexistence.
    inventory = []
    by_name = defaultdict(list)
    for t in old:
        by_name[t.system_key].append(t)
    for name, group in sorted(by_name.items()):
        ns = [v for v in speeds if v.system_key == name]
        nr = [v for v in rates if v.system_key == name]
        if not ns and not nr:
            continue
        inventory.append(
            dict(
                system=group[0].system,
                cpu95_rate_rows=len(group),
                cpu2000_speed_rows=len(ns),
                cpu2000_rate_rows=len(nr),
                cpu95_rate_chips=json.dumps(sorted({x.chips for x in group})),
                cpu2000_speed_chips=json.dumps(sorted({x.chips for x in ns})),
                cpu2000_rate_chips=json.dumps(sorted({x.chips for x in nr})),
                cpu95_rate_processors=json.dumps(sorted({x.processor_key for x in group})),
                cpu2000_speed_processors=json.dumps(sorted({x.processor_key for x in ns})),
                cpu2000_rate_processors=json.dumps(sorted({x.processor_key for x in nr})),
                source_urls=json.dumps([x.source_url for x in group + ns + nr]),
            )
        )
    write_csv(research / "ablation.csv", counts)
    write_csv(research / "blockers.csv", flags_rows)
    write_csv(research / "system-coverage.csv", inventory)
    write_csv(output / "candidate-pairs.csv", exports)
    write_csv(output / "scenario-triples.csv", triples)
    write_csv(
        output / "source-records.csv",
        [dict(asdict(r), role=role) for role, data in (("95rate", old), ("2000speed", speeds), ("2000rate", rates)) for r in data],
    )
    selected_urls = {
        r[k] for r in triples if r["scenario"] == "memory_and_candidate_aliases" for k in ("target_url", "speed_url", "rate_url")
    }
    selected_urls |= {
        r.source_url
        for r in records.values()
        if r.system in ("HP 9000 Model N4000", "SGI 2200: 2X 400MHz R12k", "SGI 2200 2X 400MHz R12k") and r.clock_mhz in (552, 400)
    }
    selected_urls |= {r["source_url"] for r in exclusions if r["system"] == "SGI 2200 2X 400MHz R12k"}
    reviews = review_disclosures(selected_urls, records, raw, fetch_review)
    write_csv(research / "disclosure-checks.csv", reviews)
    checked = {r["source_url"] for r in reviews if r["status"] == "source_fields_match_bulk"}
    aliases = []
    for edge, pairs in edge_pairs.items():
        for left, right, flags in pairs:
            if not flags <= MEMORY | ALIASES:
                continue
            for kind, field, key in (
                ("system", "system", candidate_system_key),
                ("processor", "processor", candidate_processor_key),
            ):
                marker = "system_name" if kind == "system" else "processor_label"
                if marker in flags:
                    aliases.append(
                        dict(
                            kind=kind,
                            left_value=getattr(left, field),
                            right_value=getattr(right, field),
                            candidate_key=key(left),
                            left_url=left.source_url,
                            right_url=right.source_url,
                            edge=edge,
                            remaining_blockers=json.dumps(sorted(flags - ALIASES)),
                            status=(
                                "identity_candidate_fields_checked"
                                if left.source_url in checked and right.source_url in checked
                                else "identity_candidate_details_pending"
                            ),
                        )
                    )
    write_csv(research / "alias-candidates.csv", aliases)
    audit = dict(
        method_version="spec95-2000-overlap-audit-v1",
        code_hashes=code_hashes(__file__),
        input_sha256={g: hashlib.sha256((raw / g / "bulk.csv").read_bytes()).hexdigest() for g in ("cpu95", "cpu2000")},
        disclosure_review_counts=dict(Counter(r["status"] for r in reviews)),
        usable_records={"cpu95_rate": len(old), "cpu2000_speed": len(speeds), "cpu2000_rate": len(rates)},
        raw_integer_records={
            g: dict(Counter(r["Benchmark"] for r in rows if r["Benchmark"] in ("CINT" + g[3:], "CINT" + g[3:] + "rate")))
            for g, rows in bulk_rows.items()
        },
        scenarios={k: sorted(v) for k, v in SCENARIOS.items()},
        limitations=[
            "No factor changes or fit-cohort promotion",
            "Candidate aliases require source/configuration review",
            "Missing means absent in this cached export under this identity",
            "Ignoring resources/platform identity is a diagnostic upper bound only",
        ],
        output_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob("*.csv")},
    )
    (research / "audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    return dict(summary=str(research / "ablation.csv"), systems=len(inventory), candidate_pairs=len(exports))


@click.command("audit-95-2000")
@click.option("--raw-dir", type=click.Path(path_type=Path), default=Path("data/raw/spec"), show_default=True)
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("data/derived/spec/95-2000-audit"), show_default=True)
@click.option(
    "--research-dir", type=click.Path(path_type=Path), default=Path("research/data/spec/95-2000-audit"), show_default=True
)
@click.option("--fetch-review", is_flag=True, help="Fetch missing source disclosures selected by this audit.")
def audit_95_2000(raw_dir, output_dir, research_dir, fetch_review):
    """Explain CPU95/2000 joint-overlap losses without changing production matches."""
    try:
        result = analyze(raw_dir, output_dir, research_dir, fetch_review)
    except (OSError, ValueError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, sort_keys=True))
