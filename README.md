# CPUShowSpeed

CPUShowSpeed is a research project for tracing the performance of documented
computer system configurations across benchmark generations. The intended output is an evidence-backed timeline, with
measured results, manual-based reconstructions, and cross-benchmark estimates
identified separately.

The repository collects public SPEC CPU95–CPU2026 results and surviving
Netlib CPU92 pages. It can plot the surviving CPU92 integer speed submissions
on their original VAX-11/780-relative scale. No cross-generation normalized
performance series has been calculated yet.

## Start here

- [Documentation index](docs/README.md): scope, data interpretation, methods, and source inventory.
- [Verified research](research/README.md): checked findings with original-page evidence.
- [Research roadmap](docs/TODO.md): work that has not yet been implemented or verified.
- [SPEC collection](docs/spec-collection.md): available scraping commands and snapshot scope.

## Local setup

Use Python 3.11 or newer and a repository-local environment managed by `uv`:

```sh
uv venv .venv
uv pip install --python .venv/bin/python -e .
./.venv/bin/cpushowspeed --help
```

`requirements.txt` is the sole dependency list. `pyproject.toml` reads it for
editable installation and defines the `cpushowspeed` command.
