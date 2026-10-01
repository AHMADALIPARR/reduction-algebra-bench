# Experiment 05 — Singeli

**Status (2026-10-01): implementation written, NOT executed. All measurement
fields are null.**

## What this is

`exp05_singeli.singeli` implements the Phase 0 reduction-algebra benchmark
in Singeli:

- SplitMix64, seed `0x00BEEFCAFE`, **counter-increment** variant (canonical
  stream; cross-language checksum `1388262917130611548` over `makeVec[1024]`)
- Goldilocks `p = 18446744069414584321` vector kernels over `[4]u64` SIMD
  lanes: `gf_add4`, `gf_sub4`, `gf_mul4` (widening multiply via the C
  backend's `unsigned __int128`, since 64×64→128-bit is not expressible in
  pure `[4]u64` lanes)
- Reductions: strip-mined sequential fold (`reduce_seq`), in-place pairwise
  tree fold (`reduce_tree`)
- SUBLEQ routed reduction with the SPECIFIED predicate (taken iff `d <= 0`,
  i.e. canonical rep `== 0` or `> p/2`)

## Shape note (corrects the build brief)

The brief described Singeli as "SIMD DSL for .NET / ships as a NuGet
package". That is incorrect: Singeli ([mlochbaum/Singeli](../..)) is a
metaprogramming DSL **implemented in BQN** whose backend **emits C**. There
is no .NET involvement. The idiomatic structure is therefore kernels in
`.singeli` compiled with the `singeli` driver to C, then to a binary with a
C toolchain — which is exactly what this file targets. `main` is present as
a stub; the sweep driver (timing via `clock_gettime`, verify-before-record,
JSON emission) is meant to live in the same file once compiled.

## Why null

- No `dotnet` SDK exists on this machine (and Singeli wouldn't use it
  anyway).
- The Singeli compiler's BQN host was built and the compiler itself runs,
  but compiling this benchmark through it was explicitly de-scoped by the
  run coordinator (BQN/CBQN is not one of the 9 benchmark languages).
- Per the standing rule — *the real toolchain is the only judge; no
  results claimed until executed* — every measured field in
  `results/exp05_singeli.json` is null with provenance `unknown`.

## To run (for whoever picks this up)

```
singeli exp05_singeli.singeli -o exp05_singeli.c
cc -O3 exp05_singeli.c -o exp05_singeli
./exp05_singeli
```

The verify gate must reproduce checksum `1388262917130611548` before any
timing is recorded. Timing protocol: 3 warmup, 20 samples, median, tagged
per op.

## Open spec questions

1. `gf_mul4` widening: is `emit{}` with `unsigned __int128` the intended
   Singeli idiom, or is there a vector widening-multiply in
   `arch/iintrinsic` I should use instead? (Author call.)
2. Tail handling for `n` not divisible by 4 in `reduce_seq` is scalar;
   whether the benchmark wants the scalar tail timed separately is
   undecided.
