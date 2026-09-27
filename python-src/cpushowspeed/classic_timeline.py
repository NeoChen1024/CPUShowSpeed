"""Source-preserving classical and SPEC89 VAXen timeline."""

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import click
import numpy as np
from cpushowspeed.classic_network_data import values
from cpushowspeed.classic_overlap import full_name, model_key, relaxed_key
from cpushowspeed.classic_predict import predict_scores
from cpushowspeed.research_io import code_hashes, read_csv, write_csv

ROOT = Path("data/derived/classic")


def jsonl(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()]


def year(value):
    m = re.fullmatch(r"((?:19|20)\d\d)(?:-\d\d(?:-\d\d)?)?", str(value or "").strip())
    return int(m[1]) if m else None


def date_key(system, clock=None):
    system = re.sub(r"^DEC Alpha ", "DEC ", system, flags=re.I)
    system = re.split(r"\s*\(", system)[0].strip()
    try:
        clock = float(clock) if clock else None
    except ValueError:
        clock = None
    return relaxed_key(system, clock)


def date_catalog(records):
    evidence = []

    def add(system, date, method, url, locator, priority, clock="", notes=""):
        if year(date):
            evidence.append(
                dict(
                    system=system,
                    model_key=date_key(system, clock),
                    year=year(date),
                    date=str(date),
                    method=method,
                    source_url=url,
                    locator=locator,
                    priority=priority,
                    clock_mhz=clock or "",
                    notes=notes,
                )
            )

    for r in records:
        add(
            r["system"],
            r.get("introduction_year_raw"),
            "source_approximate_first_delivery",
            r["source_url"],
            r["locator"],
            2,
            r.get("clock_mhz"),
        )
    for r in read_csv(Path("research/data/spec89/hardware-introductions.csv")):
        add(
            r["system_normalized"],
            r["hardware_introduced_at"] or r["hardware_introduction_year"],
            r["event_type"],
            r["source_url"],
            r["source_locator"],
            1,
            notes=r["notes"],
        )
    path = ROOT / "longbottom-mips-f2019d91d05a.json"
    page = json.loads(path.read_text())
    for block in page["blocks"]:
        if block.get("kind") != "preformatted":
            continue
        vendor = ""
        for line_number, line in enumerate(block["text"].splitlines(), 1):
            if not line.strip() or line.strip() == "To Index" or line.startswith(("Manufacturer", "Processor")):
                continue
            name, tail = line[:19].strip(), line[19:]
            if name and (not tail.strip() or tail.strip().startswith("OS ")):
                vendor = name
                continue
            if name:
                add(
                    full_name(vendor, name),
                    line[61:67].strip(),
                    "catalog_year_proxy",
                    page["source"]["url"],
                    f"pre:{block.get('pre_index')}:line:{line_number}",
                    3,
                    clock=line[33:40].strip(),
                    notes=line,
                )
    for r in read_csv(Path("data/derived/spec/cpu92-rate/cpu92-rate-records.csv")):
        add(
            r["system"],
            r["hardware_availability_month"],
            "SPEC_configuration_availability_model_proxy",
            r["source_url"],
            "Hardware availability",
            2,
            notes="Availability of a SPEC configuration of this model; not necessarily this source configuration.",
        )
    import datetime

    for r in read_csv(Path("data/raw/spec/cpu95/bulk.csv")):
        try:
            date = datetime.datetime.strptime(r["HW Avail"], "%b-%Y").strftime("%Y-%m")
        except ValueError:
            continue
        link = re.search(r'HREF="([^"]+)', r.get("Disclosure", ""), re.I)
        url = "https://www.spec.org" + link[1] if link else "https://www.spec.org/cpu95/results/"
        add(
            r["System"],
            date,
            "SPEC_configuration_availability_model_proxy",
            url,
            "HW Avail",
            2,
            notes="Availability of a SPEC configuration of this model; not necessarily this source configuration.",
        )
    for r in read_csv(Path("research/data/historical/hardware-date-evidence.csv")):
        if r["use_for_timeline"] != "true":
            continue
        add(
            r["machine"],
            r["date"],
            "reviewed_" + r["event_type"] + "_model_proxy",
            r["source_url"],
            r.get("source_locator") or ("PDF page " + r["pdf_page"] + "; " + r["printed_page"]),
            0,
            notes=r["notes"],
        )
        evidence[-1]["system_regex"] = r["system_regex"]
        evidence[-1]["date_evidence_id"] = r["id"]
    return evidence


