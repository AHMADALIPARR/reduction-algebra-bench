<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<!-- Copyright (C) 2026 SnapKitty Collective -->
# Experiment 04 — SaC (Single Assignment C) track

Array-language track of the reduction-algebra benchmark in SaC, written
idiomatically: with-loops for array construction, `fold()` for reductions,
rank-generic signatures where natural.

## Files

- `exp04_sac.sac` — the implementation (11 reduction ops, 4-stage SUBLEQ
  attention pipeline, Goldilocks field arithmetic, SplitMix64 stream).
- `RUNLOG.md` — toolchain attempts and why nothing executed.

## Semantics (normative, from the Phase-0 spec)

- SplitMix64, seed `0x00BEEFCAFE`, **counter-increment** variant; canonical
  checksum **1388262917130611548** (see `substrate/splitmix64.py`).
- Goldilocks `p = 2^64 − 2^32 + 1`; `ulong` wraps mod 2^64 natively.
- SUBLEQ predicate (SPECIFIED): taken iff `rep == 0` or `rep > p/2`.
- 11 reduction ops: sum, product, min, max, scan, tree_reduction,
  segmented_reduction, subleq_subtract, subleq_compare, subleq_route,
  subleq_reduce; attention pipeline
  subtract → compare → route → reduce; Goldilocks spot checks on [2,3,4].

## Status

**Not executed.** `sac2c` is not installed in this environment; see RUNLOG.md
for the full attempt log (apt has no package, GitHub release gone, source
build from gitlab.sac-home.org attempted). Consequently every measured value
in `results/exp04_sac.json` is null with provenance `unknown`. The `.sac`
source is complete and written to compile with:

```sh
sac2c -o exp04_sac exp04_sac.sac
./exp04_sac
```

Timing (3 warmup / 20 samples / median) is specified in the source's closing
comment but not wired: the SaC stdlib exposes no wall-clock extrinsic, so
timing stays null until a clock extrinsic is added.
