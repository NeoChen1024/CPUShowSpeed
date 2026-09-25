# CPUShowSpeed — Agent guide

This is an exploratory research project. Do not describe planned data collection
or statistical methods as implemented results.

## Sources of truth

- [Documentation index](docs/README.md) routes research and tool questions.
- [Scope and metrics](docs/scope-and-metrics.md) defines the tracks and evidence classes.
- [Data contract](docs/data-contract.md) defines how results and dates are interpreted.
- [Methods](docs/methods.md) owns reconstruction and cross-benchmark methods.
- [Sources](docs/sources.md) owns source selection and acquisition caveats.
- [SPEC collection](docs/spec-collection.md) owns implemented result scraping commands.
- [Document extraction](docs/document-extraction.md) owns PDF/OCR evidence policy.
- [Machine watchlist](docs/machine-watchlist.md) owns priority systems and variants.
- [Verified findings](research/README.md) owns checked research results.
- CLI `--help` owns implemented commands and options.

## Documentation and research integrity

- Give each topic one primary document; summarize and link elsewhere.
- Distinguish current behavior, selected research rules, and open plans.
- Write known full dates as `YYYY-MM-DD`; retain partial dates at their actual
  precision rather than inventing missing components.
- Keep stable data semantics, units, dates, assumptions, and limitations readable
  without inspecting code. Preserve per-result citations in data records.
- Make source-checked archaeological performance values and related observations
  script-readable when extraction begins. Defer the concrete schema and format
  until historical PDF and KIPS work; Markdown findings provide context and
  citations, not the sole canonical store for extracted numerical data.
- Record source-checked research findings in `research/`, with original
  document/page citations and the review date. Keep candidate leads in the
  watchlist and bulk OCR or debugging transcripts out of ordinary documents.
  Remove superseded plans and stale links as work lands.
- Keep source documents and extracted raw records immutable. Derived datasets must
  retain source identity and calculation method; never overwrite a reported score
  with an estimate or fill missing values with invented measurements.
- Keep large downloaded documents and generated datasets out of Git. Do not edit
  unrelated files or another repository as part of this project.

## Python workflow

- Use the repository-root `.venv`, managed by `uv`, on this Arch Linux host.
- Python code lives in `python-src/cpushowspeed/`. Use Click for CLI commands and
  register user-facing commands in `pyproject.toml`.
- `requirements.txt` is the single dependency list; `pyproject.toml` reads it.
- Use Black (132 columns, Python 3.11 target) and isort (Black profile).
- Machine-readable output goes to stdout; progress, warnings, and errors go to stderr.
- Validate parsers against independent source pages or documents and calculations
  against published examples. Report what was actually checked.
