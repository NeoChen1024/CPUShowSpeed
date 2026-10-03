"""Source-specific, hash-audited extraction of three historical PDF table sets."""

import hashlib
import json
import re
import statistics
import subprocess
from collections import Counter
from pathlib import Path

import blake3
import click
from cpushowspeed.research_io import code_hashes, write_csv

ROOT = Path("research/data/classic/pdf-extraction")


def scalar(raw):
    """Parse literal decimal/K/M only; never repair suspect units or footnotes."""
    text = raw.strip().replace(",", "")
    m = re.fullmatch(r"(\d+(?:\.\d*)?)([KM]?)", text)
    if not m:
        return None
    return float(m[1]) * {"": 1, "K": 1000, "M": 1000000}[m[2]]


def parse_table(recipe, text):
    lines = text.splitlines()
    rows = []
    for lineno in range(recipe["start_line"], recipe["end_line"] + 1):
        raw = lines[lineno - 1]
        if not raw.strip():
            continue
        if recipe["orientation"] == "metrics_as_rows":
            cut = recipe["label_cut"]
            label = raw[:cut].strip()
            if label and not re.match(r"[A-Za-z]", label):
                continue
            cells = [""] * len(recipe["columns"])
            for match in re.finditer(r"\S+(?: [^\s]+)*(?= {2,}|$)", raw[cut:]):
                endpoint = match.end() + cut
                i = min(range(len(cells)), key=lambda j: abs(recipe["column_ends"][j] - endpoint))
                if cells[i]:
                    raise ValueError(f'cell collision {recipe["table_id"]}:{lineno}')
                cells[i] = match.group()
            if not label:
                if any(cells):
                    if not rows:
                        raise ValueError("orphan table continuation")
                    rows[-1].setdefault("continuation_lines", []).append(dict(line=lineno, raw=raw, cells=cells))
                continue
            rows.append(dict(line=lineno, label_raw=label, cells=cells, text_layer_cells=cells.copy(), raw=raw))
        else:
            cells = re.split(r"\s{2,}", raw.strip())
            if recipe.get("fill_down_first") and len(cells) == len(recipe["fields"]) - 1:
                cells.insert(0, "")
            if len(cells) != len(recipe["fields"]):
                raise ValueError(
                    f'{recipe["source_id"]}:{recipe["table_id"]}:{lineno}: expected {len(recipe["fields"])} fields, got {cells}'
                )
            rows.append(dict(line=lineno, cells=cells, text_layer_cells=cells.copy(), raw=raw))
    if recipe.get("expected_rows") is not None and len(rows) != recipe["expected_rows"]:
        raise ValueError(f"row count mismatch: {recipe['table_id']}")
    return dict(recipe, rows=rows)


def correct(tables, corrections):
    applied = []
    for patch in corrections:
        table = next(t for t in tables if (t["source_id"], t["table_id"]) == (patch["source_id"], patch["table_id"]))
        row = next(r for r in table["rows"] if r["line"] == patch["line"])
        col = patch["column"] - 1
        if row["cells"][col] != patch["before"]:
            raise ValueError(f"correction precondition failed: {patch}")
        row["cells"][col] = patch["after"]
        row.setdefault("corrections", []).append(patch)
        applied.append(patch)
    return applied


