# Processor identity resolution

Reviewed: 2026-10-02. Status: **implemented** as step 2 of the
[data schema](../docs/data-schema.md#migration-plan). Rules were designed afresh
(user decision 2026-10-02); the previous matching code was used only for
comparison, not as a parity target. No fitter or timeline consumes the
resolution yet.

## Reproduce

```sh
uv run cpushowspeed inputs build            # existing input catalogue
uv run cpushowspeed data extract-mentions   # data/derived/schema/processor-mentions.jsonl
uv run cpushowspeed data build              # adds processor_mention / processor_resolution
```

`data import-processors` performed the one-time seed of `processor_family`,
`processor_sku` and `alias` from the [CPU SKU catalogue](cpu-sku-chronology.md);
the tables are curated data from then on and the command refuses to overwrite
them without `--force`.

## Entities and rules

- **SKUs**: 1,352 Xeon, Opteron and EPYC models from the parsed Wikipedia tables,
  each with its `sku-key-v1` match key, every listed base clock and the verbatim
  table heading path (generation, codename). Each cites its source revision.
- **Families**: the most specific processor line a text can identify. Xeon,
  Opteron and EPYC come with the catalogue; 105 chip-model lines (POWER*, RS64,
  PowerPC, UltraSPARC, SPARC64/SPARC, PA-RISC, Alpha, MIPS R-series, Itanium,
  Pentium Pro/II/III/4 and Pentium II/III Xeon) were seeded from observed texts
  and have no catalogue source yet.
- **Resolution order**: exact-text alias, then `sku-key-v1` with a 2% nominal
  clock constraint, then family patterns. A failed SKU rule keeps its reason
  (`no_single_sku`, `sku_not_in_catalog`, `clock_conflict`) even when a family
  pattern resolves the text. Overlapping family patterns are reported as
  `ambiguous_family_patterns` rather than resolved by order.
- `sku-key-v1` was refined before first use: every parenthetical is removed
  (sockets such as "(939-pin)" were read as model numbers) and attached Opteron
  suffixes ("2220SE") are split. The SKU catalogue keys were unchanged.

Patterns match after removing (R)/(TM)/®/™. UltraSPARC suffixes are
case-sensitive because "IIi" and "III" differ only by case; 16 spelling tests
pass. Pentium II/III Xeon overlap with both the Pentium and Xeon patterns was
detected by the ambiguity check and fixed with explicit families.

## Coverage

3,951 distinct (scope, text, clock) mentions over 103,456 input observations:
**74,178 SKU (71.7%), 20,923 family (20.2%), 5,955 unresolved and 2,400 without
processor text**.

| Scope | Observations | SKU | Family | Unresolved | Missing text |
| --- | ---: | ---: | ---: | ---: | ---: |
| `spec:cpu2006` | 47,553 | 43,506 | 911 | 3,136 | 0 |
| `spec:cpu2017` | 40,075 | 27,772 | 11,903 | 400 | 0 |
| `spec:cpu2000` | 7,402 | 2,695 | 4,166 | 541 | 0 |
| `spec:cpu95` | 2,619 | 0 | 2,391 | 228 | 0 |
| `spec:cpu92` | 989 | 0 | 699 | 290 | 0 |
| `classical:longbottom-whetstone-history` | 862 | 0 | 84 | 746 | 32 |
| `classical:netlib-linpack-report` | 815 | 0 | 0 | 0 | 815 |
| `reviewed-vector:dec-n3909-1994` | 661 | 0 | 0 | 0 | 661 |
| `historical-spec:spec89` | 653 | 0 | 53 | 97 | 503 |
| `classical:netlib-dhrystone-results` | 542 | 0 | 145 | 397 | 0 |
| `historical-spec:spec92-netlib` | 473 | 0 | 371 | 102 | 0 |
| `spec:cpu2026` | 423 | 205 | 200 | 18 | 0 |
| `mix:longbottom-cpumix` | 360 | 0 | 0 | 0 | 360 |
| `historical-spec:spec89-throughput` | 20 | 0 | 0 | 0 | 20 |
| `historical-spec:spec92-dec` | 9 | 0 | 0 | 0 | 9 |

## Comparison with the previous SPEC processor key

`spec_overlap._processor_key` grouped SPEC processors for cross-generation
pairing. Over 99,061 SPEC observations with processor text:

- No previous key merged two different catalogued SKUs.
- Nine SKUs were split by "Dual"/"Quad" prefixes (for example Xeon 5160 under
  three keys; 1,630 observations across the split groups).
- Texts carrying only a clock ("291 Mhz", "66 MHz PowerPC") produced an empty key
  and were grouped together; the new rule leaves them unresolved.
- Differences on 47 keys come from the new clock constraint sending conflicting
  mentions (overclocked or mistyped clocks) to family level.

## Known gaps

- **Missing or misparsed text in older sources.** LINPACK, the DEC report vectors,
  the mix table and most SPEC89 rows carry no processor field; their CPU is in the
  system name, which step 2b (system models) must parse. Longbottom's Whetstone
  table yields internal codes ("P1", "P8") and run modes ("Scalar") as processor
  text. These are adapter defects for the pipeline rewrite.
- **Catalogue gaps**: Sapphire/Emerald/Granite Rapids and EPYC Milan (no dated
  Wikipedia SKU tables) resolve to family; Intel Core and Pentium (desktop) have
  no catalogue and are left unresolved, because a brand-level family would mix
  products a decade apart.
- **Ordering variants** such as "100MHz 604 PowerPC" do not match the
  "PowerPC 604" pattern.
- System models, hardware configurations and date events are not yet resolved.
