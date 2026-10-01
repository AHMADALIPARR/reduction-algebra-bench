# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""Goldilocks field arithmetic — exact, canonical, no silent overflow.

Field: F_p with p = 2^64 - 2^32 + 1 = 18446744069414584321.

CONVENTION (field-arithmetic convention for this benchmark):
  * Every value is stored in canonical representative form: an int in
    0 .. p-1. Python big ints make every op exact; reduction is always
    `mod p`, never silent.
  * The SUBLEQ branch predicate ("branch when subtraction result <= 0")
    uses the SIGNED interpretation of the canonical rep:
        rep == 0            -> zero      (branches: 0 <= 0)
        1 <= rep <= p//2    -> positive  (does not branch)
        p//2 < rep <= p-1   -> negative  (branches)
    i.e. is_negative(rep) <=> rep > p//2. Zero is not negative.
"""

P = 2**64 - 2**32 + 1
assert P == 18446744069414584321
HALF = P // 2  # 9223372034707292160


def canonical(x: int) -> int:
    """Reduce any integer to its canonical representative in 0..p-1."""
    return x % P


def add(a: int, b: int) -> int:
    return (a + b) % P


def sub(a: int, b: int) -> int:
    return (a - b) % P


def mul(a: int, b: int) -> int:
    return (a * b) % P


def neg(a: int) -> int:
    return (-a) % P


def from_int(x: int) -> int:
    """Lift any Python int into the field (canonical)."""
    return x % P


def is_negative(rep: int) -> bool:
    """Signed interpretation: rep > p//2 means negative. Zero is not negative."""
    r = rep % P
    return r > HALF


def is_zero(rep: int) -> bool:
    return (rep % P) == 0


def branch_taken(rep: int) -> bool:
    """SUBLEQ branch predicate: taken iff subtraction result <= 0 (signed)."""
    r = rep % P
    return r == 0 or r > HALF


def to_signed(rep: int) -> int:
    """Canonical rep -> symmetric signed integer in [-(p-1)//2, (p-1)//2]."""
    r = rep % P
    return r - P if r > HALF else r
