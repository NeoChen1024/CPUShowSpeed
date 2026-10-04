"""Source score parsing, independent of fitting commands."""

import re


def numeric(value):
    value = str(value).strip().rstrip("*")
    if not re.fullmatch(r"(?:\d+(?:\.\d*)?|\.\d+)", value):
        return None
    x = float(value)
    return x if x > 0 else None


def linpack_n100(record, pages):
    """Read only the n=100 column using this physical page's aligned header."""
    match = re.fullmatch(r"pdf:page:(\d+):line:(\d+)", record["locator"])
    if not match:
        return None
    page, line = map(int, match.groups())
    lines = pages[page - 1].splitlines()
    raw = lines[line - 1]
    if raw != record["raw_record"]:
        raise ValueError(f"LINPACK locator mismatch: {record['id']}")
    header = next((s for s in lines[:12] if re.search(r"n=100\s", s)), None)
    if header is None:
        return None
    start = header.index("n=100")
    # pdftotext aligns values slightly left of the header. Restrict to this
    # column, never fall back to the first numeric compiler/TPP/peak token.
    value = raw[max(0, start - 4) : start + 7].strip()
    return numeric(value)


TARGETS = ("SPECmark89", "SPECint89", "SPECfp89", "SPECrate_base_int92", "SPECrate_int92")
