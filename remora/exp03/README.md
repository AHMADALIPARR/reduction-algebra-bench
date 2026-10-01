<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<!-- Copyright (C) 2026 SnapKitty Collective -->
# Experiment 03 — Remora track

Rank-polymorphic array-language track of the reduction-algebra benchmark,
implemented in Remora (Kennedy) as executed by **remorac** (costigan/remora,
a Python re-imagining of the language with ML syntax).

## Files

- `exp03_remora.remora` — the implementation. Returns a packed 95-int vector:
  checksum bytes (8), first-8 stream values raveled (64), seq/tree/chunked
  gates, SUBLEQ partition identity + taken count + routed/totalV byte vectors,
  gfMul/gfSub test gates.
- `exp03_sweep.remora` — topology sweep kernel (n = 128 / 1024 / 8192).
- `verify_exp03.py` — verify-before-record driver: runs the program, parses
  the output, checks every gate against `substrate/`, emits the results JSON.
- `RUNLOG.md` — what was tried, what executed, what is null and why.

## Semantics (normative, from the Phase-0 spec)

- SplitMix64, seed `0x00BEEFCAFE`, **counter-increment** variant:
  `state_k = seed + (k+1)·0x9E3779B97F4A7C15 (mod 2^64)`, `z = mix(state_k)`,
  emit `z mod p`. Cross-language checksum (first 1024 values, sum mod p):
  **1388262917130611548** — verified bit-for-bit against
  `substrate/splitmix64.py`.
- Goldilocks `p = 2^64 − 2^32 + 1 = 18446744069414584321`.
- SUBLEQ predicate (SPECIFIED): taken iff `d <= 0`; on canonical unsigned
  reps, taken iff `rep == 0` or `rep > p//2`.
- 11 reduction ops: sum, product, min, max, scan, tree_reduction,
  segmented_reduction, subleq_subtract, subleq_compare, subleq_route,
  subleq_reduce; 4-stage attention pipeline
  (subtract → compare → route → reduce); Goldilocks arith spot checks
  (`(p−1)·2 mod p = p−2`, `(5−8) mod p = p−3`, `200·300 = 60000`).

## Implementation notes (remorac dialect realities)

- `int` lowers to **i32 only**; u64 is emulated as 8 little-endian bytes in
  i32 cells, every intermediate kept below 2^19 so all arithmetic is exact.
- Shifts/xor are rebuilt from bit tests; `add64` is an 8-stage carry chain;
  `mul64` is schoolbook with bit-extracted divmod-256; `modp` adds back
  `2^64 − p` when `z ≥ p`; `gfMul` is double-and-add folded over 64 bits.
- The counter-increment variant makes the stream closed-form, so the whole
  1024-stream is one rank-polymorphic `map` — no sequential state threading.
- `iota` requires a **compile-time constant** shape; stream sizes are fixed
  at call sites (`iota 1024`, `iota 64`, `iota 8`).
- SUBLEQ routing is a predicated masked select via scalar-`if` in a binary
  `map` (data-parallel; the dialect has no early exit).
- **No wall-clock builtin exists** in the dialect (verified by source grep),
  so the 3-warmup/20-sample/median timing protocol cannot run: all timing
  values in `results/exp03_remora.json` are null with provenance `unknown`.

## Run

```sh
PYTHONPATH=/tmp/remorac python3 -m remora.cli --target interp exp03_remora.remora
python3 verify_exp03.py   # verify-before-record + results JSON
```
