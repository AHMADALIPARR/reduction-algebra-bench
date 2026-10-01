#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""Experiment 01 orchestrator: Chapel vertical slice.

Pipeline:
  1. Generate deterministic vectors (substrate/data_gen) -> chapel/exp01/vectors/
  2. Build the Chapel program (chpl --fast). If chpl is missing or the
     build fails, emit null measurements (provenance unknown) — never fabricate.
  3. Run it, parse `value`/`timing` lines.
  4. Validate EVERY value against the scalar reference. Any mismatch
     invalidates that op's timing (timing -> null, provenance unknown).
  5. Emit results/exp01_chapel.json (canonical JSON, provenance-tagged).

Usage: python3 chapel/exp01/run_exp01.py  (run from repo root)
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from substrate import data_gen, emit, reference as R  # noqa: E402

EXP_DIR = os.path.join(ROOT, "chapel", "exp01")
VEC_DIR = os.path.join(EXP_DIR, "vectors")
RESULTS = os.path.join(ROOT, "results", "exp01_chapel.json")

# name in Chapel output -> (reference function, timing key)
OPS = {
    "sum": (lambda v: R.ref_sum(v["a"]), "sum"),
    "product": (lambda v: R.ref_product(v["a"]), "product"),
    "min": (lambda v: R.ref_min(v["a"]), "min"),
    "max": (lambda v: R.ref_max(v["a"]), "max"),
    "scan": (lambda v: R.ref_scan(v["a"]), "scan"),
    "tree_reduction": (lambda v: R.ref_tree_reduction(v["a"]), "tree_reduction"),
    "segmented_reduction": (
        lambda v: R.ref_segmented_reduction(v["a"]),
        "segmented_reduction",
    ),
    "subleq_subtract": (
        lambda v: R.ref_subleq_subtract(v["a"], v["b"]),
        "subleq_subtract",
    ),
    "subleq_compare": (
        lambda v: R.ref_subleq_compare(v["a"], v["b"]),
        "subleq_compare",
    ),
    "subleq_route": (
        lambda v: R.ref_subleq_route(
            R.ref_subleq_compare(v["a"], v["b"]),
            R.ref_subleq_subtract(v["a"], v["b"]),
            v["c"],
        ),
        "subleq_route",
    ),
    "subleq_reduce": (
        lambda v: R.ref_subleq_reduce(v["a"], v["b"]),
        "subleq_reduce",
    ),
    "attention_subleq_reduce": (
        lambda v: R.ref_attention_pipeline(v["a"], v["b"], v["c"])["subleq_reduce"],
        None,  # pipeline value; no separate timing
    ),
    "arith_subleq_subtract": (
        lambda v: R.ref_subleq_subtract(v["a"], v["b"]),
        "arith_subleq_subtract",
    ),
    "arith_subleq_multiply": (
        lambda v: R.ref_subleq_multiply(v["a"], v["b"]),
        "arith_subleq_multiply",
    ),
}

UNRESOLVED_SLOTS = [
    "sealed",
    "consensus",
    "commitment",
    "proof",
    "glyphs",
    "META",
    "Omega",
    "resonance",
    "worm_seal",
]


def sha256_of_vec(vec: list[int]) -> str:
    return hashlib.sha256(",".join(str(x) for x in vec).encode()).hexdigest()


def null_op(reason: str) -> dict:
    return {
        "value": emit.measurement(None, emit.UNKNOWN),
        "time_s": emit.measurement(None, emit.UNKNOWN),
        "validated": False,
        "note": reason,
    }