def observations(tables):
    out = []
    for t in tables:
        previous_first = None
        for row in t["rows"]:
            if t["orientation"] == "records_as_rows":
                context = dict(zip(t["fields"], row["cells"]))
                if t.get("fill_down_first"):
                    if not row["cells"][0]:
                        context[t["fields"][0]] = previous_first
                    else:
                        previous_first = row["cells"][0]
            for col, raw in enumerate(row["cells"]):
                if t["orientation"] == "metrics_as_rows":
                    metric = row.get("label_checked", row["label_raw"])
                    ctx = dict(
                        t["columns"][col],
                        cell_notes=[n["cells"][col] for n in row.get("continuation_lines", []) if n["cells"][col]],
                    )
                else:
                    metric = t["fields"][col]
                    ctx = dict(t.get("table_context", {}), **context)
                    if metric in (
                        "machine",
                        "cpu",
                        "os",
                        "compiler",
                        "program",
                        "program_options",
                        "options",
                        "reference_time_expression_s",
                    ):
                        continue
                flags = []
                if "Whetstone" in metric and "KW" in metric:
                    flags.append("printed_KWIPS_label")
                if "Dhrystone" in metric and "instr/sec" in metric and raw and not raw.endswith(("K", "M")):
                    flags.append("source_missing_magnitude_suffix")
                if "LINPACK_DP_MFLOPS_size" in metric:
                    flags.append("matrix_size_not_explicit_in_table")
                if metric in ("CINT2006_reported", "CFP2006_reported"):
                    flags.append("research_report_not_official_rate_submission;base_peak_not_asserted")
                if not raw.strip() or raw.strip() in ("-", "—", "?"):
                    status = "missing"
                elif scalar(raw) is None:
                    status = "qualified_or_unparsed"
                else:
                    status = "numeric_literal"
                out.append(
                    dict(
                        id=f'{t["source_id"]}:{t["table_id"]}:l{row["line"]}:c{col+1}',
                        source_id=t["source_id"],
                        source_url=t["source_url"],
                        pdf_blake3=t["pdf_blake3"],
                        pdf_page=t["pdf_page"],
                        printed_page=t["printed_page"],
                        table=t["table_id"],
                        metric_raw=row.get("label_raw", metric),
                        metric=metric,
                        value_raw=raw,
                        value=scalar(raw),
                        value_status=status,
                        context=ctx,
                        flags=flags,
                        review="page_layout_and_selected_cells_checked",
                        fit_eligible=False,
                        evidence_kind="manufacturer_compilation" if t["source_id"].startswith("dec-") else "research_report",
                        row_line=row["line"],
                        column=col + 1,
                    )
                )
    return out