def choose_date(system, clock, evidence, overrides):
    """Model dates are proxies for configurations, never exact configuration dates."""
    key = date_key(system, clock)
    candidates = [
        e for e in evidence if (re.search(e["system_regex"], system, re.I) if e.get("system_regex") else e["model_key"] == key)
    ]
    for rule in overrides:
        if rule.get("fallback") == "true" and candidates:
            continue
        if re.search(rule["system_regex"], system, re.I):
            y = year(rule["year"])
            return dict(
                year=y or "",
                year_low=y or "",
                year_high=y or "",
                date_method=rule["method"],
                date_status="estimated" if y else "unresolved_conflict",
                date_sources=rule["source_url"],
                date_notes=rule["notes"],
            )
    if not candidates:
        base = re.split(r"\s*\(", system)[0].strip()
        candidates = [e for e in evidence if not e.get("system_regex") and e["model_key"] == model_key(base)]
    # Only use explicitly model-matched evidence. No performance-derived dates.
    if candidates:
        priority = min(e["priority"] for e in candidates)
        candidates = [e for e in candidates if e["priority"] == priority]
        compatible = [e for e in candidates if clock and e["clock_mhz"] and str(clock) == str(e["clock_mhz"])]
        if compatible:
            candidates = compatible
        ys = sorted({e["year"] for e in candidates})
        return dict(
            year=int(np.median(ys)),
            year_low=min(ys),
            year_high=max(ys),
            date_method=";".join(sorted({e["method"] for e in candidates})),
            date_status="estimated",
            date_sources=";".join(sorted({e["source_url"] for e in candidates})),
            date_notes="Model-year proxy for measured configuration; midpoint of distinct source years if conflicting. "
            "Configuration upgrades and software may be later. "
            + " | ".join(sorted({e["notes"] for e in candidates if e["notes"]})),
        )
    return dict(year="", year_low="", year_high="", date_method="unknown", date_status="unknown", date_sources="", date_notes="")


def apply_cpu_release_proxy(record, proxies):
    """Use reviewed configuration-specific CPU dates only for genuinely unknown years."""
    if record.get("date_status") != "unknown":
        return
    proxy = proxies.get(record["configuration_id"])
    if proxy is None:
        return
    for key in ("system", "cpu", "clock_mhz"):
        actual = str(record.get(key) or "")
        expected = proxy[key]
        if key == "clock_mhz" and actual and expected:
            matches = float(actual) == float(expected)
        else:
            matches = actual == expected
        if not matches:
            raise ValueError(f"Stale CPU date mapping for {record['configuration_id']}: {key}")
    y = year(proxy["release_date"])
    if y is None:
        raise ValueError(f"Invalid CPU release date: {proxy['release_date']}")
    record.update(
        year=y,
        year_low=y,
        year_high=y,
        date_method="reviewed_cpu_release_year_proxy",
        date_status="estimated",
        date_sources=proxy["source_url"],
        date_notes=f"CPU release proxy: {proxy['cpu_interpretation']}; {proxy['release_date']}. "
        "Not a system/configuration launch date; later boards, options and software may differ. " + proxy["notes"],
    )


