"""Observed benchmark/configuration nodes for sparse joint calibration."""

import json
import math
import re
from collections import defaultdict

from cpushowspeed.benchmark_records import classical_values as values
from cpushowspeed.calibration import ANCHOR
from cpushowspeed.classic_overlap import model_key, relaxed_key
from cpushowspeed.classic_values import linpack_n100, numeric


def family(metric):
    return metric.split(":", 1)[0]


def clock_adjust(score, metric, measured, target, scaling):
    """Unknown clocks stay unknown; LINPACK is never clock-scaled."""
    measured, target = numeric(measured), numeric(target)
    conflict = measured and target and abs(measured - target) > 0.01 * max(measured, target)
    if conflict and (not scaling or family(metric) == "LINPACK"):
        return None, 1.0, "clock_conflict"
    if scaling and family(metric) in ("Dhrystone", "Whetstone") and measured and target:
        return score * target / measured, target / measured, "linear_clock_assumption"
    return score, 1.0, "unknown_clock_unscaled" if not measured or not target else "compatible_clock"


def cpu_identity(text):
    text = str(text or "").lower()
    text = re.sub(r"\b[0-9.]+\s*(?:mhz|ghz)\b", "", text)
    compact = re.sub(r"[^a-z0-9]", "", text)
    # Preserve revisions and LC variants. A generic ISA is not a CPU identity.
    match = re.search(
        r"7100lc|7100|7200|7300lc|7300|21064a?|21066a?|21164a?|r[234568]000[a-z]*|cy7c601|ti390c601|680[2346]0", compact
    )
    if match:
        return match[0]
    if "weitek" in compact:
        return "weitek"
    for vendor in ("intel", "motorola", "digital", "dec"):
        if compact.startswith(vendor):
            compact = compact[len(vendor) :]
    if re.fullmatch(r"(?:80[2345]86|i?486|680[2346]0)[a-z0-9]*", compact):
        return compact.removeprefix("i")
    return None


def scaling_cpu_check(classical, spec):
    a, b = cpu_identity(classical.get("processor_raw")), cpu_identity(spec.get("processor_raw"))
    if a is None or b is None:
        return "cpu_identity_unverified"
    return "cpu_identity_compatible" if a == b else "cpu_identity_conflict"


def reference_record(spec):
    raw = spec["raw_record"]
    return isinstance(raw, dict) and (
        raw.get("measurement_type") == "reference_definition" or "reference_definition" in raw.get("review_flags", "")
    )


