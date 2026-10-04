"""Family power-law calibration with eliminated missing target nodes.

Metric m predicts log speed-VAXen as a_m + b_g log x_m, with one exponent b_g per
exponent group: the benchmark family, except that each Whetstone precision is its own
group. Where the VAX-11/780 measured metric m, the intercept is tied to it,
a_m = -b_g c_m (c_m its median log score), so the 780 predicts 1 speed-VAXen by that
metric; other metrics (the instruction mixes) keep a free intercept. Both forms are
linear in the parameters, so the family/variant/node/model balanced least squares stays
a linear solve: per-node normal equations are built for the unconstrained (a_m, b_m)
and mapped to the parameters by a matrix that depends only on the anchor.

The fit has two stages. Exponents (with every parameter) are solved from anchored nodes
and from unanchored nodes spanning two or more families; an unanchored node of one family
compares variants measured side by side, whose ratios drift by era, so it does not set
exponents (user decision 2026-10-03). Free intercepts are then re-solved from all nodes
with the exponents fixed.
"""

import itertools
import math
from collections import defaultdict

import numpy as np
from cpushowspeed.classical.result_store import family

# Whetstone native/SP/DP ratios drift by era, and one shared exponent let unanchored
# Whetstone-only nodes pull it down (user decision 2026-10-03).
SEPARATE_EXPONENTS = {"Whetstone"}


def exponent_group(metric):
    return metric if family(metric) in SEPARATE_EXPONENTS else family(metric)


def metric_weights(metrics):
    counts = defaultdict(int)
    for metric in metrics:
        counts[family(metric)] += 1
    return {m: 1 / len(counts) / counts[family(m)] for m in metrics}


def is_anchored(n, bridge_enabled):
    return n["target_kind"] == "observed_speed" or (bridge_enabled and n["target_kind"] == "estimated_89")


def sets_exponents(n, bridge_enabled, metrics):
    return is_anchored(n, bridge_enabled) or len({family(m) for m in metrics}) > 1


def supported_metrics(nodes, bridge_enabled, latent=True):
    supported = set()
    groups = []
    for n in nodes:
        metrics = set(n["log_scores"])
        if is_anchored(n, bridge_enabled):
            supported |= metrics
        elif latent and sets_exponents(n, bridge_enabled, metrics):
            groups.append(metrics)
    old = None
    while old != supported:
        old = supported.copy()
        for group in groups:
            if group & supported:
                supported |= group
    return sorted(supported)


def matrices(nodes, metrics, bridge_enabled, latent=True):
    """Per model key, the normal equations (h, g, bridge vector) in the unconstrained (a_m, b_m) space.

    The first three are averaged over the model's exponent-setting nodes (zero when it has
    none), the last three over all its informative nodes; each model weighs one in each stage.
    """
    index = {m: i for i, m in enumerate(metrics)}
    q = 2 * len(metrics)
    bymodel = defaultdict(list)
    for n in nodes:
        logs = {k: v for k, v in n["log_scores"].items() if k in index}
        anchored = is_anchored(n, bridge_enabled)
        if not logs or (not anchored and (not latent or len(logs) < 2)):
            continue
        w = metric_weights(logs)
        design = np.zeros((len(logs), q))
        weights = np.zeros(len(logs))
        for row, (m, v) in enumerate(sorted(logs.items())):
            design[row, 2 * index[m]] = 1.0
            design[row, 2 * index[m] + 1] = v
            weights[row] = w[m]
        if anchored:
            weighted = design.T * weights
            h = weighted @ design
            g = weighted.sum(axis=1) * math.log(n["target"])
            b = weighted.sum(axis=1) if n["target_kind"] == "estimated_89" else np.zeros(q)
        else:
            # The node's missing target is eliminated at its weighted mean prediction.
            mean = weights @ design
            h = (design.T * weights) @ design - np.outer(mean, mean)
            g = np.zeros(q)
            b = np.zeros(q)
        bymodel[n["model_key"]].append((sets_exponents(n, bridge_enabled, logs), (h, g, b)))
    # Equal model weight; divide that weight over informative configuration nodes.
    result = {}
    for k, values in bymodel.items():
        first = [v for use, v in values if use]
        stage1 = tuple(np.mean([v[i] for v in first], axis=0) if first else np.zeros_like(values[0][1][i]) for i in range(3))
        stage2 = tuple(np.mean([v[i] for _, v in values], axis=0) for i in range(3))
        result[k] = stage1 + stage2
    return result


