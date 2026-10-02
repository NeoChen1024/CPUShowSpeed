"""Reviewed DEC N3909 report columns as source vectors: classical scores and SPEC targets of one machine."""

from cpushowspeed.classic_overlap import model_key
from cpushowspeed.classic_pdf import scalar


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
