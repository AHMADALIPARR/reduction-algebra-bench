# PRNG divergence note — Experiment 02 (Wolfram) vs Experiment 01b (Chapel)

**Status: flagged, not fixed.** `wolfram/exp02/exp02_wolfram.wl` is saved
verbatim as delivered. The divergence below is reported for the author's
call on which stream is canonical.

## The divergence

The WL `splitMix64` threads the **fully-mixed value back as the next state**:

```mathematica
splitMix64[state_] := Module[{z},
   z = Mod[state + 16^^9E3779B97F4A7C15, M64];
   (* ... mix z ... *)
   {Mod[z, p], z}];          (* nextState = mixed z *)
```

The Chapel/Python stream (`substrate/splitmix64.py`, `chapel/exp01/shapesweep.chpl`)
increments a **separate counter** and mixes a copy:

```
state += 0x9E3779B97F4A7C15; z = state; z = mix(z); emit z mod p
```

## Measured consequence (Python, exact integer arithmetic)

| | Chapel/Python stream | WL-as-written stream |
|---|---|---|
| 1st value | 6041607748924030458 | 6041607748924030458 (match) |
| 2nd value | 8399375536991227553 | 15441153672277613145 (diverge) |
| checksum Σ₁₀₂₄ mod p | 1388262917130611548 | 17310257690175346081 |

The WL file's own comment says "must match Chapel output exactly" — as
written, it does not. The cross-language checksum gate in `correctness[]`
would fail on the second vector element.

## Not changed

`exp02_wolfram.wl` is byte-faithful to the delivered text. No "fix" applied:
changing the state-threading changes the author's specified algorithm,
and that call belongs to the author.

## Execution status

`wolframscript` is not installed in this environment (2026-10-01), so
Experiment 02 has not run here. All Exp 02 results remain null.
