# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""Scalar reference implementations for every op in chapel_experiment_01.json.

These are the ground truth. Every per-language kernel must match these
bit-for-bit (canonical field elements) before any of its timings are valid.

Interpretation decisions (all documented here; Chapel must implement the same):
  * min/max compare CANONICAL representatives as integers (0..p-1).
  * min/max of an empty vector raise ValueError (no identity exists).
  * sum of empty = 0, product of empty = 1 (additive/multiplicative identity).
  * scan = prefix sums (add), same length as input; empty -> [].
  * tree_reduction = pairwise tree summation mod p (odd element carried up).
  * segmented_reduction splits the vector into fixed segments of SEG_LEN
    (default 250 -> 4 segments for n=1000) and sums each segment mod p.
  * subleq_subtract(a, b) = elementwise (b_i - a_i) mod p  (SUBLEQ: mem[b] -= mem[a]).
  * subleq_compare(a, b) = elementwise branch predicate of the subtraction:
    1 iff (b_i - a_i) <= 0 under the signed interpretation, else 0.
  * subleq_route(pred, x_branch, x_next) = elementwise conditional select:
    x_branch[i] where pred[i] is 1, else x_next[i].
  * subleq_reduce(a, b) = routed accumulation: acc starts at 0; for each i,
    d = (b_i - a_i) mod p; if the branch is taken for d, acc = (acc + d) mod p.
    Returns the scalar acc. (The experiment's definition of "reduce via
    subleq-routed accumulation".)
  * attention_pipeline(a, b, c): chains the four SUBLEQ ops —
    subtract -> compare -> route -> reduce — returning every stage plus the
    final scalar. No claim is made that this equals softmax attention.
  * goldilocks_arithmetic: subleq_subtract (field sub, elementwise) and
    subleq_multiply (field mul, elementwise).
"""

from __future__ import annotations

from .goldilocks import P, add, sub, mul, branch_taken

SEG_LEN = 250


def _check_pair(a: list[int], b: list[int]) -> None:
    if len(a) != len(b):
        raise ValueError(f"length mismatch: {len(a)} != {len(b)}")


def ref_sum(v: list[int]) -> int:
    return sum(v) % P


def ref_product(v: list[int]) -> int:
    acc = 1
    for x in v:
        acc = (acc * x) % P
    return acc


def ref_min(v: list[int]) -> int:
    if not v:
        raise ValueError("min of empty vector is undefined")
    return min(v)


def ref_max(v: list[int]) -> int:
    if not v:
        raise ValueError("max of empty vector is undefined")
    return max(v)


def ref_scan(v: list[int]) -> list[int]:
    out: list[int] = []
    acc = 0
    for x in v:
        acc = (acc + x) % P
        out.append(acc)
    return out


def ref_tree_reduction(v: list[int]) -> int:
    """Pairwise tree summation mod p. Must equal ref_sum (tested, not assumed)."""
    level = [x % P for x in v]
    while len(level) > 1:
        nxt: list[int] = []
        it = iter(level)
        for x in it:
            y = next(it, None)
            nxt.append((x + y) % P if y is not None else x)
        level = nxt
    return level[0] if level else 0


def ref_segmented_reduction(v: list[int], seg_len: int = SEG_LEN) -> list[int]:
    return [sum(v[i : i + seg_len]) % P for i in range(0, len(v), seg_len)]


def ref_subleq_subtract(a: list[int], b: list[int]) -> list[int]:
    _check_pair(a, b)
    return [sub(bi, ai) for ai, bi in zip(a, b)]


def ref_subleq_compare(a: list[int], b: list[int]) -> list[int]:
    _check_pair(a, b)
    return [1 if branch_taken(sub(bi, ai)) else 0 for ai, bi in zip(a, b)]


def ref_subleq_route(
    pred: list[int], x_branch: list[int], x_next: list[int]
) -> list[int]:
    if not (len(pred) == len(x_branch) == len(x_next)):
        raise ValueError("length mismatch in subleq_route")
    return [xb if p else xn for p, xb, xn in zip(pred, x_branch, x_next)]


def ref_subleq_reduce(a: list[int], b: list[int]) -> int:
    _check_pair(a, b)
    acc = 0
    for ai, bi in zip(a, b):
        d = sub(bi, ai)
        if branch_taken(d):
            acc = add(acc, d)
    return acc


def ref_attention_pipeline(
    a: list[int], b: list[int], c: list[int]
) -> dict[str, object]:
    """Chain: subtract -> compare -> route -> reduce. Returns every stage."""
    _check_pair(a, b)
    if len(c) != len(a):
        raise ValueError("length mismatch in attention_pipeline")
    diffs = ref_subleq_subtract(a, b)
    preds = ref_subleq_compare(a, b)
    routed = ref_subleq_route(preds, diffs, c)
    out = ref_subleq_reduce(a, b)
    return {
        "subleq_subtract": diffs,
        "subleq_compare": preds,
        "subleq_route": routed,
        "subleq_reduce": out,
    }


def ref_subleq_multiply(a: list[int], b: list[int]) -> list[int]:
    _check_pair(a, b)
    return [mul(ai, bi) for ai, bi in zip(a, b)]
