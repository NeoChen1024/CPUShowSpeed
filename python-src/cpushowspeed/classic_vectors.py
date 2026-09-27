"""Exact-observation pair/triple assembly shared by experiments."""

import itertools
import json
import math
import statistics
from collections import defaultdict


def composites(pairs, stage, targets=("SPECint89", "SPECint92")):
    rows = []
    groups = defaultdict(list)
    for r in pairs:
        if r["stage"] != stage or r["target"] not in targets:
            continue
        metrics = r["pattern"].split("+")
        members = tuple((m, r[key + "_id"], float(r[key])) for m, key in zip(metrics, ("first", "second")))
        item = dict(r, members=members)
        rows.append(item)
        groups[r["model_key"], r["spec_id"], r["target"], r["origin"], r["y"]].append(item)
    # A triple must have all three compatible pair edges for this exact target
    # and exact classical record/value identities. Joining is not replication.
    for group in groups.values():
        edges = {frozenset(r["members"]) for r in group}
        nodes = sorted(set(itertools.chain.from_iterable(edges)))
        for combo in itertools.combinations(nodes, 3):
            if len({n[0].split(":")[0] for n in combo}) != 3:
                continue
            if all(frozenset(edge) in edges for edge in itertools.combinations(combo, 2)):
                supporting = [r for r in group if set(r["members"]).issubset(combo)]
                rows.append(
                    dict(
                        group[0],
                        pattern="+".join(n[0] for n in combo),
                        members=combo,
                        provenance=json.dumps([r["provenance"] for r in supporting]),
                    )
                )
    for r in rows:
        r["member_ids"] = json.dumps([n[1] for n in r["members"]])
        r["member_values"] = json.dumps([n[2] for n in r["members"]])
        r["x"] = math.exp(statistics.mean(math.log(n[2]) for n in r["members"]))
        r["generation"] = "89" if r["target"] == "SPECint89" else "92"
        r["raw_target"] = float(r["y"])
        r["z"] = math.log(r["raw_target"] / r["x"])
        del r["members"]
    return rows
