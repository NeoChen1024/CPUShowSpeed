"""Family-balanced sparse log calibration with eliminated missing target nodes."""

import itertools
import math
from collections import defaultdict

import numpy as np
from cpushowspeed.classic_network_data import family


def metric_weights(metrics):
    counts = defaultdict(int)
    for metric in metrics:
        counts[family(metric)] += 1
    return {m: 1 / len(counts) / counts[family(m)] for m in metrics}


def supported_metrics(nodes, bridge_enabled, latent=True):
    supported = set()
    groups = []
    for n in nodes:
        metrics = set(n["log_scores"])
        anchored = n["target_kind"] == "observed_rate" or (bridge_enabled and n["target_kind"] == "estimated_89")
        if anchored:
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
    index = {m: i for i, m in enumerate(metrics)}
    p = len(metrics)
    bymodel = defaultdict(list)
    for n in nodes:
        logs = {k: v for k, v in n["log_scores"].items() if k in index}
        anchored = n["target_kind"] == "observed_rate" or (bridge_enabled and n["target_kind"] == "estimated_89")
        if not logs or (not anchored and (not latent or len(logs) < 2)):
            continue
        w = metric_weights(logs)
        a = np.zeros(p)
        z = np.zeros(p)
        for m, v in logs.items():
            a[index[m]] = w[m]
            z[index[m]] = w[m] * v
        if anchored:
            h = np.diag(a)
            g = a * math.log(n["target"]) - z
            b = a if n["target_kind"] == "estimated_89" else np.zeros(p)
        else:
            h = np.diag(a) - np.outer(a, a)
            g = a * z.sum() - z
            b = np.zeros(p)
        bymodel[n["model_key"]].append((h, g, b))
    # Equal model weight; divide that weight over informative configuration nodes.
    return {k: tuple(np.mean([v[i] for v in values], axis=0) for i in range(3)) for k, values in bymodel.items()}


def bridge_log(edges, exclude=None):
    return sum(np.mean([v for k, v in values.items() if k != exclude]) for values in edges.values())


def train(nodes, edges, bridge_enabled, exclude=None, latent=True):
    training = [n for n in nodes if n["model_key"] != exclude]
    metrics = supported_metrics(training, bridge_enabled, latent)
    if not metrics:
        return {}, {}
    grouped = matrices(training, metrics, bridge_enabled, latent)
    b = bridge_log(edges, exclude) if bridge_enabled else 0.0
    h = sum(v[0] for v in grouped.values())
    g = sum(v[1] + b * v[2] for v in grouped.values())
    if np.linalg.matrix_rank(h) < len(metrics):
        return {}, grouped
    alpha = np.linalg.solve(h, g)
    return dict(zip(metrics, alpha)), grouped


def bootstrap(nodes, edges, bridge_enabled, draws, seed):
    alpha, grouped = train(nodes, edges, bridge_enabled)
    metrics = list(alpha)
    p = len(metrics)
    if not p:
        return metrics, np.empty((0, 0))
    keys = sorted(set(grouped) | ({k for edge in edges.values() for k in edge} if bridge_enabled else set()))
    index = {k: i for i, k in enumerate(keys)}
    rng = np.random.default_rng(seed)
    weights = rng.multinomial(len(keys), np.full(len(keys), 1 / len(keys)), size=draws)
    b = np.zeros(draws)
    valid = np.ones(draws, dtype=bool)
    if bridge_enabled:
        for edge in edges.values():
            w = weights[:, [index[k] for k in edge]]
            total = w.sum(axis=1)
            valid &= total > 0
            b += np.divide(w @ np.array(list(edge.values())), total, out=np.zeros(draws), where=total > 0)
    w = weights[:, [index[k] for k in grouped]]
    h = (w @ np.array([v[0].reshape(-1) for v in grouped.values()])).reshape(-1, p, p)
    g = w @ np.array([v[1] for v in grouped.values()]) + b[:, None] * (w @ np.array([v[2] for v in grouped.values()]))
    valid &= np.linalg.matrix_rank(h) == p
    return metrics, np.linalg.solve(h[valid], g[valid, :, None])[..., 0]


def estimates(node, alpha):
    scores = {m: v + alpha[m] for m, v in node["log_scores"].items() if m in alpha}
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