def source_identity(record, pages):
    """Rejoin LINPACK wrapped identity lines; retain original record in provenance."""
    r = dict(record)
    if r["benchmark"] != "LINPACK" or not r["locator"].startswith("pdf:"):
        return r
    page, line = map(int, r["locator"].split(":")[2::2])
    lines = pages[page - 1].splitlines()
    header = next(s for s in lines[:12] if re.search(r"n=100\s", s))
    start = header.index("n=100") - 4
    parts = []
    for index in range(line - 1, max(10, line - 7), -1):
        text = lines[index]
        if index != line - 1 and re.search(r"\d", text[start:]):
            break
        if not text.strip():
            break
        # A deeply indented fragment is a compiler continuation, not a machine.
        if len(text) - len(text.lstrip()) < 5:
            first = re.split(r"\s{2,}", text[:start].strip())[0]
            if first:
                parts.insert(0, first)
    if parts:
        r["system"] = " ".join(parts)
        r["original_system"] = record["system"]
        r["identity_reconstruction"] = "joined machine-column fragments preceding numeric source row"
        match = re.search(r"(\d+)\s*proc\b", r["system"], re.I)
        if match:
            r["reported_processor_count"] = int(match[1])
        match = re.search(r"(\d+(?:\.\d+)?)\s*(MHz|GHz)", r["system"], re.I)
        if match:
            r["clock_mhz"] = float(match[1]) * (1000 if match[2].lower() == "ghz" else 1)
    return r


def collect(records, pages, vectors, spec_rows, specs):
    groups = defaultdict(list)
    excluded = Counter()
    for original_record in records:
        r = source_identity(original_record, pages)
        scores = values(r, pages)
        if not scores:
            excluded["no_supported_score"] += 1
            continue
        if r.get("reported_processor_count") not in (None, 1):
            excluded["explicit_multiple_processors_outside_calibration"] += 1
            continue
        # Unknown configurations stay separate; no cross-source environment equivalence is assumed.
        key = (
            r["source_id"],
            r["system"],
            r.get("clock_mhz"),
            r.get("processor_raw"),
            r.get("os_raw"),
            r.get("configuration_raw"),
            r.get("language_raw"),
            r.get("optimization_raw"),
        )
        if not r.get("clock_mhz"):
            key += (r["id"],)
        groups[key].append((r, scores))
    rows, observations = [], []
    for key, members in groups.items():
        r = members[0][0]
        cid = "classic-" + hashlib.sha256(json.dumps(key).encode()).hexdigest()[:16]
        samples = defaultdict(list)
        for original, scores in members:
            for metric, score in scores.items():
                samples[metric].append(score)
                observations.append(
                    dict(
                        configuration_id=cid,
                        observation_id=original["id"],
                        metric=metric,
                        score=score,
                        source_url=original["source_url"],
                        locator=original["locator"],
                        provenance=json.dumps(original, sort_keys=True),
                    )
                )
        scores = {m: math.exp(float(np.median(np.log(v)))) for m, v in samples.items()}
        rows.append(
            dict(
                configuration_id=cid,
                route="classical",
                system=r["system"],
                cpu=r.get("processor_raw") or "",
                clock_mhz=r.get("clock_mhz") or "",
                os=r.get("os_raw") or "",
                configuration=r.get("configuration_raw") or "",
                scores=scores,
                source_url=r["source_url"],
                observation_count=len(members),
            )
        )
    for v in vectors:
        if not v["scores"]:
            continue
        cid = "vector-" + v["id"]
        rows.append(
            dict(
                configuration_id=cid,
                route="classical",
                system=v["machine"],
                cpu="",
                clock_mhz=v.get("clock_mhz") or "",
                os=v.get("os") or "",
                configuration="Reviewed same-source table column; unknown CPU count",
                scores=v["scores"],
                source_url=v["source_url"],
                observation_count=1,
            )
        )
        for m, score in v["scores"].items():
            observations.append(
                dict(
                    configuration_id=cid,
                    observation_id=v["observation_ids"].get(m, v["id"]),
                    metric=m,
                    score=score,
                    source_url=v["source_url"],
                    locator=f"PDF page {v['pdf_page']}",
                    provenance=json.dumps(v, sort_keys=True),
                )
            )
    for r in spec_rows:
        original = specs[r["spec_id"]]
        raw = original["raw_record"]
        cid = r["spec_id"]
        rows.append(
            dict(
                configuration_id=cid,
                route="SPEC89",
                system=r["system"],
                cpu=original.get("processor_raw") or "",
                clock_mhz=original.get("clock_mhz") or "",
                os=original.get("os_raw") or "",
                configuration=raw.get("cache_raw", "") if isinstance(raw, dict) else "",
                scores={"SPECint89": float(r["raw_specint89"])},
                source_url=r["source_url"],
                observation_count=1,
                vaxen=float(r["estimated_rate_vaxen"]),
                ci95_low=float(r["factor_ci95_target_low"]),
                ci95_high=float(r["factor_ci95_target_high"]),
            )
        )
        observations.append(
            dict(
                configuration_id=cid,
                observation_id=cid,
                metric="SPECint89",
                score=r["raw_specint89"],
                source_url=r["source_url"],
                locator=original.get("locator", ""),
                provenance=json.dumps(original, sort_keys=True),
            )
        )
    return rows, observations, dict(excluded)


