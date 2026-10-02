"""One parser for Netlib PDS SPEC CPU92 disclosure pages (CINT92, CFP92 and their rate forms).

Every page carries the same 21 labelled fields; all are kept verbatim, together with
the issue heading, the result table, the reported means and the tuning notes. Track
adapters validate scores; this module only reads what the page states.
"""

from __future__ import annotations

import re
from datetime import datetime

FIELDS = (
    "Model Number",
    "CPU",
    "FPU",
    "Number of CPUs",
    "Primary Cache",
    "Secondary Cache",
    "Other Cache",
    "Memory",
    "Disk Subsystem",
    "Other Hardware",
    "O/S & Version",
    "Compilers & Version",
    "Other Software",
    "File System Type",
    "System State",
    "Hardware Availability",
    "Software Availability",
    "License #",
    "Tested",
    "By",
    "Of",
)
MONTH_FIELDS = {
    "Hardware Availability": "hardware_availability_month",
    "Software Availability": "software_availability_month",
    "Tested": "test_month",
}
_FIELD = re.compile(r"^<D[TD]>\s*(" + "|".join(re.escape(f) for f in FIELDS) + r")\s*:\s*(.*)$")
_ISSUE = re.compile(r"<H2>\s*(SPEC\w+)\s*\(Volume\s+(\d+),\s*Issue\s+(\d+),\s*([A-Za-z]+\s+\d{4})\)\s*</H2>", re.I)
_MEAN = re.compile(r"(?:<DD>|Geometric Mean\s*\()\s*(SPEC\w+?92)\)?:\s*([0-9]+(?:\.[0-9]+)?|-)", re.I)


def text(value: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", value).split())


def month(value: str) -> str | None:
    """'Jan-94' -> '1994-01'; anything else (such as '######') is not a date."""
    try:
        return datetime.strptime(value.strip(), "%b-%y").strftime("%Y-%m")
    except ValueError:
        return None


def parse(document: str) -> dict:
    """Read one disclosure page; raises ValueError only when its fixed structure is absent."""
    issue = _ISSUE.search(document)
    if issue is None:
        raise ValueError("missing issue heading")
    headings = [text(h) for h in re.findall(r"<H3>(.*?)</H3>", document, re.I | re.S)]
    if len(headings) < 2:
        raise ValueError("missing vendor/system headings")
    fields, current = {}, None
    notes, note = [], None
    for line in document.splitlines():
        match = _FIELD.match(line)
        if match:
            label = match[1]
            if label in fields:
                raise ValueError(f"repeated field: {label}")
            fields[label] = [text(match[2])]
            current = label if label == "Compilers & Version" else None
            continue
        heading = re.match(r"<DT><STRONG>(.*Notes.*?):?</STRONG>", line, re.I)
        if heading:
            note = dict(heading=text(heading[1]).rstrip(":"), lines=[])
            notes.append(note)
            current = None
            continue
        if line.startswith("<DD>"):
            value = text(line[4:])
            if current and value:
                fields[current].append(value)
            elif note is not None and value:
                note["lines"].append(value)
        elif re.match(r"<DT>", line) and not line.strip() == "<DT>":
            current = None
    missing = [f for f in FIELDS if f not in fields]
    if missing:
        raise ValueError("missing fields: " + ", ".join(missing))
    table = []
    for block in re.findall(r"<STRONG>Results:</STRONG>\s*<PRE>(.*?)</PRE>", document, re.I | re.S):
        for row in block.splitlines():
            parts = row.split()
            if parts and re.fullmatch(r"\d{3}\.\w+", parts[0]):
                table.append([parts[0], *parts[1:]])
    means = {}
    for name, value in _MEAN.findall(document):
        if name in means and means[name] != value:
            raise ValueError(f"conflicting reported means: {name}")
        means[name] = value
    record = dict(
        metric_heading=issue[1],
        volume=int(issue[2]),
        issue=int(issue[3]),
        publication_month=datetime.strptime(issue[4], "%B %Y").strftime("%Y-%m"),
        company=headings[0],
        system=headings[1],
        fields={label: "; ".join(fields[label]) for label in FIELDS},
        table=table,
        reported_means=means,
        notes=notes,
    )
    for label, key in MONTH_FIELDS.items():
        record[key] = month(fields[label][0])
    return record
