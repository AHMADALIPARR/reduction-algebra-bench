# Reduction Algebra / SUBLEQ Attention Benchmark

A benchmark harness for attention-as-reduction-algebra over the Goldilocks
field, executed as SUBLEQ-style branch-gated reductions. Experiment 01 is
the Chapel vertical slice: the full op set from
`spec/chapel_experiment_01.json`, computed in Chapel and validated
bit-for-bit against a pure-Python scalar reference before any timing is
recorded.

## Design space

| Experiment | Language / runtime | Scope | Status |
|---|---|---|---|
| 01 — Chapel | Chapel 2.10.0, single locale, single machine | All 11 JSON ops + full attention pipeline (subtract → compare → route → reduce) over n=1000 Goldilocks vectors | **Complete — 14/14 values validated, 13 timings measured** (`results/exp01_chapel.json`) |
| 02+ | TBD (per author spec) | — | Not started |

Result schema (`results/exp01_chapel.json`) tags every number with
provenance — `measured` / `derived` / `specified` / `unknown` — and carries
an `environment` block shaped for multi-locale runs later. Anything that
could not run or is not yet specified is `null` with provenance `unknown`,
never fabricated.

## The seven constraints this build obeys

1. **Vertical slice first.** Experiment 01 (Chapel) implements the whole
   pipeline end-to-end before any other experiment is started.
2. **True SUBLEQ semantics.** A SUBLEQ branch is taken when the subtraction
   result is ≤ 0 in the signed interpretation — not when an unsigned
   comparison fires.
3. **Single machine, single locale now; schema ready for multi-locale.**
   Timings are single-locale; the result schema already allows per-locale
   entries later.
4. **Validate before timing.** Every Chapel value is compared against the
   scalar reference (`substrate/reference.py`). Any mismatch invalidates
   that op's timing (timing → null, provenance `unknown`).
5. **Nulls, never fabricated.** Unrunnable measurements and unspecified
   fields are `null` with provenance `unknown`.
6. **Canonical field convention.** All field elements are canonical reps
   `0 .. p-1` with `p = 2^64 − 2^32 + 1 = 18446744069414584321`; a rep is
   negative (signed) iff it is `> p//2`. Field elements are serialized as
   decimal strings.
7. **AGPLv3 + per-file SPDX headers; git init + commit, no push.**
   Nothing leaves this machine without explicit authorization.

## Field kernels — provenance

`chapel/exp01/goldilocks_kernels.chpl` is the only field arithmetic the
benchmark uses. Its three kernels were each verified against the exact
Python scalar reference over ~80,000 adversarial + random canonical pairs
(0 errors each):

- `gfAdd` — carry-free form. The two author-supplied variants
  (`user_kernels_variant1.chpl`, `user_kernels_variant2.chpl`) both failed
  verification (variant 1: off-by-one on the carry path, e.g.
  `gfAdd(P-1,P-1) = P-1` instead of `P-2`; variant 2: catastrophically
  wrong, e.g. `gfAdd(0,0) = 2^32-1`). Both files are preserved verbatim in
  `chapel/exp01/` with STATUS headers and are **not** used by the build.
  The verified replacement stands pending the author's fix — the author
  was notified and may override the substitution.
- `gfSub` — kept verbatim from author variant 1 (verified correct).
  Argument order: `gfSub(x, y) = (x − y) mod p`; SUBLEQ `mem[b] −= mem[a]`
  calls `gfSub(B[i], A[i])`.
- `gfMul` — double-and-add via `gfAdd` (verified correct). Variant 1's
  `uint(128)` form does not compile on Chapel 2.10 (no 128-bit integer
  type: `error: illegal size 128 for uint`), so it could not be kept.

## Measured results (Experiment 01)

Measured 2026-10-01 on this host: `chpl version 2.10.0` (LLVM 18.1.3),
single locale, mean of 5 reps, n=1000. Full provenance-tagged record in
`results/exp01_chapel.json`. All 14 op values validated against the scalar
reference (including `tree_reduction == sum`, the tree/sequential
equivalence law, holding on real Chapel execution).

| op | time (s) | provenance |
|---|---|---|
| sum (sequential baseline) | 6.0e-06 | measured |
| product | 1.39e-03 | measured |
| min | 3.72e-05 | measured |
| max | 6.4e-06 | measured |
| scan (exact prefix) | 7.6e-06 | measured |
| tree_reduction (forall tree) | 4.58e-05 | measured |
| segmented_reduction (4×250) | 5.8e-06 | measured |
| subleq_subtract | 5.2e-06 | measured |
| subleq_compare | 3.0e-06 | measured |
| subleq_route | 7.6e-06 | measured |
| subleq_reduce | 1.3e-05 | measured |
| arith_subleq_subtract | 3.4e-06 | measured |
| arith_subleq_multiply | 7.418e-04 | measured |
| attention_subleq_reduce | — (pipeline value; same as subleq_reduce) | measured (value), unknown (timing) |

Unresolved slots (`sealed`, `consensus`, `commitment`, `proof`, `glyphs`,
`META`, `Omega`, `resonance`, `worm_seal`): all null, provenance unknown —
the author's reduction-algebra spec has not arrived yet.

Notes on kernel choices: Chapel's native `+ reduce` / `+ scan` on
`uint(64)` wrap mod 2^64, not mod p, so their numbers would be invalid
here — they are not recorded. `sum` is a sequential `gfAdd` baseline;
`tree_reduction` is the parallel double-buffered tree (a naive in-place
tree has a read/write race; double buffering is required for
correctness).

## Layout

- `spec/chapel_experiment_01.json` — experiment spec (author-supplied).
- `substrate/` — stdlib-only Python: `goldilocks.py` (field arithmetic),
  `reference.py` (scalar implementations of all ops + attention pipeline),
  `data_gen.py` (seeded deterministic vectors; seed =
  SHA256("reduction-algebra-bench:2,3,4")[:8], draw order a, b, c),
  `emit.py` (provenance-tagged canonical JSON), `laws.py` (law table).
- `chapel/exp01/` — `exp01.chpl` (benchmark), `goldilocks_kernels.chpl`
  (verified kernels), `user_kernels_variant{1,2}.chpl` (author variants,
  preserved verbatim, failing, unused), `run_exp01.py` (orchestrator:
  generate → build → run → validate → emit), `vectors/` (deterministic
  inputs, regenerable).
- `results/exp01_chapel.json` — the measured record.
- `tests/test_substrate.py` — 30 tests, all green.

## Run it

Requirements: Python 3.10+ (stdlib only), Chapel ≥ 2.10 (`chpl` on PATH).

```sh
# substrate correctness suite
python3 -m pytest tests/ -q

# full experiment: generate vectors, build Chapel, run, validate, emit
python3 chapel/exp01/run_exp01.py
# -> validated: 14/14 ops, timed: 13 ; writes results/exp01_chapel.json
```

If `chpl` is missing or the build fails, the orchestrator emits null
measurements with provenance `unknown` instead of failing or inventing
numbers.

## Open items

- The author's reduction-algebra spec is still awaited; on arrival it
  integrates against the law table (`substrate/laws.py`) and fills the
  unresolved slots. The glyph set in the author's plan (▣/⊛) differs from
  the screenshot-derived engine (▦/⊗) — to be reconciled before either is
  baked into code.
- The `gfAdd` substitution (verified replacement for the two failing
  author variants) stands pending the author's fix or override.

## License

AGPLv3 — see `LICENSE`. Per-file SPDX headers
(`Copyright (C) 2026 SnapKitty Collective`) throughout.