def build(classical, specs, pairs, vectors, matching, pages, scaling, target_metric="SPECrate_int92", target_scale=None):
    if target_metric not in {"SPECrate_int92", "SPECint92"}:
        raise ValueError("unsupported calibration target")
    if target_scale is None:
        target_scale = ANCHOR if target_metric == "SPECrate_int92" else 1.0
    observed_kind = "observed_rate" if target_metric == "SPECrate_int92" else "observed_speed"
    nodes = {}
    observations = []
    audit = []
    used = set()
    # Use the existing clock-corroborated identity normalization for fold grouping.
    keys = {r["id"]: relaxed_key(r["system"], numeric(r.get("clock_mhz"))) for r in list(classical.values()) + list(specs.values())}
    # Fold/bootstrap identity joins every alias already accepted by pairing.
    # This prevents an observation reappearing under a frequency-suffix alias.
    parent = {}

    def find(k):
        parent.setdefault(k, k)
        if parent[k] != k:
            parent[k] = find(parent[k])
        return parent[k]

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[max(a, b)] = min(a, b)

    for r in list(classical.values()) + list(specs.values()):
        union(model_key(r["system"]), keys[r["id"]])
    for pair in pairs:
        union(keys[pair["classic_id"]], keys[pair["spec_id"]])
    for match in matching:
        if str(match["included"]).lower() == "true":
            v = next(v for v in vectors if v["id"] == match["vector_id"])
            union(v["model_key"], keys[match["spec_id"]])
    keys = {k: find(v) for k, v in keys.items()}
    scores = {k: values(r, pages) for k, r in classical.items() if r.get("reported_processor_count") in (None, 1)}

    def node(nid, key, system, kind="unanchored", target=None):
        if nid not in nodes:
            nodes[nid] = dict(node_id=nid, model_key=key, system=system, target_kind=kind, target=target, observations=[])
        return nodes[nid]

    def add(n, metric, oid, original, adjusted, multiplier, source, measured=None, target=None, policy="original", provenance=None):
        identity = (n["node_id"], metric, oid)
        if identity in used:
            return
        used.add(identity)
        row = dict(
            node_id=n["node_id"],
            model_key=n["model_key"],
            metric=metric,
            observation_id=oid,
            original_score=original,
            adjusted_score=adjusted,
            multiplier=multiplier,
            measured_clock_mhz=measured,
            target_clock_mhz=target,
            clock_policy=policy,
            source_url=source,
            provenance=json.dumps(provenance, sort_keys=True),
        )
        observations.append(row)
        n["observations"].append(row)

    # Anchor candidates accept a single available metric; pair intersections are unnecessary.
    for pair in pairs:
        c, s = classical[pair["classic_id"]], specs[pair["spec_id"]]
        if reference_record(s):
            continue
        rate = numeric(s["metrics_raw"].get(target_metric))
        old = numeric(s["metrics_raw"].get("SPECint89"))
        if not rate and not old:
            continue
        if rate and target_metric == "SPECrate_int92" and numeric(s.get("cpu_count")) != 1:
            continue
        for metric, score in scores.get(c["id"], {}).items():
            adjusted, multiplier, policy = clock_adjust(score, metric, c.get("clock_mhz"), s.get("clock_mhz"), scaling)
            cpu_check = scaling_cpu_check(c, s)
            if scaling and adjusted is not None and abs(multiplier - 1) > 1e-12:
                measured, target = numeric(c.get("clock_mhz")), numeric(s.get("clock_mhz"))
                if cpu_check != "cpu_identity_compatible":
                    if measured and target and abs(measured - target) <= 0.01 * max(measured, target):
                        adjusted, multiplier, policy = score, 1.0, "compatible_clock_no_scaling"
                    else:
                        adjusted, policy = None, cpu_check
            audit.append(
                dict(
                    cpu_check=cpu_check,
                    classic_id=c["id"],
                    spec_id=s["id"],
                    metric=metric,
                    included=adjusted is not None,
                    clock_policy=policy,
                    multiplier=multiplier,
                )
            )
            if adjusted is None:
                continue
            n = node(
                s["id"], keys[s["id"]], s["system"], observed_kind if rate else "estimated_89", rate * target_scale if rate else old
            )
            add(
                n,
                metric,
                c["id"],
                score,
                adjusted,
                multiplier,
                c["source_url"],
                c.get("clock_mhz"),
                s.get("clock_mhz"),
                policy,
                dict(classical=c, spec=s, qualification="existing_model_candidate;OS_compiler_cache_FPU_equivalence_unverified"),
            )
    # Same-column data supply both directly anchored and missing-target nodes.
    byvector = {v["id"]: v for v in vectors}
    for v in vectors:
        rate = v["targets"].get(target_metric)
        n = node(
            v["id"],
            find(v["model_key"]),
            v["machine"],
            observed_kind if rate else "unanchored",
            rate * target_scale if rate else None,
        )
        for metric, score in v["scores"].items():
            add(n, metric, v["observation_ids"][metric], score, score, 1, v["source_url"], provenance=v)
    # Reuse approved model/OS candidate extensions, including singleton measurements.
    for match in matching:
        if str(match["included"]).lower() != "true":
            continue
        v, s = byvector[match["vector_id"]], specs[match["spec_id"]]
        rate = numeric(s["metrics_raw"].get(target_metric))
        old = numeric(s["metrics_raw"].get("SPECint89"))
        if not rate and not old:
            continue
        n = node(
            s["id"], keys[s["id"]], s["system"], observed_kind if rate else "estimated_89", rate * target_scale if rate else old
        )
        for metric, score in v["scores"].items():
            add(
                n,
                metric,
                v["observation_ids"][metric],
                score,
                score,
                1,
                v["source_url"],
                target=s.get("clock_mhz"),
                policy="unknown_clock_unscaled",
                provenance=dict(vector=v, spec=s),
            )
    # Co-measured candidate hardware at the reported clock can constrain relative scales.
    # Never create new clock-scaled unanchored measurements.
    for cid, metrics in scores.items():
        c = classical[cid]
        if not metrics:
            continue
        options = ";".join(
            sorted(set(re.findall(r"\b(?:nof|fpa|fpu|fpp)\b", (c["system"] + " " + c.get("configuration_raw", "")).lower())))
        )
        nid = "classical:" + keys[cid] + ":" + str(c.get("clock_mhz")) + ":" + options
        n = node(nid, keys[cid], c["system"])
        for metric, score in metrics.items():
            add(n, metric, cid, score, score, 1, c["source_url"], c.get("clock_mhz"), c.get("clock_mhz"), provenance=c)
    # Observations attached to a SPEC target must not be reused as a duplicate
    # unanchored training node. Non-SPEC co-measurements remain available.
    anchored_ids = {r["observation_id"] for n in nodes.values() if n["target_kind"] != "unanchored" for r in n["observations"]}
    for n in nodes.values():
        if n["node_id"].startswith("classical:"):
            n["observations"] = [r for r in n["observations"] if r["observation_id"] not in anchored_ids]
        groups = defaultdict(list)
        for r in n["observations"]:
            groups[r["metric"]].append(math.log(r["adjusted_score"]))
        # All runs remain in observations; robust within-variant centers prevent
        # cartesian pair enumeration from creating additional training records.
        import statistics

        n["log_scores"] = {m: statistics.median(v) for m, v in groups.items()}
    return [n for n in nodes.values() if n["log_scores"]], observations, audit, {k: find(k) for k in list(parent)}


