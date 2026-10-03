"""Power laws through the VAX-11/780, optionally behind the SPECint89 bridge edge: equal models and common resample weights.

The fitted form is log V = β (log x − c), where c is the 780's log composite score, so the
780 predicts exactly one speed-VAXen. Each model weighs 1 and each of its rows 1/n, so the
anchored least-squares exponent is a ratio of model-weighted moments. SPECint89 rows reach
speed-VAXen by adding the bridge log b to their log target.
"""

import statistics

import numpy as np

# Per-model means: log x, (log x)², log target, log x · log target, SPECint89 flag, flag · log x.
M1, M2, MY, MXY, MO, MXO = range(6)


def bridge_log(edges, exclude=None):
    return sum(statistics.mean(v for k, v in values.items() if k != exclude) for values in edges.values())


def moments(rows):
    """Sorted model keys and their row-mean moments; rows carry model_key, lx, ly and generation."""
    groups = {}
    for r in rows:
        groups.setdefault(r["model_key"], []).append(r)
    keys = sorted(groups)
    out = np.zeros((len(keys), 6))
    for i, k in enumerate(keys):
        lx = np.array([r["lx"] for r in groups[k]])
        ly = np.array([r["ly"] for r in groups[k]])
        old = np.array([r["generation"] == "89" for r in groups[k]], dtype=float)
        out[i] = lx.mean(), (lx * lx).mean(), ly.mean(), (lx * ly).mean(), old.mean(), (old * lx).mean()
    return keys, out


def exponent(m, weights, c, b=0.0):
    """Anchored exponent(s) for model weights (K or D×K), anchor log c and bridge log b (scalars or length D)."""
    w = np.asarray(weights, dtype=float)
    num = w @ m[:, MXY] - c * (w @ m[:, MY]) + b * (w @ m[:, MXO] - c * (w @ m[:, MO]))
    den = w @ m[:, M2] - 2 * c * (w @ m[:, M1]) + c * c * w.sum(axis=-1)
    return num / den, den


def coefficient(rows, edges, c, exclude=None):
    """(exponent, bridge log) from all models except `exclude`, which also leaves every bridge edge."""
    b = bridge_log(edges, exclude) if edges else 0.0
    keys, m = moments([r for r in rows if r["model_key"] != exclude])
    return float(exponent(m, np.ones(len(keys)), c, b)[0]), b


def joint_bootstrap(rows, edges, draws, seed, c=0.0):
    """Exponent draws, bridge factor draws and the kept-draw mask from one model-cluster resample across the edges and fit.

    `c` may be a length-`draws` array of anchor draws. Draws whose bridge edge or fit lost every
    model, or whose exponent is undefined, are dropped from both outputs.
    """
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
    if not rows:
        return np.array([]), np.exp(b[valid]), valid
    model_keys, m = moments(rows)
    w = weights[:, [index[k] for k in model_keys]]
    with np.errstate(divide="ignore", invalid="ignore"):
        beta, den = exponent(m, w, c, b)
    valid &= (w.sum(axis=1) > 0) & (den > 1e-12)
    return beta[valid], np.exp(b[valid]), valid
