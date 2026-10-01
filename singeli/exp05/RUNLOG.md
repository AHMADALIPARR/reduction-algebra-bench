# RUNLOG — Experiment 05 (Singeli)

Date: 2026-10-01. Agent 2 of the 3-agent guardian build.

## What was tried

1. Read the brief (`guardian/prompts/agent2.txt`), the spec entries in
   `spec/benchmarks_all_languages.json`, `substrate/splitmix64.py`,
   `results/exp01b_shapesweep.json` (schema), and
   `wolfram/exp02/PRNG_DIVERGENCE_NOTE.md`.
2. Checked for a `dotnet` SDK: **absent** (`which dotnet` → nothing).
3. Researched what Singeli actually is (web): it is **not** a .NET/NuGet
   component. Singeli is a SIMD metaprogramming DSL implemented in BQN
   (mlochbaum/Singeli); its backend emits C. The brief's "NuGet package"
   premise was wrong — recorded in README.md.
4. Time-box for a Singeli runtime (~15 min) expired; the run coordinator
   additionally steered *away* from the BQN/CBQN route (not one of the 9
   benchmark languages), so no compile of `exp05_singeli.singeli` was
   attempted here.
5. Wrote the full idiomatic implementation anyway:
   `singeli/exp05/exp05_singeli.singeli` — SplitMix64 (counter-increment),
   `[4]u64` Goldilocks kernels, sequential + tree reductions, SUBLEQ routed
   reduction with the SPECIFIED `d <= 0` predicate, `main` stub.

## What executed

Nothing. No Singeli compilation, no binary, no timings.

## Results

`results/exp05_singeli.json`: all measurement fields null, provenance
`unknown`. No numbers fabricated. The verify gate (checksum
`1388262917130611548` over `makeVec[1024]`) has not been exercised.

## Next step for a real run

`singeli exp05_singeli.singeli -o exp05_singeli.c && cc -O3
exp05_singeli.c -o exp05_singeli && ./exp05_singeli`, on a machine with the
Singeli compiler's BQN host available. Flesh out `main` into the full
sweep driver first (timing, verify-before-record, JSON emission).