def label_annual_maxima(ax, rows, colors):
    """Place readable callouts in display space, retaining exact data anchors."""
    import textwrap

    from matplotlib.font_manager import FontProperties
    from matplotlib.transforms import Bbox

    byyear = defaultdict(list)
    for row in rows:
        if row["year"]:
            byyear[row["year"]].append(row)
    ax.figure.canvas.draw()
    renderer = ax.figure.canvas.get_renderer()
    font = FontProperties(size=7.5)
    occupied = []
    anchors = [ax.transData.transform((yr, max(group, key=lambda r: r["vaxen"])["vaxen"])) for yr, group in sorted(byyear.items())]
    for (yr, group), (px, py) in zip(sorted(byyear.items()), anchors):
        row = max(group, key=lambda r: r["vaxen"])
        color = colors[row["route"]]
        label = f"{yr} · " + "\n".join(textwrap.wrap(row["system"], width=30, break_long_words=False))
        lines = label.splitlines()
        width = max(renderer.get_text_width_height_descent(line, font, False)[0] for line in lines) + 12
        height = len(lines) * renderer.points_to_pixels(9) + 10
        candidates = []
        for dy in (32, 65, 100, 140, -35, -70, -110, 185, -155):
            for dx in (0, 65, -65, 130, -130, 200, -200, 280, -280):
                cx = min(max(px + dx, ax.bbox.x0 + width / 2 + 5), ax.bbox.x1 - width / 2 - 5)
                cy = min(max(py + dy, ax.bbox.y0 + height / 2 + 5), ax.bbox.y1 - height / 2 - 5)
                box = Bbox.from_bounds(cx - width / 2, cy - height / 2, width, height)
                overlap = sum(box.overlaps(other) for other in occupied)
                covered = sum(box.contains(x, y) for x, y in anchors)
                distance = math.hypot(cx - px, cy - py)
                candidates.append((overlap * 10000 + covered * 5000 + distance + (25 if dy < 0 else 0), cx, cy, box))
        _, cx, cy, box = min(candidates, key=lambda c: c[0])
        occupied.append(box.expanded(1.06, 1.15))
        ax.scatter([yr], [row["vaxen"]], s=52, facecolors="white", edgecolors=color, linewidths=1.6, zorder=5)
        ax.scatter([yr], [row["vaxen"]], s=9, color=color, zorder=6)
        ax.annotate(
            label,
            xy=(yr, row["vaxen"]),
            xytext=((cx - px) / renderer.points_to_pixels(1), (cy - py) / renderer.points_to_pixels(1)),
            textcoords="offset points",
            ha="center",
            va="center",
            fontsize=7.5,
            color="#173342",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=color, alpha=0.96, lw=0.65),
            arrowprops=dict(arrowstyle="->", color=color, lw=1.0, shrinkA=3, shrinkB=4, mutation_scale=8),
            zorder=7,
        )


