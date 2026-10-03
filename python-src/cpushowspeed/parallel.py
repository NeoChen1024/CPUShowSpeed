"""Process-parallel map for independent, deterministic work items.

Results come back in input order, so parallel and serial runs produce identical output.
`--jobs` options pass their value here; 0 means every available CPU and 1 runs in-process.
"""

import os
from concurrent.futures import ProcessPoolExecutor

import click


def workers(jobs):
    return jobs or len(os.sched_getaffinity(0))


def pmap(function, items, jobs=0, chunksize=1):
    """`map(function, items)` across worker processes; function and items must be picklable."""
    items = list(items)
    n = min(workers(jobs), len(items))
    if n <= 1:
        return [function(item) for item in items]
    with ProcessPoolExecutor(n) as pool:
        return list(pool.map(function, items, chunksize=chunksize))


def jobs_option(function):
    return click.option(
        "--jobs",
        type=click.IntRange(min=0),
        default=0,
        show_default=True,
        help="Worker processes; 0 uses every available CPU, 1 runs serially.",
    )(function)
