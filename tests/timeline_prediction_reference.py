"""Emit independent NumPy/CLI expectations for the generated-page JS integration test.

uv run --no-sync python tests/timeline_prediction_reference.py > /tmp/timeline-prediction-reference.json
node tests/timeline_interaction.js data/derived/figures/timeline/vaxen-timeline.html full /tmp/timeline-prediction-reference.json
"""

import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
from cpushowspeed.classic_predict import predict_scores
from cpushowspeed.research_io import read_csv
from cpushowspeed.timeline_calculator import HISTORICAL_INPUTS
from cpushowspeed.timeline_estimates import bundle

result = dict(historical=[], spec=[])
root = Path("data/derived/classic/mix-network-fit")
audit = json.loads((root / "audit.json").read_text())
run = next(r for r in audit["runs"] if (r["scenario"], r["cohort"]) == ("linear_clock", "with_spec89"))
metrics = run["metrics"]
rows = {
    r["metric"]: r for r in read_csv(root / "coefficients.csv") if (r["scenario"], r["cohort"]) == ("linear_clock", "with_spec89")
}
with np.load(root / "coefficient-log-draws.npz", allow_pickle=False) as archive:
    samples = archive["linear_clock__with_spec89"]
names = [r[1] for r in HISTORICAL_INPUTS]
for mask in range(1, 1 << len(names)):
    scores = {m: float(2 + i * 3) for i, m in enumerate(names) if mask & (1 << i)}
    if not any(m.startswith("InstructionMix:") for m in scores):
        prediction = predict_scores(scores, Path("data/derived/classic/network-fit"))
        values = [prediction["vaxen"], prediction["vaxen_ci95"]["low"], prediction["vaxen_ci95"]["high"]]
    else:
        counts = Counter(m.split(":")[0] for m in scores)
        weights = np.array([1 / len(counts) / counts[m.split(":")[0]] for m in scores])
        logs = np.log(list(scores.values()))
        point = math.exp(np.dot(weights, logs + np.log([float(rows[m]["coefficient_vaxen_per_score"]) for m in scores])))
        draws = np.exp((samples[:, [metrics.index(m) for m in scores]] + logs) @ weights)
        values = [point, *map(float, np.quantile(draws, [0.025, 0.975]))]
    result["historical"].append(dict(scores=scores, values=values))
for policy in ("strict", "ram-aliases", "cpu-clock"):
    fits, backbone, _, _ = bundle(policy)
    for g in ("cpu95", "cpu2000", "cpu2006", "cpu2017", "cpu2026"):
        for mode in ("base", "peak"):
            for speed, rate, method in [(7, "", "speed_only"), ("", 13, "backbone"), (7, 13, "equal_geometric")]:
                if method == "backbone":
                    fit = backbone[g, mode]
                    keys = ("coefficient", "ci95_low", "ci95_high")
                    score = rate
                else:
                    if (g, mode, method) not in fits:
                        continue
                    fit = fits[g, mode, method]
                    keys = ("coefficient_vaxen", "vaxen_ci95_low", "vaxen_ci95_high")
                    score = math.sqrt(speed * rate) if rate else speed
                result["spec"].append(
                    dict(
                        generation=g, mode=mode, speed=speed, rate=rate, policy=policy, values=[float(fit[k]) * score for k in keys]
                    )
                )
print(json.dumps(result, allow_nan=False))
