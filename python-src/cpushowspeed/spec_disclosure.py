"""Source-preserving extraction of declared SPEC execution resources, not CPU capacity."""

import csv
import hashlib
import io
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


class TableRows(HTMLParser):
    """Accept old SPEC tables with omitted TD/TH/TR closing tags."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.row, self.cell = [], [], None

    def flush_cell(self):
        if self.cell is not None:
            self.row.append(" ".join(" ".join(self.cell).split()))
            self.cell = None

    def flush_row(self):
        self.flush_cell()
        if self.row:
            self.rows.append(self.row)
        self.row = []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.flush_row()
        elif tag in ("td", "th"):
            self.flush_cell()
            self.cell = []
        elif tag == "br" and self.cell is not None:
            self.cell.append(" ")

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self.flush_cell()
        elif tag in ("tr", "table"):
            self.flush_row()

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def canonical(value):
    return re.sub(r"[^a-z0-9]", "", value.lower())


def integer(value):
    text = str(value).strip()
    return int(text) if re.fullmatch(r"[1-9]\d*", text) else None


def parse_disclosure(body, suffix, generation, track):
    text = body.decode("utf-8", errors="replace") if suffix == ".csv" else body.decode("latin1")
    if suffix == ".csv":
        rows = list(csv.reader(io.StringIO(text)))
    else:
        parser = TableRows()
        parser.feed(text)
        parser.flush_row()
        rows = parser.rows
    hardware = {}
    aliases = {
        "cpusenabled": "enabled",
        "enabled": "enabled",
        "cpuname": "processor",
        "cpucharacteristics": "processor_characteristics",
        "cpusorderable": "orderable",
        "nominal": "nominal_mhz",
        "cpumhz": "nominal_mhz",
        "maxmhz": "max_mhz",
        "memory": "memory",
        "autoparallel": "parallel",
        "parallel": "parallel",
        "basepointers": "base_pointer_size",
        "peakpointers": "peak_pointer_size",
    }
    execution, header, section = [], None, ""
    quantity = "copies" if track == "rate" else "threads"
    for row_number, row in enumerate(rows, 1):
        if not row:
            continue
        if len(row) == 1 and "Results Table" in row[0]:
            section = row[0]
        for index, cell in enumerate(row):
            if canonical(cell) in aliases and index + 1 < len(row):
                hardware[aliases[canonical(cell)]] = " ".join(row[index + 1 :]).strip()
        labels = [canonical(c) for c in row]
        if any(c in ("benchmark", "benchmarkandname") for c in labels) or any("benchmark" in c and "name" in c for c in labels):
            if any(quantity in c for c in labels):
                header = labels
            else:
                header = None
            continue
        if header is None:
            continue
        bench = next((v for v in row if re.fullmatch(r"\d{3}\.[\w]+", v.strip())), None)
        if bench is None:
            continue
        for mode in ("base", "peak"):
            # CPU2000's unlabeled second half denotes peak.
            indexes = [
                i for i, c in enumerate(header) if quantity in c and (c.startswith(mode) or (mode == "peak" and c == quantity))
            ]
            for i in indexes:
                if i >= len(row):
                    continue
                value = integer(row[i])
                if value is None:
                    continue
                selected_index = next((j for j, c in enumerate(header) if c == mode + "selected"), None)
                if suffix == ".csv" and "Selected Results Table" not in section and selected_index is not None:
                    if selected_index >= len(row) or row[selected_index] != "1":
                        continue
                execution.append(
                    dict(
                        benchmark=bench,
                        mode=mode,
                        quantity=quantity,
                        value=value,
                        locator=f"{section or 'results table'} row {row_number}",
                        raw_value=row[i],
                    )
                )
    # Prefer the explicit selected table when both full/selected tables exist.
    selected = [r for r in execution if r["locator"].startswith("Selected Results Table")]
    if selected:
        execution = selected
    unique = {}
    for row in execution:
        unique[row["benchmark"], row["mode"], row["quantity"], row["value"]] = row
    execution = list(unique.values())
    normalized = {}
    enabled = hardware.get("enabled", "")
    for name, pattern in (
        ("enabled_cores", r"\b(\d+)\s+cores?\b(?!\s*/)"),
        ("enabled_chips", r"\b(\d+)\s+chips?\b"),
        ("threads_per_core", r"\b(\d+)\s+threads?\s*/\s*core"),
        ("cores_per_chip", r"\b(\d+)\s+cores?\s*/\s*chip"),
    ):
        match = re.search(pattern, enabled, re.I)
        if match:
            normalized[name] = int(match[1])
    if enabled.strip().isdigit():
        normalized["legacy_enabled_cpus"] = int(enabled.strip())
    modes = {}
    for mode in ("base", "peak"):
        values = [r["value"] for r in execution if r["mode"] == mode]
        modes[mode] = dict(
            quantity=quantity,
            status="reported" if values else "not_reported_in_parsed_table",
            minimum=min(values) if values else None,
            maximum=max(values) if values else None,
        )
    return dict(generation=generation, track=track, hardware_raw=hardware, hardware=normalized, execution=execution, modes=modes)


def disclosure_path(raw_dir, source_url, suffix):
    path = Path(urlparse(source_url).path)
    return raw_dir / path.parts[1] / path.parent.name / path.with_suffix(suffix).name


def load_disclosure(raw_dir, source_url, generation, track):
    for suffix in (".csv", ".html"):
        path = disclosure_path(raw_dir, source_url, suffix)
        if not path.exists():
            continue
        body = path.read_bytes()
        meta = json.loads(path.with_name(path.name + ".meta.json").read_text())
        digest = hashlib.sha256(body).hexdigest()
        if digest != meta["sha256"]:
            raise ValueError("disclosure hash mismatch: " + str(path))
        if Path(urlparse(meta["source_url"]).path).name != path.name:
            raise ValueError("disclosure source mismatch: " + str(path))
        return dict(
            parse_disclosure(body, suffix, generation, track),
            source_url=source_url,
            document_url=meta["source_url"],
            source_sha256=digest,
            source_path=str(path),
            status="parsed",
        )
    return dict(source_url=source_url, generation=generation, track=track, status="not_collected")
