# Maintenance inventory snapshot

Date: 2026-09-27. Code baseline: `d2e4329`. Owner:
[cleanup inventory](../../cleanup-inventory.md).

- `module-imports.csv`: AST `ImportFrom` statements referencing `cpushowspeed`
  in all top-level package modules; aliases appear under `symbols` as imported names.
- `command-entrypoints.csv`: top-level functions decorated with `.command(...)`;
  this is not a complete runtime command/alias tree.
- `exact-function-bodies.csv`: groups with equal AST function bodies, ignoring
  locations; signatures/decorators are not compared. Equivalence still needs review.
- `derived-artifacts.csv`: current file count/logical-byte size, known producer,
  known consumers and provisional disposition. Every `rebuild_verified` is false.
- `audit-hash-checks.csv`: SHA-256 checks of path mappings in classical audit
  `input_sha256`, `inputs_sha256`, `code_sha256` fields. Relative paths resolve
  from repository root. Scalar code hashes for environment/source diagnostics
  were resolved to their defining modules by inspecting the hash-writing code.

The snapshot was produced by read-only AST/filesystem inspection and SHA-256
comparison. Only known statically traced consumers are listed; an empty consumer
field never proves safe deletion. Filesystem sizes and hash comparisons describe
this date's checkout and local cache. No source or fitted score was changed.

## Implemented cleanup verification

- `cleanup-parity.csv`: preparation byte parity, primary fit numerical parity
  and unchanged full-chain numerical fields.
- `error-policy-comparison.csv`: modern edge P95 before/after selecting the
  common observed-target relative error. Factors and CI95 are unchanged.
- `removed-validation-files.csv`: exact paths, logical sizes and hashes of this
  cleanup's transient verification files, removed only after parity passed.

[Implementation report](../../calibration-cleanup.md) owns these follow-up results.
