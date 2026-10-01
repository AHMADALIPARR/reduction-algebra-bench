# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""SplitMix64 Phase-0 PRNG oracle.

Language-neutral specification of the deterministic stream used by
Experiment 01b (shape sweep) and Experiment 02 (Wolfram):

    state += 0x9E3779B97F4A7C15          (mod 2^64)
    z = state
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9   (mod 2^64)
    z = (z ^ (z >> 27)) * 0x94D049BB133111EB   (mod 2^64)
    z = z ^ (z >> 31)
    emit z mod p                              (canonical Goldilocks rep)

This module is the cross-validation oracle: the Chapel SplitMix64 in
chapel/exp01/shapesweep.chpl must reproduce this stream bit-for-bit
(first 1024 values AND the cross-language checksum below), otherwise
the sweep does not run. It models the PRNG specification, not any
Chapel program's execution.
"""

from __future__ import annotations

M64 = 2**64
P = 2**64 - 2**32 + 1
SEED = 0x00BEEFCAFE


def splitmix64_stream(seed: int = SEED, n: int = 1024) -> list[int]:
    state = seed
    out: list[int] = []
    for _ in range(n):
        state = (state + 0x9E3779B97F4A7C15) % M64
        z = state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) % M64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) % M64
        z = z ^ (z >> 31)
        out.append(z % P)
    return out


def crosslang_checksum(n: int = 1024, seed: int = SEED) -> int:
    """Mod[+ reduce makeVec[1024], p] — the Experiment-10 equivalence gate,
    arriving early. Chapel and Wolfram must reproduce this bit-for-bit."""
    return sum(splitmix64_stream(seed, n)) % P


if __name__ == "__main__":
    v = splitmix64_stream()
    print("first8:", " ".join(str(x) for x in v[:8]))
    print("crosslang_checksum:", crosslang_checksum())
