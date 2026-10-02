"""In-memory classical and SPEC results for pairing and fitter tests."""

from cpushowspeed.classical_store import Result


def result(result_id, system_id, values, *, clock=None, cpus=None, entity="", scope="classical:test", reference=False):
    r = Result(result_id, scope, "System " + system_id, system_id, entity, clock, cpus, "", "https://example.org/" + result_id)
    r.reference = reference
    r.values = dict(values)
    r.observation_ids = {m: f"{result_id}:{m}" for m in values}
    return r
