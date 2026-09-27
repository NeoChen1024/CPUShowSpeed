"""Reviewed source vectors and staged matching, independent of experiments."""

import itertools
import json

from cpushowspeed.calibration import ANCHOR
from cpushowspeed.classic_overlap import model_key
from cpushowspeed.classic_pdf import scalar
from cpushowspeed.classic_values import numeric

STAGES = ("within_source", "plus_legacy_unscaled", "plus_cross_source_unscaled", "plus_cross_source_clock_sensitivity")


def os_key(value):
    value = value.lower()
    if "vms" in value:
        return "vms"
    if "osf" in value:
        return "osf"
    if "ultrix" in value:
        return "ultrix"
    return None


def pair_patterns(scores):
    for a, b in itertools.combinations(
        sorted(scores, key=lambda s: ({"Dhrystone": 0, "Whetstone": 1, "LINPACK": 2}[s.split(":")[0]], s)), 2
    ):
        if a.split(":")[0] != b.split(":")[0]:
            yield a, b


def source_vectors(tables, interpreted):
    lookup = {r["observation_id"]: r for r in interpreted}
    vectors = []
    units = []
    for table in tables:
        if table["source_id"] != "dec-n3909-1994":
            continue
        for i, col in enumerate(table["columns"], 1):
            scores, targets, ids = {}, {}, {}
            for row in table["rows"]:
                metric = row["label_checked"]
                raw = row["cells"][i - 1]
                oid = f"{table['source_id']}:{table['table_id']}:l{row['line']}:c{i}"
                if oid in lookup:
                    r = lookup[oid]
                    if metric.startswith("Dhrystone"):
                        name = "Dhrystone:v" + ("1.1" if "1.1" in metric else "2.1") + "_DMIPS"
                    else:
                        name = "Whetstone:MWIPS_" + ("DP" if metric.endswith("dp") else "SP")
                    scores[name] = float(r["normalized_value"])
                    ids[name] = oid
                    units.append(dict(r, normalized_metric=name, unit_review="explicit_user_policy_applied"))
                elif metric.startswith("LINPACK 100x100") and scalar(raw) is not None:
                    name = "LINPACK:n100_MFLOPS"
                    scores[name] = scalar(raw)
                    ids[name] = oid
                    units.append(
                        dict(
                            observation_id=oid,
                            metric=metric,
                            value_raw=raw,
                            normalized_value=scalar(raw),
                            normalized_unit="MFLOPS",
                            unit_review="n100_dp_source_row",
                        )
                    )
                elif (
                    metric in ("SPECmark89", "SPECint92", "SPECbase_int92", "SPECfp92", "SPECrate_int92", "SPECrate_fp92")
                    and scalar(raw) is not None
                ):
                    targets[metric] = scalar(raw)
                    ids[metric] = oid
            vectors.append(
                dict(
                    id=f"{table['source_id']}:{table['table_id']}:column:{i}",
                    source_id=table["source_id"],
                    machine=col["machine"],
                    os=col["os"],
                    model_key=model_key(col["machine"]),
                    scores=scores,
                    targets=targets,
                    observation_ids=ids,
                    clock_mhz=None,
                    cpu_count=None,
                    source_url=table["source_url"],
                    pdf_page=table["pdf_page"],
                    pdf_blake3=table["pdf_blake3"],
                    qualification="same_source_column;compiler_copies_active_cpu_not_established",
                )
            )
    return vectors, units


def make_pair(vector, a, b, target, score, spec_id, origin, extra=""):
    return dict(
        pattern=a + "+" + b,
        target=target,
        model_key=vector["model_key"],
        system=vector["machine"],
        spec_id=spec_id,
        first_id=vector["observation_ids"][a],
        second_id=vector["observation_ids"][b],
        first=vector["scores"][a],
        second=vector["scores"][b],
        y=score * (ANCHOR if target == "SPECrate_int92" else 1),
        origin=origin,
        qualification=vector["qualification"] + extra,
        target_unit="SPEC92 integer-rate VAXen" if target == "SPECrate_int92" else target + " raw",
        provenance=json.dumps(dict(vector_id=vector["id"], source_url=vector["source_url"], target_record_id=spec_id)),
    )


def prepare(vectors, legacy, specs):
    within, cross, audit = [], [], []
    for vector in vectors:
        for a, b in pair_patterns(vector["scores"]):
            for target, score in vector["targets"].items():
                within.append(make_pair(vector, a, b, target, score, vector["observation_ids"][target], "within_DEC"))
        for spec in specs:
            if model_key(spec["system"]) != vector["model_key"]:
                continue
            reasons = []
            if not os_key(spec.get("os_raw", "")) or os_key(spec["os_raw"]) != os_key(vector["os"]):
                reasons.append("os_missing_or_conflict")
            if spec["cohort"].startswith("SPEC92") and numeric(spec.get("cpu_count")) != 1:
                reasons.append("archive_rate_cpu_count_not_one")
            raw = spec["raw_record"]
            if isinstance(raw, dict) and (
                raw.get("measurement_type") == "reference_definition" or "reference_definition" in raw.get("review_flags", "")
            ):
                reasons.append("reference_definition")
            targets = {
                k: numeric(v)
                for k, v in spec["metrics_raw"].items()
                if k in ("SPECmark89", "SPECint89", "SPECrate_int92", "SPECrate_base_int92") and numeric(v)
            }
            audit.append(
                dict(
                    vector_id=vector["id"],
                    spec_id=spec["id"],
                    model_key=vector["model_key"],
                    included=bool(targets) and not reasons,
                    exclusion_reasons=";".join(reasons) if targets else "no_supported_target",
                    clock_status="source_column_clock_unknown_no_scaling",
                    source_url=spec["source_url"],
                )
            )
            if reasons:
                continue
            for a, b in pair_patterns(vector["scores"]):
                for target, score in targets.items():
                    row = make_pair(
                        vector,
                        a,
                        b,
                        target,
                        score,
                        spec["id"],
                        "DEC_to_archive",
                        ";model_os_candidate_only;source_independence_unverified;clock_unknown_unscaled",
                    )
                    if target == "SPECrate_base_int92":
                        row["y"] = score * ANCHOR
                        row["target_unit"] = "SPEC92 integer-rate VAXen"
                    cross.append(row)
    result = []
    for stage in STAGES:
        result += [dict(r, stage=stage) for r in within]
        if stage != "within_source":
            scenario = "linear_clock_scaling" if stage == STAGES[-1] else "unknown_allowed"
            for old in legacy:
                if old["scenario"] != scenario or old["included"] != "True":
                    continue
                result.append(
                    dict(
                        pattern=old["pattern"],
                        target=old["target"],
                        stage=stage,
                        model_key=old["model_key"],
                        system=old["system"],
                        spec_id=old["spec_id"],
                        first_id=old["first_id"],
                        second_id=old["second_id"],
                        first=float(old["first"]),
                        second=float(old["second"]),
                        y=float(old["y"]),
                        origin="legacy_cross_source",
                        qualification="legacy_candidate_rules;shared_lineage_possible",
                        provenance=old["provenance"],
                        target_unit="SPEC92 integer-rate VAXen" if old["target"].startswith("SPECrate") else old["target"] + " raw",
                    )
                )
        if stage in STAGES[2:]:
            result += [dict(r, stage=stage) for r in cross]
    return result, audit
