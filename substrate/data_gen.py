# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""Deterministic seeded data generator.

How goldilocks_values [2,3,4] seed the generator:
  seed_int = int.from_bytes(SHA256(b"reduction-algebra-bench:2,3,4")[:8], "big")
A single random.Random(seed_int) stream is then drawn in a fixed order:
first vector `a`, then `b`, then `c`, each n canonical field elements via
randrange(p). Same seed values -> byte-identical vectors on any machine
(random.Random with an int seed is a stable Mersenne Twister stream).

The experiment consumes one 1000-element column (shape [1000,1]) of the
[1000,1000,1] input: vector `a`. Vectors `b` and `c` are the second operand
and the route-alternative for the SUBLEQ ops.

Vectors are written as decimal ints, one per line (a.txt, b.txt, c.txt),
so the Chapel program and the Python reference consume IDENTICAL inputs.
"""

from __future__ import annotations

import hashlib
import random

from .goldilocks import P

SEED_TAG = b"reduction-algebra-bench"
CANONICAL_VALUES = [2, 3, 4]  # goldilocks_values from chapel_experiment_01.json
N = 1000


def seed_from_values(values: list[int] = CANONICAL_VALUES) -> int:
    payload = SEED_TAG + b":" + b",".join(str(v).encode() for v in values)
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def gen_vector(rng: random.Random, n: int) -> list[int]:
    return [rng.randrange(P) for _ in range(n)]


def gen_experiment(
    values: list[int] = CANONICAL_VALUES, n: int = N
) -> dict[str, list[int]]:
    rng = random.Random(seed_from_values(values))
    # Fixed draw order — do not reorder.
    a = gen_vector(rng, n)
    b = gen_vector(rng, n)
    c = gen_vector(rng, n)
    return {"a": a, "b": b, "c": c}


def write_vectors(vecs: dict[str, list[int]], directory: str) -> None:
    import os

    os.makedirs(directory, exist_ok=True)
    for name, v in vecs.items():
        with open(os.path.join(directory, f"{name}.txt"), "w") as f:
            f.write("\n".join(str(x) for x in v) + "\n")


def read_vectors(directory: str) -> dict[str, list[int]]:
    import os

    out: dict[str, list[int]] = {}
    for name in ("a", "b", "c"):
        with open(os.path.join(directory, f"{name}.txt")) as f:
            out[name] = [int(line.strip()) for line in f if line.strip()]
    return out
