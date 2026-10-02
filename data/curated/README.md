# Curated data tables

Canonical, reviewable tables of the [data schema](../../docs/data-schema.md), which
owns their meaning and migration status. `schema.json` declares every table and
row schema; tables are JSONL, one row per line, sorted by primary key.

| File | Table | Since |
| --- | --- | --- |
| `source.jsonl` | `source`: documents, page revisions and dataset snapshots | 2026-10-02 |
| `processor_family.jsonl` | `processor_family`: processor lines | 2026-10-02 |
| `processor_sku.jsonl` | `processor_sku`: sold processor models | 2026-10-02 |
| `alias.jsonl` | `alias`: exact-text, pattern and rule links from text to entities | 2026-10-02 |
| `vendor.jsonl` | `vendor`: hardware vendors and their model prefixes | 2026-10-02 |
| `system_model.jsonl` | `system_model`: curated machines and canonical names; other models are rule-derived | 2026-10-02 |
| `date_event.jsonl` | `date_event`: dated events of processors and system models | 2026-10-02 |
| `review.jsonl` | `review`: rejected result dates, accepted result pairs, identity links awaiting review | 2026-10-02 |
| `metric.jsonl` | `metric`: observation metric strings and the registry metric each measures | 2026-10-02 |

Edit rows directly, then run:

```sh
uv run cpushowspeed data validate --check-local
uv run cpushowspeed data extract   # when a source adapter or raw input changes
uv run cpushowspeed data build
```

`data extract` runs every source adapter into `data/derived/schema/observations.jsonl`
(`benchmark-observation-v2`); `data build` writes the ignored SQLite database
`data/derived/schema/cpushowspeed.sqlite`, including the `observation` table.