def render(rows, output):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from cpushowspeed.rate_convert import _si
    from matplotlib.ticker import FuncFormatter

    fig, (ax, undated) = plt.subplots(1, 2, figsize=(24, 13), gridspec_kw={"width_ratios": [5, 1]}, sharey=True)
    colors = {"classical": "#207ca3", "SPEC89": "#bd5934"}
    for route, color in colors.items():
        for dated, target in ((True, ax), (False, undated)):
            group = [r for r in rows if r["route"] == route and bool(r["year"]) == dated]
            x = [r["year"] if dated else (0 if route == "classical" else 1) for r in group]
            y = [r["vaxen"] for r in group]
            target.errorbar(
                x,
                y,
                yerr=[[r["vaxen"] - r["ci95_low"] for r in group], [r["ci95_high"] - r["vaxen"] for r in group]],
                fmt="none",
                ecolor=color,
                alpha=0.10,
                linewidth=2,
                zorder=1,
            )
            if dated:
                target.hlines(y, [r["year_low"] for r in group], [r["year_high"] for r in group], color=color, alpha=0.14)
            target.scatter(
                x,
                y,
                s=17,
                marker="o" if route == "classical" else "D",
                facecolors="none",
                edgecolors=color,
                linewidths=0.6,
                alpha=0.6,
                label=f"{route} ({len(group)})",
                zorder=2,
            )
    for target in (ax, undated):
        target.set_yscale("log")
        target.grid(alpha=0.16, which="both")
        target.legend(loc="lower right", fontsize=9)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: _si(x)))
    ax.set_ylabel("Estimated VAXen — equivalent SPEC92 integer rate", fontsize=12)
    ax.set_xlabel("Estimated model / CPU introduction year (configuration may be later)", fontsize=12)
    undated.set_xticks([0, 1], ["Classical", "SPEC89"])
    undated.set_xlim(-0.6, 1.6)
    undated.set_title("Year unresolved\nSame vertical scale", fontsize=11)
    ax.set_title("Classical benchmarks + SPEC89: historical hardware in VAXen", fontsize=19, loc="left")
    fig.text(
        0.06,
        0.018,
        "Hollow points: model/CPU-year estimates. Horizontal spans: conflicting date evidence. Pale vertical spans: calibration CI95 only,\n"
        "not machine prediction intervals. Repeated source measurements retained; source/configuration aggregation uses median log scores.\n"
        "Native / SP / DP remain distinct; equal available families. SPEC89 uses the two-edge SPEC92 bridge. No additional clock scaling.\n"
        "Boxed labels and arrows identify annual maxima; emphasized rings locate their exact data points. All eligible records remain plotted.",
        fontsize=10,
    )
    fig.subplots_adjust(bottom=0.13, top=0.9, left=0.06, right=0.98, wspace=0.10)
    label_annual_maxima(ax, rows, colors)
    for ext in ("png", "svg"):
        fig.savefig(output / ("historical-vaxen." + ext), dpi=160)
    plt.close(fig)
    # Embedded data and native SVG: usable offline, with full-name search and hover.
    payload = json.dumps(rows, ensure_ascii=False).replace("<", "\\u003c")
    page = """<!doctype html><meta charset="utf-8"><title>Historical VAXen</title>
<style>body{font:15px system-ui;margin:24px;color:#223}input{width:36em;padding:8px}svg{width:100%;min-width:900px;background:#fafbfd}td,th{padding:7px;text-align:left;border-bottom:1px solid #ddd}table{border-collapse:collapse;width:100%}small{color:#556}</style>
<h1>Classical benchmarks + SPEC89: historical VAXen</h1><p>Search system, CPU, configuration or benchmark: <input id="q" placeholder="VAX, PDP, LINPACK…"></p>
<p id="count"></p><p>Hardware years are estimates/proxies; unknown years remain in the table. Pale spans show calibration CI95, not individual prediction intervals. The two routes share calibration evidence and are not independent validation.</p>
<svg id="plot" viewBox="0 0 1400 760"></svg><table><thead><tr><th>Year / evidence</th><th>System / configuration</th><th>Route / inputs</th><th>VAXen / CI95</th><th>Sources</th></tr></thead><tbody id="body"></tbody></table>
<script>const data=PAYLOAD;const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=x=>Number(x).toPrecision(4);const dated=data.filter(r=>r.year);const ymin=Math.floor(Math.log10(Math.min(...data.map(r=>r.ci95_low))));const ymax=Math.ceil(Math.log10(Math.max(...data.map(r=>r.ci95_high))));const xmin=Math.min(...dated.map(r=>r.year))-1,xmax=Math.max(...dated.map(r=>r.year))+1;
const X=x=>90+(x-xmin)/(xmax-xmin)*1270,Y=y=>680-(Math.log10(y)-ymin)/(ymax-ymin)*640;
function draw(){let rows=data.filter(r=>JSON.stringify(r).toLowerCase().includes(document.querySelector('#q').value.toLowerCase()));document.querySelector('#count').textContent=`${rows.length} configurations / source submissions; ${rows.filter(r=>r.year).length} with estimated years`;
let s='';for(let y=ymin;y<=ymax;y++){let p=Y(10**y);s+=`<path d="M90 ${p}H1360" stroke="#dde3e8"/><text x="8" y="${p+5}">10^${y} VAXen</text>`}for(let x=Math.ceil(xmin/5)*5;x<=xmax;x+=5){s+=`<path d="M${X(x)} 40V680" stroke="#eee"/><text x="${X(x)-17}" y="710">${x}</text>`}
for(const r of rows.filter(r=>r.year)){let c=r.route==='SPEC89'?'#bd5934':'#207ca3';let title=esc(`${r.system} | ${r.cpu} | ${r.clock_mhz} MHz | ${r.os}\n${r.configuration}\n${r.year_low}–${r.year_high}: ${r.date_method}\n${r.vaxen} VAXen; CI95 ${r.ci95_low}–${r.ci95_high}\n${r.scores}`);s+=`<g><title>${title}</title><path d="M${X(r.year)} ${Y(r.ci95_low)}V${Y(r.ci95_high)} M${X(r.year_low)} ${Y(r.vaxen)}H${X(r.year_high)}" stroke="${c}" opacity=".2" stroke-width="3"/><circle cx="${X(r.year)}" cy="${Y(r.vaxen)}" r="4" fill="${c}" fill-opacity=".45"/></g>`}document.querySelector('#plot').innerHTML=s;
document.querySelector('#body').innerHTML=rows.map(r=>`<tr><td>${esc(r.year||'Unknown')}<br><small>${esc(r.date_method)} ${esc(r.year_low)}–${esc(r.year_high)}</small></td><td>${esc(r.system)}<br>${esc(r.cpu)} ${esc(r.clock_mhz)} MHz<br><small>${esc(r.os)} ${esc(r.configuration)}</small></td><td>${esc(r.route)}<br><small>${esc(r.scores)}</small></td><td>${fmt(r.vaxen)}<br><small>${fmt(r.ci95_low)}–${fmt(r.ci95_high)}</small></td><td><a href="${esc(r.source_url)}">Benchmark</a><br>${r.date_sources.split(';').filter(Boolean).map(u=>`<a href="${esc(u)}">Year source</a>`).join(' ')}<br><small>${esc(r.date_notes)}</small></td></tr>`).join('')};document.querySelector('#q').addEventListener('input',draw);draw();</script>"""
    (output / "historical-vaxen.html").write_text(page.replace("PAYLOAD", payload))


