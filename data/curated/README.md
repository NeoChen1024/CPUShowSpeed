# Curated data tables

Canonical, reviewable tables of the [data schema](../../docs/data-schema.md), which
owns their meaning and migration status. `schema.json` declares every table and
row schema; tables are JSONL, one row per line, sorted by primary key.

| File | Table | Since |
| --- | --- | --- |
| `source.jsonl` | `source`: documents, page revisions and dataset snapshots | 2026-10-02 |

Edit rows directly, then run:

```sh
uv run cpushowspeed data validate --check-local
uv run cpushowspeed data build
```

`data build` writes the ignored SQLite database `data/derived/schema/cpushowspeed.sqlite`.