def parameters(metrics, anchor):
    """Parameter names: one exponent per exponent group, and an intercept for each metric the anchor does not tie."""
    names = [("exponent", g) for g in sorted({exponent_group(m) for m in metrics})]
    return names + [("intercept", m) for m in metrics if m not in anchor]


def transform(metrics, names, anchor, anchor_logs=None):
    """Map from parameters to the (a_m, b_m) vector; with anchor_logs (draws x metrics), one map per draw."""
    index = {n: i for i, n in enumerate(names)}
    base = np.zeros((2 * len(metrics), len(names)))
    tied = []
    for i, m in enumerate(metrics):
        j = index["exponent", exponent_group(m)]
        base[2 * i + 1, j] = 1.0
        if m in anchor:
            base[2 * i, j] = -anchor[m]
            tied.append((i, j))
        else:
            base[2 * i, index["intercept", m]] = 1.0
    if anchor_logs is None:
        return base
    maps = np.repeat(base[None], len(anchor_logs), axis=0)
    for i, j in tied:
        maps[:, 2 * i, j] = -anchor_logs[:, i]
    return maps


def bridge_log(edges, exclude=None):
    return sum(np.mean([v for k, v in values.items() if k != exclude]) for values in edges.values())


def solve(names, t, h1, g1, h2, g2):
    """Two-stage solve per draw (leading axis): every parameter from stage 1, then free intercepts
    from stage 2 with the stage-1 exponents fixed. Returns the (a_m, b_m) vectors and validity."""
    p = len(names)
    free = np.array([kind == "intercept" for kind, _ in names])
    ht = np.einsum("dqi,dqr,drj->dij", t, h1, t)
    valid = np.linalg.matrix_rank(ht) == p
    params = np.zeros((len(t), p))
    params[valid] = np.linalg.solve(ht[valid], np.einsum("dqi,dq->di", t[valid], g1[valid])[..., None])[..., 0]
    if free.any():
        tu, te = t[:, :, free], t[:, :, ~free]
        resid = g2 - np.einsum("dqr,drj,dj->dq", h2, te, params[:, ~free])
        hu = np.einsum("dqi,dqr,drj->dij", tu, h2, tu)
        valid &= np.linalg.matrix_rank(hu) == free.sum()
        intercepts = np.zeros((len(t), free.sum()))
        intercepts[valid] = np.linalg.solve(hu[valid], np.einsum("dqi,dq->di", tu[valid], resid[valid])[..., None])[..., 0]
        params[:, free] = intercepts
    return np.einsum("dqi,di->dq", t, params), valid


def calibration(metrics, phi):
    return {m: (float(phi[2 * i]), float(phi[2 * i + 1])) for i, m in enumerate(metrics)}


