"""Reviews (schema step 4): judgements that qualify extracted evidence without editing it.

A review targets one reported date of a result (`result_date`), two results treated as
one configuration (`result_pair`) or two source system texts that may denote one
machine (`system_link`). Targets are selectors resolved at build time against the
extracted result records and hardware records; a selector that matches nothing is
reported, never dropped silently. Rejected result dates leave the chronology
candidates (also as model-level dates for other results) but stay in the extracted
records. Aliases and date events carry their own status and need no review row.
"""

import json
from collections import Counter, defaultdict

from cpushowspeed.curated_dates import RESULTS


def build_reviews(db, tables):
    """Resolve review selectors: review_result (one row per matched result) and review_system_link."""
    db.execute(
        "CREATE TABLE review_result (review_id TEXT, target_kind TEXT, side TEXT, field TEXT, decision TEXT, result_id TEXT)"
    )
    db.execute(
        "CREATE TABLE review_system_link (review_id TEXT PRIMARY KEY, decision TEXT, left_system_ids TEXT, "
        "right_system_ids TEXT, same_model INTEGER)"
    )
    db.execute("CREATE TABLE review_finding (review_id TEXT, finding TEXT, detail TEXT)")
    if not RESULTS.exists():
        return {"reviews": "skipped: run `cpushowspeed data extract`"}
    by_id, by_text = set(), defaultdict(list)
    for line in RESULTS.read_text().splitlines():
        r = json.loads(line)
        by_id.add(r["result_id"])
        by_text[r["scope"], r["system"]].append(r["result_id"])
    systems = defaultdict(set)
    for scope, system, system_id in db.execute("SELECT scope, system, system_id FROM hardware_record"):
        systems[scope, system].add(system_id)
    counts = Counter()

    def finding(review, kind, detail):
        db.execute("INSERT INTO review_finding VALUES (?, ?, ?)", (review["review_id"], kind, detail))
        counts[f"finding:{kind}"] += 1

    def matched(selector):
        if "result_id" in selector:
            return [selector["result_id"]] if selector["result_id"] in by_id else []
        return by_text.get((selector["scope"], selector["system"]), [])

    for review in tables.get("review", []):
        kind, target = review["target_kind"], review["target"]
        counts[f"{kind}:{review['decision']}"] += 1
        if kind == "system_link":
            sides = [
                sorted(x for x in systems.get((target[s]["scope"], target[s]["system"]), set()) if x) for s in ("left", "right")
            ]
            if not all(systems.get((target[s]["scope"], target[s]["system"])) for s in ("left", "right")):
                finding(review, "target_unmatched", json.dumps(target, ensure_ascii=False))
            same = bool(sides[0]) and sides[0] == sides[1]
            if same and review["decision"] != "accept":
                finding(review, "unreviewed_link_merged_by_rule", f"both texts resolve to {sides[0][0]}")
            db.execute(
                "INSERT INTO review_system_link VALUES (?, ?, ?, ?, ?)",
                (review["review_id"], review["decision"], json.dumps(sides[0]), json.dumps(sides[1]), int(same)),
            )
            continue
        for side, selector in [(None, target)] if kind == "result_date" else [("left", target["left"]), ("right", target["right"])]:
            ids = matched(selector)
            if not ids:
                finding(review, "target_unmatched", json.dumps(selector, ensure_ascii=False))
            db.executemany(
                "INSERT INTO review_result VALUES (?, ?, ?, ?, ?, ?)",
                [(review["review_id"], kind, side, review.get("field"), review["decision"], rid) for rid in ids],
            )
    return {f"reviews:{k}": str(v) for k, v in sorted(counts.items())}


def rejected_dates(db):
    """{(result_id, field): review_id} for rejected result dates."""
    return {
        (rid, field): review_id
        for review_id, rid, field in db.execute(
            "SELECT review_id, result_id, field FROM review_result WHERE target_kind = 'result_date' AND decision = 'reject'"
        )
    }
