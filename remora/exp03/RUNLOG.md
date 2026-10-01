# RUNLOG — Remora track (exp03)

SPDX-License-Identifier: AGPL-3.0-or-later
Copyright (C) 2026 SnapKitty Collective

Date: 2026-10-01. All times PDT. All results below are from real
`remorac` interpreter runs; nothing is modeled or fabricated.

## Toolchain

- Implementation: `remorac` (costigan/remora on GitHub — note the 'c';
  the brief's `remora-lang/remora` 404s). A Python re-imagining of Remora
  with ML-style syntax (`let`/`def`/`\` lambdas), not the Kennedy Haskell
  implementation.
- Location: `~/workspace/vendor/remorac` (re-cloned after a VM restart
  wiped /tmp; /tmp is ephemeral on this host).
- Invocation: `PYTHONPATH=~/workspace/vendor/remorac python3 -m remora.cli --target interp <file>`
- Startup ~2s per run. No wall-clock builtin exists in the dialect
  (verified by grep of the runtime sources), so the 3-warmup/20-sample
  timing protocol cannot be executed: all `timings_ns` are null with
  provenance `unknown`.

## Dialect facts (all established by execution on 2026-10-01)

- `int` is i32 only; literals wrap mod 2^32; `modulo` is floored;
  `/` is float division. No quotient operator, no `^`, no bitwise ops,
  no 64-bit ints, no clock.
- `fold`/`scan`/`map` (unary and binary) work; `reduce/1` fails to lex;
  `trace` parses but has no runtime implementation.
- `iota` requires a compile-time constant shape: stream sizes are fixed
  per definition (`stream1024`, `stream64`, `stream128`, `stream8192`,
  `stream8v`, `stream64_64`, `stream64_128` are separate monomorphic defs).
- `def` bodies must start on the `=` line; vector literals cannot span
  lines; array literals must be bound with `let` before use as map/fold
  operands; `--` comments break parsing after defs begin.

## remorac typechecker limitations (all hit and worked around 2026-10-01)

1. First-class `(==)` inside `map (==)` misattributes a type error to an
   unrelated def ("comparison == expects numeric operands"). Workaround:
   `eq8` replaced by `isZero8` via `gfSub8` (sum of bytes == 0).
2. Indexing into a function-result array (e.g. `s9[0]` where
   `s9 = add64c a b`) → "indexing expects an array operand". Workaround:
   removed 9-element `add64c`/`gfNorm`; `add64` rewritten with a direct
   carry chain plus a scalar `carry64 a b` returning 0/1.
3. `ge_p`-based `modp` triggered the same indexing error. Workaround:
   `modp z = if carry64 z negp8 == 1 then add64 z negp8 else z`.
4. Nullary stream defs combined with `eq8` triggered it. Workaround:
   streams take a dummy parameter (`stream1024 d`).
5. Inline lambda `map (\c -> fold gfAdd8 zero8 c)` combined with other
   folds triggered it. Workaround: named `def sum8 a = fold gfAdd8 zero8 a`.
6. **Binary `map` over functions that index their parameters fails**
   (`map gfSub8 kk qq`, `map carry64 kk nqq` → "indexing expects an array
   operand"), while unary `map` works (`map pminus qq` fine). Workaround:
   unary index-map: `map (\i -> gfSub8 kk[i] qq[i]) (iota 64)`.
7. The monolithic `exp03_remora.remora` still fails whole-program
   typecheck, so execution uses five split programs sharing one def
   library (the defs alone typecheck and run fine).

## Real arithmetic bugs found and fixed in the agent's own code

- `gfAdd8` initially ignored 64-bit overflow (the `ge_p` check was
  insufficient when `add64` wrapped); a 4-element fold was off by exactly
  2^32−1. Fixed with `carry64`; the fold then matched Python.
- `pminus` byte-4 bug: used `0 - b[4]` instead of `255 - b[4]`
  (p = 0xFFFFFFFF00000001).
- A `pm3` test vector was wrong in the test, not the code: correct
  p−3 = [254,255,255,255,254,255,255,255] (verified in Python).
- **Checksum off-by-one**: the oracle increments state BEFORE mixing, so
  value_k = mix(seed + (k+1)·INC); the stream uses `u64_of_k (k+1)`.
- **`u64_of_k` bit-width bug (the red-gate root cause)**: the helper only
  emitted bits 0–9, so `u64_of_k 1024` produced byte1=2 instead of 4.
  The last stream element (index 1023) was wrong, which poisoned every
  sum over n≥1024 while n≤64 sums passed. Fixed by computing bits 8–13
  explicitly; the checksum then matched.

## Executed results (real interpreter output, 2026-10-01)

| program | output | gate |
|---|---|---|
| exp03a_checksum.remora | [92,235,106,142,196,25,68,19] = 1388262917130611548 | checksum MATCH |
| exp03a_first8.remora | [250,61,221,226,60,26,216,83,…] (64 bytes) | bit-for-bit vs substrate ✓ |
| exp03b_reduce.remora | [1,1] | seq==tree ✓, seq==chunked ✓ |
| exp03c_subleq.remora | [1,34] | partition identity ✓, taken=34 matches Python ref ✓ |
| exp03d_gfops.remora | [1,1,1] | gfMul 200·300 ✓, (p−1)·2 ✓, 5−8 ✓ |
| exp03_sweep.remora | n=128 → 17025989809213925053 ✓; n=1024 → 1388262917130611548 ✓; n=8192 → 8386807993349546782 ✓ | all match Python |

`verify_exp03.py` runs all six programs fresh and asserts every gate:
**VERIFY-BEFORE-RECORD: PASS**. Results in
`results/exp03_remora.json` with per-value provenance.

## Nulls

- All `timings_ns` are null / provenance `unknown`: the remorac dialect
  exposes no wall-clock (no `clock` builtin; confirmed by source grep),
  so the 3-warmup/20-sample/median protocol is not executable here.
- Unresolved slots (sealed, consensus, commitment, proof, glyphs, META,
  Omega, resonance, worm_seal): null / unknown — not part of this track.

## Files

- `remora/exp03/exp03_remora.remora` — monolithic source (does not
  typecheck under remorac; kept as the readable reference)
- `remora/exp03/exp03a_checksum.remora`, `exp03a_first8.remora`,
  `exp03b_reduce.remora`, `exp03c_subleq.remora`, `exp03d_gfops.remora`,
  `exp03_sweep.remora` — executed split programs
- `remora/exp03/verify_exp03.py` — verify-before-record driver
- `remora/exp03/README.md`, `remora/exp03/RUNLOG.md` (this file)
- `results/exp03_remora.json` — provenance-tagged results
