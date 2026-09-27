"""Source-paired native SPEC integer bridge evidence."""

import math
import statistics
from collections import defaultdict

from cpushowspeed.classic_overlap import model_key


def bridge_rows(path):
    # utf-8-sig preserves the archive's BOM without changing its bytes.
    import csv

    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return [
        dict(r, model_key=model_key(r["system"]), log_ratio=math.log(float(r["SPECint92"]) / float(r["SPECint89"])))
        for r in rows
        if r["SPECint89"] and r["SPECint92"]
    ]


def bridge_centers(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[r["model_key"]].append(float(r["log_ratio"]))
    return {k: statistics.median(v) for k, v in groups.items()}