@click.command("historical-timeline")
@click.option("--output", type=click.Path(path_type=Path), default=ROOT / "historical-timeline", show_default=True)
def historical_timeline(output):
    """Aggregate original classical measurements and SPEC89 estimates, date and plot."""
    paths = [
        ROOT / "overlap-spec/classical-records.jsonl",
        ROOT / "netlib-linpack-report.txt",
        ROOT / "source-pair-fit/vectors.jsonl",
        Path("research/data/classic/spec89-rate-estimates.csv"),
        ROOT / "overlap-spec/spec-records.jsonl",
        Path("research/data/historical/timeline-year-overrides.csv"),
        Path("research/data/spec89/hardware-introductions.csv"),
        ROOT / "longbottom-mips-f2019d91d05a.json",
        Path("data/derived/spec/cpu92-rate/cpu92-rate-records.csv"),
        Path("data/raw/spec/cpu95/bulk.csv"),
        Path("research/data/historical/hardware-date-evidence.csv"),
        Path("research/data/historical/cpu-release-proxies.csv"),
    ]
    records = jsonl(paths[0])
    rows, observations, excluded = collect(
        records, paths[1].read_text().split("\f"), jsonl(paths[2]), read_csv(paths[3]), {r["id"]: r for r in jsonl(paths[4])}
    )
    evidence, overrides = date_catalog(records), read_csv(paths[5])
    cpu_proxies = {r["configuration_id"]: r for r in read_csv(paths[-1])}
    for i, r in enumerate(rows):
        if r["route"] == "classical":
            p = predict_scores(r["scores"], ROOT / "network-fit")
            r.update(vaxen=p["vaxen"], ci95_low=p["vaxen_ci95"]["low"], ci95_high=p["vaxen_ci95"]["high"])
        r.update(choose_date(r["system"], r["clock_mhz"], evidence, overrides))
        apply_cpu_release_proxy(r, cpu_proxies)
        r["scores"] = json.dumps(r["scores"], sort_keys=True)
        r["evidence_class"] = "model_prediction_not_reported_SPEC_result"
        r["uncertainty_scope"] = "conditional_calibration_CI95_not_machine_prediction_interval"
        if i % 200 == 0:
            click.echo(f"Predicting / dating {i+1}/{len(rows)}", err=True)
    rows.sort(key=lambda r: (r["year"] or 9999, r["system"], r["configuration_id"]))
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "configurations.csv", rows)
    write_csv(output / "observations.csv", observations)
    for r in rows:
        if r["date_method"] == "reviewed_cpu_release_year_proxy":
            proxy = cpu_proxies[r["configuration_id"]]
            evidence.append(
                dict(
                    system=r["system"],
                    model_key="",
                    year=r["year"],
                    date=proxy["release_date"],
                    method=r["date_method"],
                    source_url=proxy["source_url"],
                    locator=proxy["source_locator"],
                    priority="fallback_only",
                    clock_mhz=r["clock_mhz"],
                    notes=r["date_notes"],
                    configuration_id=r["configuration_id"],
                )
            )
    write_csv(output / "date-evidence.csv", evidence)
    write_csv(output / "undated.csv", [r for r in rows if not r["year"]])
    render(rows, output)
    paths += list((ROOT / "network-fit").glob("prediction-calibration.json")) + [
        ROOT / "network-fit/coefficients.csv",
        ROOT / "network-fit/coefficient-log-draws.npz",
    ]
    audit = dict(
        configurations=len(rows),
        observations=len(observations),
        routes=dict(Counter(r["route"] for r in rows)),
        dated=sum(bool(r["year"]) for r in rows),
        undated=sum(not r["year"] for r in rows),
        year_min=min(r["year"] for r in rows if r["year"]),
        year_max=max(r["year"] for r in rows if r["year"]),
        exclusions=excluded,
        input_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        code_sha256=code_hashes(__file__),
        date_policy="model-era estimates with reviewed CPU-release fallback; unknown configurations retained",
        no_additional_clock_scaling=True,
    )
    (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    click.echo(json.dumps({k: v for k, v in audit.items() if k not in ("input_sha256", "code_sha256")}))