def train(nodes, edges, bridge_enabled, anchor, exclude=None, latent=True, cache=None):
    """Point calibration {metric: (intercept, exponent)} and the per-model normal equations.

    A model's equations depend only on its own nodes and the calibrated metrics, so holdout
    loops pass a `cache` dict (one per node list) and reuse them across folds.
    """
    if any(n["target_kind"] not in {"observed_speed", "estimated_89", "unanchored"} for n in nodes):
        raise ValueError("the classical network anchors only on SPECint92 speed or bridged SPECint89")
    training = [n for n in nodes if n["model_key"] != exclude]
    metrics = supported_metrics(training, bridge_enabled, latent)
    if not metrics:
        return {}, {}
    if cache is None:
        grouped = matrices(training, metrics, bridge_enabled, latent)
    else:
        key = (bridge_enabled, latent, tuple(metrics))
        if key not in cache:
            cache[key] = matrices(nodes, metrics, bridge_enabled, latent)
        grouped = {k: v for k, v in cache[key].items() if k != exclude}
    bridge = bridge_log(edges, exclude) if bridge_enabled else 0.0
    h1, h2 = (sum(v[i] for v in grouped.values())[None] for i in (0, 3))
    g1, g2 = (sum(v[i] + bridge * v[i + 1] for v in grouped.values())[None] for i in (1, 4))
    names = parameters(metrics, anchor)
    phi, valid = solve(names, transform(metrics, names, anchor)[None], h1, g1, h2, g2)
    if not valid[0]:
        return {}, grouped
    return calibration(metrics, phi[0]), grouped


def bootstrap(nodes, edges, bridge_enabled, anchor, anchor_sd, draws, seed):
    """Model-cluster bootstrap with the anchor's own sampling error; returns metrics, intercept and exponent draws.

    The 780 anchor of each metric is drawn as c_m + N(0, anchor_sd[m]) per draw.
    """
    calib, grouped = train(nodes, edges, bridge_enabled, anchor)
    metrics = list(calib)
    if not metrics:
        return metrics, np.empty((0, 0)), np.empty((0, 0))
    q = 2 * len(metrics)
    keys = sorted(set(grouped) | ({k for edge in edges.values() for k in edge} if bridge_enabled else set()))
    index = {k: i for i, k in enumerate(keys)}
    rng = np.random.default_rng(seed)
    weights = rng.multinomial(len(keys), np.full(len(keys), 1 / len(keys)), size=draws)
    bridge = np.zeros(draws)
    valid = np.ones(draws, dtype=bool)
    if bridge_enabled:
        for edge in edges.values():
            w = weights[:, [index[k] for k in edge]]
            total = w.sum(axis=1)
            valid &= total > 0
            bridge += np.divide(w @ np.array(list(edge.values())), total, out=np.zeros(draws), where=total > 0)
    noise = rng.standard_normal((draws, len(metrics)))
    anchor_logs = np.array([[anchor.get(m, 0.0) + anchor_sd.get(m, 0.0) * z for m, z in zip(metrics, row)] for row in noise])
    w = weights[:, [index[k] for k in grouped]]

    def stage(i):
        h = (w @ np.array([v[i].reshape(-1) for v in grouped.values()])).reshape(-1, q, q)
        g = w @ np.array([v[i + 1] for v in grouped.values()]) + bridge[:, None] * (
            w @ np.array([v[i + 2] for v in grouped.values()])
        )
        return h, g

    (h1, g1), (h2, g2) = stage(0), stage(3)
    names = parameters(metrics, anchor)
    phi, ok = solve(names, transform(metrics, names, anchor, anchor_logs), h1, g1, h2, g2)
    phi = phi[valid & ok]
    return metrics, phi[:, 0::2], phi[:, 1::2]


def estimates(node, calib):
    scores = {m: calib[m][0] + calib[m][1] * v for m, v in node["log_scores"].items() if m in calib}
    if not scores:
        return []
    result = []

    def add(label, subset):
        w = metric_weights(subset)
        result.append(
            dict(
                subset=label,
                metrics=";".join(sorted(subset)),
                predicted_log=sum(w[m] * scores[m] for m in subset),
                families=len({family(m) for m in subset}),
            )
        )

    for m in scores:
        add("single:" + m, [m])
    families = sorted({family(m) for m in scores})
    for f in families:
        add("family:" + f, [m for m in scores if family(m) == f])
    for a, b in itertools.combinations(families, 2):
        add("two_families:" + a + "+" + b, [m for m in scores if family(m) in (a, b)])
    # Full availability requires all observed variants calibrated in this fold.
    if len(scores) == len(node["log_scores"]):
        add("all_available", list(scores))
    return result
