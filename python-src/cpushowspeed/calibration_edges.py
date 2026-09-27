"""Shared dependent-edge calibration: equal models and common resample weights."""

import statistics
from collections import defaultdict

import numpy as np


def bridge_log(edges, exclude=None):
    return sum(statistics.mean(v for k, v in values.items() if k != exclude) for values in edges.values())


def coefficient(rows, edges, exclude=None):
    b = bridge_log(edges, exclude)
    groups = defaultdict(list)
    for r in rows:
        if r["model_key"] != exclude:
            groups[r["model_key"]].append(r["z"] + (b if r["generation"] == "89" else 0))
    return statistics.mean(statistics.median(v) for v in groups.values()), b


def joint_bootstrap(rows, edges, draws, seed):
    keys = sorted({r["model_key"] for r in rows} | {k for e in edges.values() for k in e})
    index = {k: i for i, k in enumerate(keys)}
    weights = np.random.default_rng(seed).multinomial(len(keys), np.full(len(keys), 1 / len(keys)), size=draws)
    b = np.zeros(draws)
    valid = np.ones(draws, dtype=bool)
    for values in edges.values():
        w = weights[:, [index[k] for k in values]]
        total = w.sum(axis=1)
        valid &= total > 0
        b += np.divide(w @ np.array(list(values.values())), total, out=np.zeros(draws), where=total > 0)
    numerator = np.zeros(draws)
    denom = np.zeros(draws)
    for key in sorted({r["model_key"] for r in rows}):
        group = [r for r in rows if r["model_key"] == key]
        z = np.array([r["z"] for r in group])[:, None]
        old = np.array([r["generation"] == "89" for r in group])[:, None]
        center = np.median(z + old * b, axis=0)
        w = weights[:, index[key]]
        numerator += center * w
        denom += w
    if rows:
        valid &= denom > 0
        factors = np.exp(numerator[valid] / denom[valid]).tolist()
    else:
        factors = []
    return factors, np.exp(b[valid]).tolist()
