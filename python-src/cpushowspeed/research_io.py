"""CSV policies shared by research pipelines; source bytes remain immutable."""

import csv
from pathlib import Path


def read_csv(path, *, encoding=None):
    with Path(path).open(encoding=encoding, newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows, *, fields=None, lineterminator="\r\n", empty_text=None):
    if not rows and empty_text is not None:
        Path(path).write_text(empty_text)
        return
    fields = fields if fields is not None else list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fields, lineterminator=lineterminator)
        writer.writeheader()
        writer.writerows(rows)


def code_hashes(entry):
    """Hash local static import closure, so extracted helpers remain in provenance."""
    import ast
    import hashlib

    package = Path(__file__).resolve().parent
    pending = [Path(entry)]
    result = {}
    while pending:
        path = pending.pop().resolve()
        if str(path) in result or not path.is_file():
            continue
        content = path.read_bytes()
        result[str(path)] = hashlib.sha256(content).hexdigest()
        for node in ast.walk(ast.parse(content)):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("cpushowspeed."):
                base = package.joinpath(*node.module.split(".")[1:])
                pending.append(base.with_suffix(".py"))
                pending += [base / f"{alias.name}.py" for alias in node.names]
    return dict(sorted(result.items()))
