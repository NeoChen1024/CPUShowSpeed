"""Shared CPU > hardware > submission chronology selection; retain all candidates."""

import re
from collections import defaultdict


def date_year(value):
    match = re.fullmatch(r"((?:19|20)\d{2})(?:-\d{2}(?:-\d{2})?)?", str(value or ""))
    return int(match[1]) if match else None


def candidate(kind, date, source_url, method, notes="", low=None, high=None):
    y = date_year(date)
    if y is None:
        return None
    return dict(
        kind=kind,
        date=str(date),
        year=y,
        year_low=int(low or y),
        year_high=int(high or y),
        source_url=source_url,
        method=method,
        notes=notes,
    )


def select_date(candidates, submission_review=None):
    valid = []
    for c in candidates:
        if c is not None and c not in valid:
            valid.append(c)
    # A review vetoes only the fallback date, never the benchmark observation.
    if submission_review:
        if submission_review["decision"] not in ("accept", "reject"):
            raise ValueError("invalid submission date review decision")
        submissions = [c for c in valid if c["kind"] == "submission"]
        if not submissions or any(c["date"] != submission_review["submission_date"] for c in submissions):
            raise ValueError("stale submission date review")
        valid = [
            (
                dict(c, eligible=submission_review["decision"] == "accept", review=dict(submission_review))
                if c["kind"] == "submission"
                else c
            )
            for c in valid
        ]
    for kind in ("cpu", "hardware", "submission"):
        matches = [c for c in valid if c["kind"] == kind and c.get("eligible", True)]
        if not matches:
            continue
        years = sorted({c["year"] for c in matches})
        # A conflict spans the evidence; the display midpoint is not a new historical claim.
        mid = (years[(len(years) - 1) // 2] + years[len(years) // 2]) // 2
        return dict(
            year=mid,
            year_low=min(c["year_low"] for c in matches),
            year_high=max(c["year_high"] for c in matches),
            date_status="estimated",
            date_kind=kind,
            date_method="selected_" + kind + "_year",
            date_sources=";".join(sorted({c["source_url"] for c in matches if c["source_url"]})),
            date_notes=" | ".join(dict.fromkeys(c["notes"] for c in matches if c["notes"])),
            date_candidates=valid,
        )
    return dict(
        year="",
        year_low="",
        year_high="",
        date_status="unknown",
        date_kind="unknown",
        date_method="unknown",
        date_sources="",
        date_notes=" | ".join(c.get("review", {}).get("reason", "") for c in valid if not c.get("eligible", True)),
        date_candidates=valid,
    )


def cpu_key(name, clock):
    if not name or not clock:
        return None
    # Conservative exact CPU text plus clock. Do not infer families from vague names.
    return (re.sub(r"[^a-z0-9]", "", name.lower()), round(float(clock), 1))


class CPUChronology:
    def __init__(self, proxies):
        self.by_id = {r["configuration_id"]: r for r in proxies}
        self.by_cpu = defaultdict(list)
        for r in proxies:
            key = cpu_key(r["cpu"], r["clock_mhz"])
            if key:
                self.by_cpu[key].append(r)

    def lookup(self, row):
        direct = self.by_id.get(row["configuration_id"])
        if direct:
            if (
                row["system"] != direct["system"]
                or row["cpu"] != direct["cpu"]
                or (
                    (float(row["clock_mhz"]) if row["clock_mhz"] else None)
                    != (float(direct["clock_mhz"]) if direct["clock_mhz"] else None)
                )
            ):
                raise ValueError("stale CPU chronology identity: " + row["configuration_id"])
            matches = [direct]
        else:
            matches = self.by_cpu.get(cpu_key(row["cpu"], row["clock_mhz"]), [])
        result = {}
        for r in matches:
            c = candidate(
                "cpu",
                r["release_date"],
                r["source_url"],
                "reviewed_cpu_release",
                "CPU release, not complete-system availability. " + r["notes"],
            )
            if c:
                result[c["date"], c["source_url"]] = c
        return list(result.values())
