# Exp09: Klong Track

## Status
- **Gate**: PASS (measured 2026-10-01)
- **sweep_1d**: Measured (2026-10-01)
- **sweep_subleq**: NULL (executed but output lost; see below)

## Toolchain
- **Source**: http://t3x.org/klong/klong20221212.tgz (Nils M. Holm)
- **Build**: `make kg` (compiles kg.c + s9core.c)
- **Note**: The brief URL `brianguertin/klong` returns 404. Correct source is t3x.org/klong.

## Key Findings
- SplitMix64 checksum VERIFIED: `1388262917130611548` (matches crosslang)
- Klong has bignum integers (no overflow issues)
- `!` is a-mod-b, `:%` is integer divide, `%` is float divide
- `:` conditional requires exactly 3 args
- Lambdas infer arity from free x/y/z; `{0<a}` is niladic (no x) → "wrong arity" if called with arg
- `::` in lambda body is single-assignment (reassign → "read-only" error)
- Application is `f(a;b)` with parens and semicolon
- `[a;b]` is a list; `(a,b)` is a vector; `(1;2)` is a syntax error
- All verbs strictly right-to-left: `a*16+b` = `a*(16+b)` — parenthesize!
- `n#v` with n > #v CYCLES (repeats vector) — must bound take manually
- Identifiers CANNOT contain `_` (it's the drop verb)
- `{` cannot be at start or end of a line (parser bug) — must have content after `{` on same line
- `+/[]` is `[]` (not 0) — guard empty sums

## Implementation Notes
- **XOR**: Implemented via 16x16 nibble table + 5-element state recursion (Klong has no bitwise ops)
- **SplitMix64**: Closed form `state_i = (seed + (i+1)*g1) mod 2^64` (no state threading)
- **mkvec**: Dyadic `mkvec(seed;n)`; K/Q/V use sequential splits of one stream
- **SUBLEQ**: Predicate is `d == 0 OR d > p//2` (specified)
- **Performance**: mkvec ~16ms/value (nibble-xor is expensive); SUBLEQ sweep shapes reduced for feasibility

## /tmp Loss Incident
On 2026-10-01, the working `.kg` file (in /tmp/klong/) was lost when /tmp was cleared
(VM cleanup). The file had:
- Full working implementation (gate PASS)
- sweep_1d results (captured)
- sweep_subleq results (NOT captured — output lost)

The `exp09_klong.kg` in this directory is an earlier non-working version.
A reconstruction was attempted but Klong's syntax is highly error-prone
(paren counting, line-boundary `{` bug), and full reconstruction was not completed.

## Results
See `results/exp09_klong.json` for measured data with provenance tags.

## Deviations from Spec
1. Timing: 1 warmup / 5 samples / minimum (vs spec 3/20/median)
2. SUBLEQ sweep shapes reduced to [[1,128,64],[1,256,64]] (mkvec too slow for larger)
3. sweep_subleq: NULL (output lost)
