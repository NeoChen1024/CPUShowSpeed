"""Mode-specific execution evidence. Never scale scores by worker count."""

POLICY = "reject-known-uniform-count-conflicts-v1"


def agreement(left, right, mode):
    if not left.track or left.track != right.track:
        return "different_or_unspecified_track"
    quantities = [r.execution.get("modes", {}).get(mode, {}) for r in (left, right)]
    if any(q.get("status") != "reported" for q in quantities):
        return "unverified"
    if any(q.get("minimum") is None or q.get("maximum") is None for q in quantities):
        return "unverified"
    if any(q["minimum"] != q["maximum"] for q in quantities):
        return "nonuniform_requires_review"
    if quantities[0].get("quantity") != quantities[1].get("quantity"):
        return "different_quantity"
    return "equal_declared_count" if quantities[0]["minimum"] == quantities[1]["minimum"] else "confirmed_count_conflict"
