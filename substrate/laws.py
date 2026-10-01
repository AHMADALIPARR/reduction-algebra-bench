# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""LAWS table: per-operator associativity/commutativity declarations.

Declared here, TESTED in tests/test_substrate.py — never assumed.
Sequential-vs-tree equivalence is an empirical claim checked against the
scalar reference, which matters for float domains and for any
sealed/consensus slots (which may be non-associative).

Unresolved operator slots (sealed, consensus, commitment, proof, and the
six glyphs / META / Omega / resonance / WORM sealing) are listed with
status "unresolved": the benchmark harness treats them as parameterized
slots and does not infer their semantics.
"""

from __future__ import annotations

LAWS: dict[str, dict[str, object]] = {
    "add": {
        "associative": True,
        "commutative": True,
        "identity": "0",
        "notes": "field addition mod p; tree/sequential equivalence tested",
    },
    "multiply": {
        "associative": True,
        "commutative": True,
        "identity": "1",
        "notes": "field multiplication mod p; tree/sequential equivalence tested",
    },
    "min": {
        "associative": True,
        "commutative": True,
        "identity": None,
        "notes": "over canonical reps; no identity (empty raises)",
    },
    "max": {
        "associative": True,
        "commutative": True,
        "identity": None,
        "notes": "over canonical reps; no identity (empty raises)",
    },
    "scan": {
        "associative": "n/a (prefix, order-fixed)",
        "commutative": False,
        "identity": "0 (prefix seed)",
        "notes": "prefix sums; order is part of the definition",
    },
    "tree_reduce": {
        "associative": "declared-add",
        "commutative": True,
        "identity": "0",
        "notes": "pairwise tree summation; equality with sequential sum TESTED",
    },
    "segmented_reduce": {
        "associative": True,
        "commutative": "within-segment",
        "identity": "0",
        "notes": "per-segment sums; segment boundaries are part of the spec",
    },
    "subleq_subtract": {
        "associative": False,
        "commutative": False,
        "identity": None,
        "notes": "subtraction is neither; non-associativity pinned by test",
    },
    "subleq_compare": {
        "associative": "n/a (predicate, not a reduction)",
        "commutative": False,
        "identity": None,
        "notes": "branch predicate per element; order follows the vectors",
    },
    "subleq_route": {
        "associative": "n/a (selection, not a reduction)",
        "commutative": False,
        "identity": None,
        "notes": "conditional select; semantics fixed by reference",
    },
    "subleq_reduce": {
        "associative": False,
        "commutative": False,
        "identity": "0 (accumulator seed)",
        "notes": "routed accumulation; branch gating makes order significant",
    },
    # --- unresolved slots: parameterized, semantics NOT inferred ---
    "sealed": {"status": "unresolved", "notes": "operator slot; no semantics assumed"},
    "consensus": {"status": "unresolved", "notes": "operator slot; no semantics assumed"},
    "commitment": {"status": "unresolved", "notes": "operator slot; no semantics assumed"},
    "proof": {"status": "unresolved", "notes": "operator slot; no semantics assumed"},
    "glyphs": {"status": "unresolved", "notes": "six glyphs; computation not inferred"},
    "META": {"status": "unresolved", "notes": "compressed form; not inferred"},
    "Omega": {"status": "unresolved", "notes": "composition; not inferred"},
    "resonance": {"status": "unresolved", "notes": "measure; not inferred"},
    "worm_seal": {"status": "unresolved", "notes": "sealing; not inferred"},
}


def declared(op: str) -> dict[str, object]:
    if op not in LAWS:
        raise KeyError(f"no law declaration for operator {op!r}")
    return LAWS[op]
