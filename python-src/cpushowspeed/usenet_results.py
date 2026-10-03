"""Result tables posted to Usenet (UTZOO archive), parsed from the stored message bytes.

Each parser reads raw message blobs named by curated `source` rows and checks the
posting against an independent copy (a second sort order, or the raw database
against its printed report) before yielding records.
"""

import json
import re
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path

from cpushowspeed.curated import CURATED


def sources():
    return {s["source_id"]: s for s in map(json.loads, (CURATED / "source.jsonl").read_text().splitlines())}


def message(source_id, table=None):
    """Message text of a stored Usenet post (Latin-1, as posted)."""
    s = (table or sources())[source_id]
    return Path(s["local_path"]).read_bytes().decode("latin-1")


def shar_files(text):
    """{name: body} for shell-archive members written with `sed 's/^X//'` or `cat` heredocs."""
    out = {}
    pattern = r"(sed 's/\^X//'|cat) << \\?'?SHAR_EOF'? > '([^']+)'\n(.*?)\nSHAR_EOF\n"
    for m in re.finditer(pattern, text, re.S):
        body = m.group(3)
        if m.group(1) != "cat":
            body = "\n".join(line[1:] if line.startswith("X") else line for line in body.split("\n"))
        out[m.group(2)] = body
    return out


def _uu_line(line):
    """One uuencoded line; decoded by hand because binascii rejects some valid short final lines."""
    n = (ord(line[0]) - 32) & 63
    need = 1 + (n + 2) // 3 * 4
    vals = [(ord(c) - 32) & 63 for c in line[1:need].ljust(need - 1, " ")]
    out = bytearray()
    for i in range(0, len(vals) - 3, 4):
        a, b, c, d = vals[i : i + 4]
        out += bytes([(a << 2 | b >> 4) & 255, (b << 4 | c >> 2) & 255, (c << 6 | d) & 255])
    return bytes(out[:n])


def uudecode(body):
    lines = body.split("\n")
    start = next(i for i, line in enumerate(lines) if line.startswith("begin "))
    out = bytearray()
    for line in lines[start + 1 :]:
        if line.strip() == "end":
            break
        if line and (ord(line[0]) - 32) & 63:
            out += _uu_line(line)
    data = bytes(out)
    if data[:2] == b"\x1f\x9d":  # compress(1)
        data = subprocess.run(["gzip", "-dc"], input=data, capture_output=True, check=True).stdout
    return data.decode("latin-1")


def prelude_rows(text):
    """Rows of a Prelude database: a typed header line, a dash line, then tab-separated rows."""
    lines = text.split("\n")
    header = [h.split(":")[0] for h in lines[0].split("\t")]
    rows = [dict(zip(header, line.split("\t"))) for line in lines[2:] if line.strip()]
    if any(len(r) != len(header) for r in rows):
        raise ValueError("Prelude row width differs from its header")
    return rows


# Richardson's Dhrystone collection. Non-C rows run Weicker's Pascal or Ada versions of the program.
NOT_C = re.compile(r"pascal|\bada\b|-ada|^(/usr/ucb/)?pc$", re.I)
REPORT_ROW = re.compile(r"^(.{10}) (.{10}) (.{8})\s*(-?[\d.]+)\s+(-?\d+)\s+(-?\d+) (.*)$")
DHRY11_REPORT = "src:richardson-dhrystone-1.1-1987-09-20"
DHRY11_DB = "src:richardson-dhrystone-1.1-db-1987-05-18"
DHRY2_DB = "src:richardson-dhrystone-2-db-1989-04-30"
DHRY2_REPORT = "src:richardson-dhrystone-2-1989-04-30"


def _number(text):
    text = (text or "").strip()
    return float(text) if re.fullmatch(r"-?\d+(\.\d+)?", text) else None


DATE_FORMATS = (
    "%m/%d/%y",
    "%m/%d/%Y",
    "%m-%d-%y",
    "%d-%b-%y",
    "%d-%b-%Y",
    "%d-%B-%Y",
    "%b %d, %Y",
    "%d %b. %Y",
    "%a %b %d %H:%M:%S PST %Y",
)


def iso_date(text):
    """A submission date as YYYY-MM-DD; numeric dates are US month/day/year, as the lists print them."""
    text = " ".join(text.split())
    for form in DATE_FORMATS:
        try:
            return datetime.strptime(text, form).date().isoformat()
        except ValueError:
            pass
    return None


