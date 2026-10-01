# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective

# Exp 06 RUNLOG — TinyAPL (2026-10-01)

## Attempt 1: Brief premise check — FAILED (wrong premise)

The brief described TinyAPL as "a C interpreter" at
`github.com/TinyAPL/TinyAPL`. That URL returns 404. There is no C
interpreter. **TinyAPL is RubenVerg/TinyAPL: a tiny APL dialect interpreter
written in Haskell.** The brief's premise was wrong; the track was rebuilt
from the real project.

## Attempt 2: Acquire runtime — OK

Downloaded the official release 0.12.0.0 native Linux binary:
`https://github.com/RubenVerg/TinyAPL/releases/download/0.12.0.0/tinyapl`
(ELF x86-64, runs). No build required.

## Attempt 3: Language probing — multiple corrections

Probed the interpreter with small programs (all via Python-generated files
with explicit `\uXXXX` escapes after the glyph hazard below):

- **Lines are independent scopes.** A multi-line script does NOT share
  bindings across lines. The whole program must be ONE line joined with `⋄`.
- **Arrays lowercase, functions UPPERCASE** — enforced by the parser
  (`A ← <array>` fails: "Invalid assignment of array to function name").
- **Numbers are IEEE doubles.** `18446744069414584321` prints as `...4320`.
  Exact 64-bit is impossible natively → 4×16-bit limb design.
- **`≠` is not-equal, NOT bitwise xor.** The first `MkStream` implementation
  used `≠` as xor and produced a wrong stream. Rewrote xor as arithmetic
  bit extraction (`X1`).
- **`+/` reduces along the FIRST axis** (not last, unlike Dyalog). Discovered
  when `{+/⍵}¨` on rank-2 arrays did not distribute; the tree-reduction idiom
  is reshape + first-axis reduce: `+/ ⟨2 ⋄ 4⟩ ⍴ ⍳ 8`.
- **Reverse is `⊖` (U+2296), not `⌽`** (`⌽` is a syntax error).
- **Catenate is `⍪` (U+236A), not `,`** (`,` is ravel). `⍪/` reduce does NOT
  catenate.
- **`⌷`: index is the LEFT argument, 0-based** (`1 ⌷ v` → 2nd element). No
  strided/vector `⌷` → medians computed in the Python driver.
- **`⍺⍺` function operands do NOT work** ("No binding found"). Timing loops
  must be unrolled by the Python code generator.
- **Glyph hazard:** a typed `¨` (U+00A8) arrived in files as `ª` (U+00AA),
  confirmed via `od`. All APL files are written via Python with explicit
  `\uXXXX` escapes. This is non-negotiable.
- `⎕←` prints; `⎕unix` returns fractional seconds (usable for timing).
- `⍝` comments run to end of LINE → unusable in the one-line program except
  at the very end.
- `2 ⊥ ⟨1⋄0⋄1⟩` → 5 (flat vectors only); `⍳ 5` → `⟨0⋄1⋄2⋄3⋄4⟩` (0-based).

## Attempt 4: Dfn library — bugs found and fixed

- **`PairGfAdd` bit-64 carry bug.** The first version used raw `PassW+ModP`
  (single conditional subtract). Sums of two field elements reach 2p−2, which
  has bit 64 set; the shortcut dropped it. Fixed by routing through `GfAdd`
  (5-limb add + conditional subtract).
- **`2 ⍣ (...)` vs `2 * (...)`.** Used the power operator `⍣` where
  multiplication `*` was meant. Fixed.
- **Weight layout in `X1`.** `⟨16⋄n⟩⍴w` paired incorrectly; broadcast
  `w × ⍉m` pairs with the first axis correctly. Fixed.
- **Uppercase array locals rejected.** All renamed lowercase.
- **`X1` optimization.** The first xor used dyadic `⊤` encode (6.6 s for
  MkStream64). Rewrote with arithmetic bit extraction (5.7 ms for 4 elems,
  ~6× faster). `⊤` on nested/rank-2 gives "Domain error".
- **`Attn` subtraction order.** First version computed `⍵ Sub ⍺`; the oracle
  expects `⍺ Sub ⍵`. Fixed and re-verified.

## Attempt 5: Self-test — ALL PASS (2026-10-01)

`/tmp/langbuild/verify_selftest.py`: all 11 self-tests pass bit-for-bit vs
the substrate Python oracle (T_SUM, T_GFADD2, T_GFMULSELF, T_MIN, T_MAX,
T_TREEADD, T_TREEMUL, T_SHR, T_XOR, T_SUB, T_ADDWRAP). Stream head =
6041607748924030458, matching the oracle.

New kernels (Scan8, SegRed, Cmp, Route, Attn) verified bit-for-bit vs oracle
2026-10-01 (SCAN, SEG, ROUTE, ATTN all match after the Attn fix).

## Attempt 6: Sweep n=128 — OK (2026-10-01, 2m24s)

All 14 kernels: 20/20 samples collected, ALL escape checksums match the
oracle bit-for-bit. Stream checksum verified.

Medians (n=128): sum 13.5 ms, product 758 ms, min 1.9 ms, max 2.0 ms,
scan 2.29 s, tree_reduction 289 ms, segmented 49.7 ms, subleq_subtract
83.6 ms, subleq_compare 6.0 ms, subleq_route 2.7 ms, subleq_reduce 5.6 ms,
attention 145 ms, gf_subtract 185 ms, gf_multiply 1.82 s.

## Attempt 7: Sweep n=1024 — OK (2026-10-01, ~7 min)

Re-ran after the /tmp wipe. All 14 kernels: 20/20 samples, ALL escapes
match the oracle bit-for-bit. Canonical checksum gate PASSED
(1388262917130611548).

Medians (n=1024): sum 5.3 ms, product 3.43 s, min 13.4 ms, max 8.0 ms,
scan 7.68 s, tree_reduction 695 ms, segmented 713 ms, subleq_subtract
373 ms, subleq_compare 28.2 ms, subleq_route 7.1 ms, subleq_reduce 3.2 ms,
attention 387 ms, gf_subtract 346 ms, gf_multiply 3.65 s.

`results/exp06_tinyapl.json` emitted with verify_before_record=True,
zero nulls. All values carry {value, provenance}.

## Notes

- The SplitMix64 stream is embedded as literals (Python-generated). The
  interpreter's xor-heavy stream gen is ~27 ms/element; xor is not used by
  any timed kernel. The APL `MkStream` is present and verified, just not on
  the timed path.
- `goldilocks_subtract` and `subleq_subtract` time the same expression
  (`ww Sub vv`); both are recorded (spec lists them as separate ops).
- Do NOT commit. Repo is local-only.
