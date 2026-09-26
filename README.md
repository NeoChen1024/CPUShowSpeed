# CPUShowSpeed

CPUShowSpeed studies **whole-machine throughput** across generations of
benchmark results. Its current quantitative series uses SPEC integer **rate**
submissions from CPU92 through CPU2026 and reports an exploratory scale
relative to the VAX-11/780's CPU92 rate reference. A rate score describes the
published machine configuration and concurrent benchmark copies. Cross-suite
values are estimates, with original scores and sources retained.

The project also preserves source-checked historical documents and a curated
SPEC89 research archive. Those materials are archival evidence; the previous
integer-speed fits and annual speed figures are outside the active analysis.
Earlier-machine throughput reconstruction from manuals remains research work,
not an implemented benchmark result.

## Start here

- [Documentation index](docs/README.md): scope, data interpretation and acquisition.
- [Rate fitting audit](research/spec95-spec2026-rate-fitting.md): current CPU92–CPU2026 factors, sources and limits.
- [Annual rate figure](research/annual-rate-vaxen.md): source-linked yearly highest submissions and distributions.
- [SPEC collection](docs/spec-collection.md): implemented rate collection and fitting commands.
- [Research index](research/README.md): checked findings and preserved source archives.
- [Roadmap](docs/TODO.md): work that remains unverified or unimplemented.

## Local setup

On Arch Linux, use a repository-local environment managed by `uv`:

```sh
uv venv .venv
uv pip install --python .venv/bin/python -e .
./.venv/bin/cpushowspeed --help
```

`requirements.txt` is the single dependency list; `pyproject.toml` reads it
for editable installation and defines the `cpushowspeed` command.