def _dhrystone_record(source_id, key, version, row, locator):
    noreg, reg = _number(row.get("NOREG")), _number(row.get("REG"))
    score, variant = (reg, "register") if reg and reg > 0 else (noreg, "no register")
    compiler = (row.get("COMPILER") or "").strip()
    excluded = None
    if not score or score <= 0:
        excluded = "no positive score (zero, blank or overflowed negative)"
    elif NOT_C.search(compiler):
        excluded = "not the C program (" + compiler + ")"
    clock = _number(row.get("CLOCK"))
    return dict(
        source_id=source_id,
        key=key,
        locator=locator,
        dhrystone_version=version,
        manufacturer=row["MANUF"].strip(),
        model=row["MODEL"].strip(),
        processor=row["PROC"].strip(),
        clock_mhz=clock if clock and clock > 0 else None,
        os=" ".join(x for x in (row.get("OS", "").strip(), row.get("OVERSION", "").strip()) if x),
        compiler=" ".join(x for x in (compiler, row.get("CVERSION", "").strip()) if x),
        options=(row.get("OPTIONS") or "").strip(),
        notes=(row.get("NOTES") or "").strip(),
        noreg=noreg,
        reg=reg,
        dhrystones_per_second=score,
        variant=variant,
        submitted=(row.get("DATE") or "").strip(),
        submitted_on=iso_date(row.get("DATE") or ""),
        submitter=(row.get("SUBMITTER") or "").strip(),
        excluded=excluded,
    )


def dhrystone11():
    """Final Dhrystone 1.1 list (1987-09-20); submission dates from the 1987-05-18 database where a row matches."""
    table = sources()
    report = shar_files(message(DHRY11_REPORT, table))["report.doc"].split("\n")
    rows = [m for m in map(REPORT_ROW.match, report) if m]
    half = len(rows) // 2
    by_manuf, by_perf = rows[:half], rows[half:]
    signature = lambda m: tuple(g.strip() for g in m.groups())
    if len(rows) % 2 or Counter(map(signature, by_manuf)) != Counter(map(signature, by_perf)):
        raise ValueError("Dhrystone 1.1 report: the manufacturer and performance listings differ")
    db = prelude_rows(shar_files(message(DHRY11_DB, table))["dry.db"])
    dated = {}
    for r in db:
        k = (r["MANUF"].strip(), r["MODEL"].strip(), int(_number(r["NOREG"]) or 0), int(_number(r["REG"]) or 0))
        dated.setdefault(k, []).append(r)
    for i, m in enumerate(by_manuf, 1):
        manuf, model, proc, clock, noreg, reg, rest = (g.strip() for g in m.groups())
        os_text, _, tail = rest.partition(",")
        compiler, _, notes = tail.partition(",")
        row = dict(
            MANUF=manuf, MODEL=model, PROC=proc, CLOCK=clock, OS=os_text, COMPILER=compiler, NOREG=noreg, REG=reg, NOTES=notes
        )
        match = dated.get((manuf, model, int(noreg), int(reg)))
        if match:
            row.update(DATE=match.pop(0)["DATE"])
            row["SUBMITTER"] = ""  # the report omits submitters; dates only are carried
        locator = f"report.doc, 'SORTED BY MANUFACTURER' row {i}"
        yield _dhrystone_record(DHRY11_REPORT, f"row{i:03d}", "1.1", row, locator)


def _report_boxes(printed):
    """Rows of a boxed report: the header row (repeated on each page) names the columns; wrapped cells are joined."""
    header, boxes, cells = None, [], None
    for line in printed.split("\n"):
        if not line.startswith("|") or line.startswith("|--"):
            continue
        parts = line.split("|")[1:-1]
        names = [p.strip().upper() for p in parts]
        if header is None or names == header:
            header = names
        elif line.startswith("|__"):
            boxes.append({h: "".join(c) for h, c in zip(header, cells)})
            cells = None
        else:
            cells = cells or [[] for _ in header]
            for c, p in zip(cells, parts):
                c.append(p.strip())
    return boxes


def _dhrystone2_key(row):
    return int(_number(row["NOREG"]) or 0), int(_number(row["REG"]) or 0), row["DATE"].strip()


def dhrystone2():
    """Dhrystone 2.0/2.1 raw database (1989-04-30), checked against the printed by-performance report."""
    table = sources()
    db = prelude_rows(uudecode(shar_files(message(DHRY2_DB, table))["raw.UU"]))
    printed = uudecode(shar_files(message(DHRY2_REPORT, table))["byperf.UU"])
    if Counter(map(_dhrystone2_key, _report_boxes(printed))) != Counter(map(_dhrystone2_key, db)):
        raise ValueError("Dhrystone 2 raw database differs from its printed report")
    for i, row in enumerate(db, 1):
        yield _dhrystone_record(DHRY2_DB, f"row{i:03d}", "2.0 or 2.1", row, f"raw.db row {i}")


def richardson_dhrystone():
    yield from dhrystone11()
    yield from dhrystone2()