@click.command("extract-pdf-tables")
@click.option(
    "--acquisition",
    type=click.Path(path_type=Path, exists=True),
    default=Path("research/data/classic/pdf-acquisition.jsonl"),
    show_default=True,
)
@click.option("--recipes", type=click.Path(path_type=Path, exists=True), default=ROOT / "recipes.json", show_default=True)
@click.option("--corrections", type=click.Path(path_type=Path, exists=True), default=ROOT / "corrections.json", show_default=True)
@click.option("--output", type=click.Path(path_type=Path), default=Path("data/derived/classic/pdf-tables"), show_default=True)
def extract_pdf_tables(acquisition, recipes, corrections, output):
    """Extract DEC section 7, SSCL tables, and Tomari/Hiraki appendix tables."""
    sources = {r["source_id"]: r for r in map(json.loads, acquisition.read_text().splitlines())}
    output.mkdir(parents=True, exist_ok=True)
    texts = {}
    for sid, source in sources.items():
        data = Path(source["blob_path"]).read_bytes()
        if blake3.blake3(data).hexdigest() != source["blake3"]:
            raise click.ClickException("source hash mismatch: " + sid)
        text = subprocess.run(["pdftotext", "-layout", source["blob_path"], "-"], check=True, capture_output=True).stdout.decode()
        texts[sid] = text
        (output / (sid + ".txt")).write_text(text)
    tables = []
    for recipe in json.loads(recipes.read_text()):
        source = sources[recipe["source_id"]]
        table = parse_table(recipe, texts[recipe["source_id"]].split("\f")[recipe["pdf_page"] - 1])
        table.update(schema_version=1, source_url=source["url"], pdf_blake3=source["blake3"], review_date="2026-09-26")
        tables.append(table)
    applied = correct(tables, json.loads(corrections.read_text()))
    labels_path = ROOT / "labels.json"
    labels = json.loads(labels_path.read_text())
    for table in tables:
        if table["orientation"] == "metrics_as_rows":
            for row in table["rows"]:
                row["label_checked"] = labels.get(row["label_raw"], row["label_raw"])
    obs = observations(tables)
    hardware = {}
    for table in tables:
        if table["source_id"] == "tomari-hiraki-2011" and table["table_id"].startswith("hardware"):
            for row in table["rows"]:
                record = dict(zip(table["fields"], row["cells"]))
                if record["machine"] in hardware:
                    raise ValueError("duplicate hardware key")
                hardware[record["machine"]] = dict(record, hardware_pdf_page=table["pdf_page"], hardware_row_line=row["line"])
    joined = []
    for table in tables:
        if table["source_id"] == "tomari-hiraki-2011" and table["table_id"].startswith("results"):
            for row in table["rows"]:
                record = dict(zip(table["fields"], row["cells"]))
                joined.append(
                    dict(
                        hardware[record["machine"]],
                        **{k: v for k, v in record.items() if k != "machine"},
                        results_pdf_page=table["pdf_page"],
                        results_row_line=row["line"],
                        source_url=table["source_url"],
                        pdf_blake3=table["pdf_blake3"],
                        fit_eligible=False,
                    )
                )
    write_csv(output / "tomari-configurations.csv", joined)
    # Simple reading aid; source cells and spans/fill-down remain in JSON.
    markdown = []
    for table in tables:
        headers = (
            ["Benchmark"] + [c["machine"] + " / " + c["os"] for c in table["columns"]]
            if table["orientation"] == "metrics_as_rows"
            else table["fields"]
        )
        markdown += [
            "## " + table["source_id"] + " — " + table["table_id"],
            "",
            "PDF page " + str(table["pdf_page"]) + "; printed " + table["printed_page"] + ".",
            "",
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]
        for row in table["rows"]:
            cells = (
                ([row.get("label_checked", row["label_raw"])] + row["cells"])
                if table["orientation"] == "metrics_as_rows"
                else row["cells"]
            )
            markdown.append("| " + " | ".join(c.replace("|", r"\|") for c in cells) + " |")
        markdown.append("")
    (output / "tables.md").write_text("\n".join(markdown) + "\n")
    for name, rows in [("tables", tables), ("observations", obs)]:
        (output / (name + ".jsonl")).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    write_csv(
        output / "observations.csv",
        [dict(r, context=json.dumps(r["context"], ensure_ascii=False), flags=";".join(r["flags"])) for r in obs],
    )
    summary = [
        dict(
            source_id=sid,
            table_parts=sum(t["source_id"] == sid for t in tables),
            rows=sum(len(t["rows"]) for t in tables if t["source_id"] == sid),
            observations=sum(r["source_id"] == sid for r in obs),
            numeric_values=sum(r["source_id"] == sid and r["value_status"] == "numeric_literal" for r in obs),
        )
        for sid in sources
    ]
    write_csv(output / "summary.csv", summary)
    paired = [
        (scalar(r["Dhrystone2.1_DMIPS"]), scalar(r["CINT2006_reported"]))
        for r in joined
        if scalar(r["CINT2006_reported"]) is not None
    ]
    correlation = statistics.correlation([x for x, y in paired], [y for x, y in paired])
    audit = dict(
        tomari_table_check=dict(
            hardware_rows=len(hardware),
            results_rows=len(joined),
            paired_cint_rows=len(paired),
            pearson_r=correlation,
            published_r=0.986,
            agrees_at_published_precision=round(correlation, 3) == 0.986,
        ),
        method="classic-source-pdf-tables-v1",
        input_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [acquisition, recipes, corrections, labels_path]},
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        text_sha256={sid: hashlib.sha256(t.encode()).hexdigest() for sid, t in texts.items()},
        pdftotext_version=subprocess.run(["pdftotext", "-v"], capture_output=True, text=True).stderr.splitlines()[0],
        corrections=len(applied),
        observation_status=dict(Counter(r["value_status"] for r in obs)),
        output_sha256={
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.suffix in (".csv", ".jsonl")
        },
    )
    audit["shared_code_sha256"] = code_hashes(Path(__file__))
    (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    click.echo(json.dumps(dict(output=str(output), sources=len(sources), table_parts=len(tables), observations=len(obs))))
