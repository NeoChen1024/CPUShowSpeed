"""Family power-law calibration with eliminated missing target nodes.

Metric m predicts log speed-VAXen as a_m + b_f log x_m, with one exponent b_f per
benchmark family. Where the VAX-11/780 measured metric m, the intercept is tied to it,
a_m = -b_f c_m (c_m its median log score), so the 780 predicts 1 speed-VAXen by that
metric; other metrics (the instruction mixes) keep a free intercept. Both forms are
linear in the parameters, so the family/variant/node/model balanced least squares stays
a linear solve: per-node normal equations are built for the unconstrained (a_m, b_m)
and mapped to the parameters by a matrix that depends only on the anchor.
"""

import itertools
import math
from collections import defaultdict

import numpy as np
from cpushowspeed.classical_store import family


def metric_weights(metrics):
    counts = defaultdict(int)
    for metric in metrics:
        counts[family(metric)] += 1
    return {m: 1 / len(counts) / counts[family(m)] for m in metrics}


def is_anchored(n, bridge_enabled):
    return n["target_kind"] == "observed_speed" or (bridge_enabled and n["target_kind"] == "estimated_89")


def supported_metrics(nodes, bridge_enabled, latent=True):
    supported = set()
    groups = []
    for n in nodes:
        metrics = set(n["log_scores"])
        if is_anchored(n, bridge_enabled):
            supported |= metrics
        elif latent:
            groups.append(metrics)
    old = None
    while old != supported:
        old = supported.copy()
        for group in groups:
            if group & supported:
                supported |= group
    return sorted(supported)


def matrices(nodes, metrics, bridge_enabled, latent=True):
    """Per model key, the normal equations (h, g, bridge vector) in the unconstrained (a_m, b_m) space."""
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
        bymodel[n["model_key"]].append((h, g, b))
    # Equal model weight; divide that weight over informative configuration nodes.
    return {k: tuple(np.mean([v[i] for v in values], axis=0) for i in range(3)) for k, values in bymodel.items()}


def parameters(metrics, anchor):
    """Parameter names: one exponent per family, and an intercept for each metric the anchor does not tie."""
    names = [("exponent", f) for f in sorted({family(m) for m in metrics})]
    return names + [("intercept", m) for m in metrics if m not in anchor]


def transform(metrics, names, anchor, anchor_logs=None):
    """Map from parameters to the (a_m, b_m) vector; with anchor_logs (draws x metrics), one map per draw."""
    index = {n: i for i, n in enumerate(names)}
    base = np.zeros((2 * len(metrics), len(names)))
    tied = []
    for i, m in enumerate(metrics):
        j = index["exponent", family(m)]
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


def calibration(metrics, phi):
    return {m: (float(phi[2 * i]), float(phi[2 * i + 1])) for i, m in enumerate(metrics)}


def train(nodes, edges, bridge_enabled, anchor, exclude=None, latent=True):
    """Point calibration {metric: (intercept, exponent)} and the per-model normal equations."""
    if any(n["target_kind"] not in {"observed_speed", "estimated_89", "unanchored"} for n in nodes):
        raise ValueError("the classical network anchors only on SPECint92 speed or bridged SPECint89")
    training = [n for n in nodes if n["model_key"] != exclude]
    metrics = supported_metrics(training, bridge_enabled, latent)
    if not metrics:
        return {}, {}
    grouped = matrices(training, metrics, bridge_enabled, latent)
    bridge = bridge_log(edges, exclude) if bridge_enabled else 0.0
    h = sum(v[0] for v in grouped.values())
    g = sum(v[1] + bridge * v[2] for v in grouped.values())
    names = parameters(metrics, anchor)
    t = transform(metrics, names, anchor)
    ht = t.T @ h @ t
    if np.linalg.matrix_rank(ht) < len(names):
        return {}, grouped
    return calibration(metrics, t @ np.linalg.solve(ht, t.T @ g)), grouped


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
    h = (w @ np.array([v[0].reshape(-1) for v in grouped.values()])).reshape(-1, q, q)
    g = w @ np.array([v[1] for v in grouped.values()]) + bridge[:, None] * (w @ np.array([v[2] for v in grouped.values()]))
    names = parameters(metrics, anchor)
    t = transform(metrics, names, anchor, anchor_logs)
    ht = np.einsum("dqi,dqr,drj->dij", t, h, t)
    gt = np.einsum("dqi,dq->di", t, g)
    valid &= np.linalg.matrix_rank(ht) == len(names)
    phi = np.einsum("dqi,di->dq", t[valid], np.linalg.solve(ht[valid], gt[valid, :, None])[..., 0])
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