def main() -> int:
    vecs = data_gen.gen_experiment([2, 3, 4], 1000)
    data_gen.write_vectors(vecs, VEC_DIR)

    vec_info = {
        name: emit.measurement(sha256_of_vec(v), emit.DERIVED)
        for name, v in vecs.items()
    }

    ops_out: dict[str, dict] = {}
    env: dict[str, dict] = {
        "machine": emit.measurement("single", emit.SPECIFIED),
        "locale": emit.measurement("single-locale", emit.SPECIFIED),
    }

    chpl = shutil.which("chpl")
    binary = os.path.join(EXP_DIR, "exp01")
    if chpl is None:
        env["chpl_version"] = emit.measurement(None, emit.UNKNOWN)
        for name in OPS:
            ops_out[name] = null_op("chpl not installed on this machine")
    else:
        ver = subprocess.run(
            [chpl, "--version"], capture_output=True, text=True
        ).stdout.splitlines()
        env["chpl_version"] = emit.measurement(
            ver[0].strip() if ver else "unknown", emit.MEASURED
        )
        build = subprocess.run(
            [
                chpl,
                "--fast",
                os.path.join(EXP_DIR, "exp01.chpl"),
                os.path.join(EXP_DIR, "goldilocks_kernels.chpl"),
                "-o",
                binary,
            ],
            capture_output=True,
            text=True,
        )
        if build.returncode != 0:
            for name in OPS:
                ops_out[name] = null_op(f"chpl build failed: {build.stderr[:200]}")
        else:
            run = subprocess.run(
                [binary, "--vecdir=" + VEC_DIR],
                capture_output=True,
                text=True,
                timeout=600,
            )
            values: dict[str, list[str]] = {}
            timings: dict[str, float] = {}
            for line in run.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 3 and parts[0] == "value":
                    values[parts[1]] = parts[2:]
                elif len(parts) == 3 and parts[0] == "timing":
                    try:
                        timings[parts[1]] = float(parts[2])
                    except ValueError:
                        pass
            for name, (ref_fn, timing_key) in OPS.items():
                if name not in values:
                    ops_out[name] = null_op("no value line from Chapel binary")
                    continue
                expected = ref_fn(vecs)
                exp_list = (
                    expected if isinstance(expected, list) else [expected]
                )
                got = [int(x) for x in values[name]]
                if got == exp_list:
                    entry: dict = {
                        "value": emit.measurement(
                            [emit.felt(x) for x in got]
                            if isinstance(expected, list)
                            else emit.felt(got[0]),
                            emit.MEASURED,
                        ),
                        "validated": True,
                    }
                    if timing_key and timing_key in timings:
                        entry["time_s"] = emit.measurement(
                            timings[timing_key], emit.MEASURED
                        )
                    else:
                        entry["time_s"] = emit.measurement(None, emit.UNKNOWN)
                    ops_out[name] = entry
                else:
                    ops_out[name] = {
                        "value": emit.measurement(None, emit.UNKNOWN),
                        "time_s": emit.measurement(None, emit.UNKNOWN),
                        "validated": False,
                        "note": "MISMATCH vs scalar reference — timing invalidated",
                    }
            for name in OPS:
                if name not in ops_out:
                    ops_out[name] = null_op("missing from Chapel output")

    payload = {
        "schema": emit.SCHEMA_VERSION,
        "experiment": emit.measurement("chapel-01", emit.SPECIFIED),
        "config": emit.measurement(
            "spec/chapel_experiment_01.json", emit.SPECIFIED
        ),
        "environment": env,
        "vectors": {
            "seed_values": emit.measurement([2, 3, 4], emit.SPECIFIED),
            "n": emit.measurement(1000, emit.SPECIFIED),
            "sha256": vec_info,
        },
        "kernels": {
            "gfAdd": emit.measurement(
                "parent-supplied carry-free (verified 0 errors / 80k pairs); "
                "replaces author variants 1+2 pending author fix",
                emit.DERIVED,
            ),
            "gfSub": emit.measurement(
                "author variant 1, verbatim (verified 0 errors / 80k pairs); "
                "gfSub(x,y) = (x-y) mod p",
                emit.DERIVED,
            ),
            "gfMul": emit.measurement(
                "double-and-add via gfAdd (verified 0 errors / 80k pairs); "
                "variant 1's uint(128) form does not compile on Chapel 2.10",
                emit.DERIVED,
            ),
            "branch": emit.measurement(
                "taken iff rep == 0 or rep > p//2 (signed <= 0)",
                emit.SPECIFIED,
            ),
        },
        "ops": ops_out,
        "unresolved_slots": {
            slot: emit.measurement(None, emit.UNKNOWN) for slot in UNRESOLVED_SLOTS
        },
    }
    os.makedirs(os.path.dirname(RESULTS), exist_ok=True)
    emit.emit(RESULTS, payload)

    n_ok = sum(1 for o in ops_out.values() if o.get("validated"))
    n_timed = sum(
        1
        for o in ops_out.values()
        if o.get("time_s", {}).get("provenance") == emit.MEASURED
    )
    print(f"validated: {n_ok}/{len(ops_out)} ops, timed: {n_timed}")
    print(f"wrote {RESULTS}")
    mism = [k for k, o in ops_out.items() if o.get("note", "").startswith("MISMATCH")]
    if mism:
        print("MISMATCHES:", mism)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
