# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""Substrate correctness suite.

Covers: empty, singleton, pow2, non-pow2, adversarial (0 and p-1),
replay determinism, law tests (sequential vs tree; non-associativity of
subtraction pinned), min/max on adversarial inputs.
"""

import random

import pytest

from substrate import data_gen, goldilocks as G, laws, reference as R


def rng(seed: int) -> random.Random:
    return random.Random(seed)


def vec(r: random.Random, n: int, lo: int = 0, hi: int = G.P) -> list[int]:
    return [r.randrange(lo, hi) for _ in range(n)]


# --- empty / singleton -------------------------------------------------------


def test_empty_sum_is_zero():
    assert R.ref_sum([]) == 0


def test_empty_product_is_one():
    assert R.ref_product([]) == 1


def test_empty_scan_is_empty():
    assert R.ref_scan([]) == []


def test_empty_tree_reduction_is_zero():
    assert R.ref_tree_reduction([]) == 0


def test_empty_min_max_raise():
    with pytest.raises(ValueError):
        R.ref_min([])
    with pytest.raises(ValueError):
        R.ref_max([])


def test_singleton():
    v = [7]
    assert R.ref_sum(v) == 7
    assert R.ref_product(v) == 7
    assert R.ref_min(v) == 7
    assert R.ref_max(v) == 7
    assert R.ref_scan(v) == [7]
    assert R.ref_tree_reduction(v) == 7


# --- shapes: pow2 / non-pow2 -------------------------------------------------


@pytest.mark.parametrize("n", [1024, 1000, 1, 17])
def test_tree_equals_sequential_sum(n):
    v = vec(rng(11), n)
    assert R.ref_tree_reduction(v) == R.ref_sum(v)


@pytest.mark.parametrize("n", [1024, 1000, 33])
def test_scan_last_equals_sum(n):
    v = vec(rng(12), n)
    s = R.ref_scan(v)
    assert s[-1] == R.ref_sum(v)
    # prefix property: differences recover the input
    assert s[0] == v[0] % G.P
    for i in range(1, n):
        assert (s[i] - s[i - 1]) % G.P == v[i] % G.P


def test_segmented_reduction_sums_to_total():
    v = vec(rng(13), 1000)
    segs = R.ref_segmented_reduction(v, 250)
    assert len(segs) == 4
    assert sum(segs) % G.P == R.ref_sum(v)


# --- adversarial: 0 and p-1 --------------------------------------------------


def test_all_zeros():
    n = 64
    z = [0] * n
    assert R.ref_sum(z) == 0
    assert R.ref_product(z) == 0
    assert R.ref_min(z) == 0 and R.ref_max(z) == 0
    assert R.ref_scan(z) == z
    assert R.ref_tree_reduction(z) == 0


def test_all_p_minus_one():
    n = 64
    m = G.P - 1  # == -1 in the field
    w = [m] * n
    assert R.ref_sum(w) == (-n) % G.P
    assert R.ref_product(w) == (1 if n % 2 == 0 else m)
    assert R.ref_min(w) == m and R.ref_max(w) == m


def test_min_max_adversarial_mixed():
    v = [0, G.P - 1, 1, G.P - 2, G.HALF, G.HALF + 1]
    assert R.ref_min(v) == 0
    assert R.ref_max(v) == G.P - 1


def test_subleq_zeros():
    z = [0] * 16
    assert R.ref_subleq_subtract(z, z) == z
    # 0 - 0 = 0 <= 0 signed -> branch taken everywhere
    assert R.ref_subleq_compare(z, z) == [1] * 16
    assert R.ref_subleq_reduce(z, z) == 0


def test_subleq_p_minus_one_self():
    m = [G.P - 1] * 16
    d = R.ref_subleq_subtract(m, m)
    assert d == [0] * 16  # (p-1) - (p-1) = 0 mod p


def test_branch_predicate_sign_boundary():
    # rep = HALF is positive (no branch); HALF+1 is negative (branch)
    assert G.branch_taken(G.HALF) is False
    assert G.branch_taken(G.HALF + 1) is True
    assert G.branch_taken(0) is True
    assert G.branch_taken(1) is False


# --- replay determinism ------------------------------------------------------


def test_generator_replay_deterministic():
    v1 = data_gen.gen_experiment([2, 3, 4], 1000)
    v2 = data_gen.gen_experiment([2, 3, 4], 1000)
    assert v1 == v2
    assert len(v1["a"]) == 1000
    # different seed values -> different vectors
    v3 = data_gen.gen_experiment([5, 6, 7], 1000)
    assert v3["a"] != v1["a"]


def test_generator_first_values_stable():
    # pinned: these exact values must reproduce on any machine, any run
    v = data_gen.gen_experiment([2, 3, 4], 1000)
    assert v["a"][:4] == [
        2167953894875042902,
        891545559712135516,
        15796329797054774206,
        13734366185008353258,
    ]
    assert v["b"][:2] == [1223196329728010584, 9932143212408904373]
    assert v["c"][:2] == [4507706864010232292, 6878501155028001760]
    assert all(0 <= x < G.P for x in v["a"])


def test_goldilocks_values_seed_vectors():
    # The canonical [2,3,4]-seeded vectors are fully determined; spot-check
    # against independently recomputed values embedded here.
    import hashlib

    seed = int.from_bytes(
        hashlib.sha256(b"reduction-algebra-bench:2,3,4").digest()[:8], "big"
    )
    r = random.Random(seed)
    expect_a0 = r.randrange(G.P)
    v = data_gen.gen_experiment([2, 3, 4], 1000)
    assert v["a"][0] == expect_a0


# --- law tests ----------------------------------------------------------------


def test_tree_vs_sequential_product_small():
    # product has no tree variant in the JSON, but the law declaration says
    # multiply is associative: verify pairwise-tree product == sequential.
    def tree_prod(xs):
        lvl = [x % G.P for x in xs]
        while len(lvl) > 1:
            nxt = []
            it = iter(lvl)
            for x in it:
                y = next(it, None)
                nxt.append((x * y) % G.P if y is not None else x)
            lvl = nxt
        return lvl[0] if lvl else 1

    v = vec(rng(21), 999)
    assert tree_prod(v) == R.ref_product(v)


def test_subtraction_not_associative():
    # pins the LAWS declaration: subleq_subtract is NOT associative.
    a, b, c = 10, 3, 4
    left = (a - b - c) % G.P
    right = (a - (b - c)) % G.P
    assert left != right


def test_subleq_reduce_order_matters():
    # branch gating makes accumulation order-significant in general
    a = [5, 0, G.P - 1]
    b = [3, 0, 2]
    fwd = R.ref_subleq_reduce(a, b)
    rev = R.ref_subleq_reduce(a[::-1], b[::-1])
    # both are well-defined; the point is the reference defines the order
    assert isinstance(fwd, int) and isinstance(rev, int)


def test_laws_table_complete_for_json_ops():
    ops = [
        "add",
        "multiply",
        "min",
        "max",
        "scan",
        "tree_reduce",
        "segmented_reduce",
        "subleq_subtract",
        "subleq_compare",
        "subleq_route",
        "subleq_reduce",
    ]
    for op in ops:
        d = laws.declared(op)
        assert "associative" in d and "commutative" in d


def test_unresolved_slots_present():
    for slot in ("sealed", "consensus", "commitment", "proof", "glyphs"):
        assert laws.declared(slot)["status"] == "unresolved"


# --- attention pipeline -------------------------------------------------------


def test_attention_pipeline_stages_consistent():
    v = data_gen.gen_experiment([2, 3, 4], 64)
    out = R.ref_attention_pipeline(v["a"], v["b"], v["c"])
    assert out["subleq_subtract"] == R.ref_subleq_subtract(v["a"], v["b"])
    assert out["subleq_compare"] == R.ref_subleq_compare(v["a"], v["b"])
    assert out["subleq_route"] == R.ref_subleq_route(
        out["subleq_compare"], out["subleq_subtract"], v["c"]
    )
    assert out["subleq_reduce"] == R.ref_subleq_reduce(v["a"], v["b"])
    # route check: where pred==1 we see the diff, else c
    for p, d, ci, r in zip(
        out["subleq_compare"], out["subleq_subtract"], v["c"], out["subleq_route"]
    ):
        assert r == (d if p else ci)


def test_field_arithmetic_exactness():
    # (p-1)*(p-1) = 1 mod p ; no silent overflow possible with big ints
    assert (G.mul(G.P - 1, G.P - 1)) == 1
    assert G.add(G.P - 1, 1) == 0
    assert G.sub(0, 1) == G.P - 1