def frequency_checks(classical, pages):
    """Conditional same-label frequency sweeps; not proof of equal software/hardware."""
    import statistics

    grouped = defaultdict(lambda: defaultdict(list))
    members = defaultdict(list)
    for r in classical.values():
        f = numeric(r.get("clock_mhz"))
        if not f or r["benchmark"] not in ("Dhrystone", "Whetstone"):
            continue
        for metric, score in values(r, pages).items():
            key = (
                r["source_id"],
                relaxed_key(r["system"], f),
                metric,
                r.get("processor_raw", ""),
                r.get("os_raw", ""),
                r.get("language_raw", ""),
                r.get("configuration_raw", ""),
            )
            grouped[key][f].append(math.log(score))
            members[key].append(r["id"])
    rows = []
    for key, frequencies in sorted(grouped.items()):
        if len(frequencies) < 2:
            continue
        first = min(frequencies)
        base = statistics.median(frequencies[first])
        for f, scores in sorted(frequencies.items()):
            if f == first:
                continue
            z = statistics.median(scores) - base
            rows.append(
                dict(
                    source_id=key[0],
                    model_key=key[1],
                    metric=key[2],
                    processor_raw=key[3],
                    os_raw=key[4],
                    language_raw=key[5],
                    configuration_raw=key[6],
                    reference_clock=first,
                    target_clock=f,
                    reference_score=math.exp(base),
                    target_score=math.exp(statistics.median(scores)),
                    observed_score_ratio=math.exp(z),
                    clock_ratio=f / first,
                    normalized_ratio=math.exp(z) / (f / first),
                    scaling_signed_error_percent=100 * math.expm1(math.log(f / first) - z),
                    loglog_exponent=z / math.log(f / first),
                    observation_ids=json.dumps(members[key]),
                    qualification="same_available_source_labels;missing_configuration_fields_not_verification",
                )
            )
    return rows
