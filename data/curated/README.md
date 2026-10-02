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
| `system_model.jsonl` | `system_model`: hand-curated machines (empty; SPEC models are derived) | 2026-10-02 |

Edit rows directly, then run:

```sh
uv run cpushowspeed data validate --check-local
uv run cpushowspeed data extract-mentions   # when the input catalogue changes
uv run cpushowspeed data build
```

`data build` writes the ignored SQLite database `data/derived/schema/cpushowspeed.sqlite`.
