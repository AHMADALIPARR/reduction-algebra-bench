#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""Verify-before-record driver for the Remora (exp03) track.

Runs the five split Remora programs through remorac (the monolithic
exp03_remora.remora does not typecheck under remorac's fragile whole-program
typechecker; see RUNLOG.md), parses their outputs, and verify-before-record
checks every gate against substrate/:
  * crosslang checksum == 1388262917130611548
  * first 8 stream values bit-for-bit vs substrate/splitmix64.py
  * seq/tree/chunked gates == 1
  * SUBLEQ partition identity, taken count vs Python reference
  * gfMul/gfSub test gates == 1
  * sweep sums at n=128/1024/8192 vs Python reference
Emits results/exp03_remora.json with provenance tags. Never fabricates.
"""
import json
import re
import subprocess
import sys
import os

REPO = os.path.expanduser("~/workspace/reduction-algebra-bench")
EXP03 = os.path.join(REPO, "remora", "exp03")
OUT_JSON = os.path.join(REPO, "results", "exp03_remora.json")
REMORAC = os.path.expanduser("~/workspace/vendor/remorac")
sys.path.insert(0, os.path.join(REPO, "substrate"))
from splitmix64 import splitmix64_stream  # noqa: E402

P = 2**64 - 2**32 + 1
CANON_CHECKSUM = 1388262917130611548


def run_remora(path):
    env = dict(os.environ, PYTHONPATH=REMORAC)
    r = subprocess.run(
        [sys.executable, "-m", "remora.cli", "--target", "interp", path],
        capture_output=True, text=True, env=env, timeout=3600,
        cwd=REMORAC,
    )
    return r


def parse_ints(stdout):
    return [int(x) for x in re.findall(r"-?\d+", stdout)]


def bytes_to_u64(bs):
    return sum(b << (8 * i) for i, b in enumerate(bs))


def main():
    progs = {
        "checksum": os.path.join(EXP03, "exp03a_checksum.remora"),
        "first8": os.path.join(EXP03, "exp03a_first8.remora"),
        "reduce": os.path.join(EXP03, "exp03b_reduce.remora"),
        "subleq": os.path.join(EXP03, "exp03c_subleq.remora"),
        "gfops": os.path.join(EXP03, "exp03d_gfops.remora"),
        "sweep": os.path.join(EXP03, "exp03_sweep.remora"),
    }
    out = {}
    for name, path in progs.items():
        print(f"running {name}...", flush=True)
        r = run_remora(path)
        if r.returncode != 0:
            print(f"REMORA RUN FAILED: {name}")
            print(r.stdout[-2000:])
            print(r.stderr[-2000:])
            sys.exit(1)
        out[name] = parse_ints(r.stdout)
        print(f"  {name}: {len(out[name])} ints", flush=True)

    # --- checksum gate ---
    cksum = bytes_to_u64(out["checksum"][:8])
    oracle_vals = splitmix64_stream(n=8192)
    oracle_cksum = sum(oracle_vals[:1024]) % P

    # --- first8 gate ---
    f8_bytes = out["first8"][:64]
    f8 = [bytes_to_u64(f8_bytes[8*i:8*i+8]) for i in range(8)]
    oracle_f8 = oracle_vals[:8]

    # --- reduce gates ---
    g_seq_tree, g_seq_chunked = out["reduce"][:2]

    # --- subleq gates ---
    g_partition, taken_count = out["subleq"][:2]

    # --- gfops gates ---
    g_gfmul_small, g_gfmul_wrap, g_gfsub_wrap = out["gfops"][:3]

    # --- sweep ---
    sw = out["sweep"]
    sweep_sums = [bytes_to_u64(sw[8*i:8*i+8]) for i in range(3)]
    sweep_ns = [128, 1024, 8192]
    sweep_ref = [sum(oracle_vals[:n]) % P for n in sweep_ns]

    gates = {
        "checksum_match": cksum == CANON_CHECKSUM == oracle_cksum,
        "first8_bit_for_bit": f8 == oracle_f8,
        "seq_tree": g_seq_tree == 1,
        "seq_chunked": g_seq_chunked == 1,
        "partition": g_partition == 1,
        "gfmul_small": g_gfmul_small == 1,
        "gfmul_wrap": g_gfmul_wrap == 1,
        "gfsub_wrap": g_gfsub_wrap == 1,
        "sweep_128": sweep_sums[0] == sweep_ref[0],
        "sweep_1024": sweep_sums[1] == sweep_ref[1],
        "sweep_8192": sweep_sums[2] == sweep_ref[2],
    }
    print("gates:", json.dumps(gates, indent=1))
    print("checksum:", cksum, "expected:", CANON_CHECKSUM)

    # SUBLEQ reference check in Python
    KQV = splitmix64_stream(0x00BEEFCAFE, 192)
    K, Q, V = KQV[0:64], KQV[64:128], KQV[128:192]
    taken_ref = 0
    routed_ref = 0
    for ki, qi, vi in zip(K, Q, V):
        d = (ki - qi) % P
        if d == 0 or d > P // 2:
            taken_ref += 1
            routed_ref = (routed_ref + vi) % P
    totalV_ref = sum(V) % P
    print("taken:", taken_count, "ref:", taken_ref)

    ok = all(gates.values()) and taken_count == taken_ref
    print("VERIFY-BEFORE-RECORD:", "PASS" if ok else "FAIL")
    if not ok:
        sys.exit(2)

    def slot(value, provenance, note=""):
        d = {"value": value, "provenance": provenance}
        if note:
            d["note"] = note
        return d

    result = {
        "schema": slot("reduction-algebra-bench/exp03", "specified"),
        "experiment": slot("exp03_remora", "specified"),
        "kernels": {
            "source": slot("remora/exp03/exp03*.remora (remorac interpreter, costigan/remora)", "specified"),
            "wiring": slot(
                "u64 as 8 LE bytes in i32 cells; SplitMix64 counter-increment variant; "
                "Goldilocks via carry-detecting add + 2^64-p add-back; SUBLEQ predicated "
                "masked select via unary index-map; seq/tree/chunked reductions; "
                "gfMul double-and-add", "specified"),
            "programs": slot(
                ["exp03a_checksum.remora", "exp03a_first8.remora", "exp03b_reduce.remora",
                 "exp03c_subleq.remora", "exp03d_gfops.remora", "exp03_sweep.remora"],
                "specified",
                "monolithic exp03_remora.remora does not typecheck under remorac; "
                "see RUNLOG.md for the typechecker limitations worked around"),
        },
        "prng": {
            "algorithm": slot("SplitMix64 counter-increment", "specified"),
            "seed": slot("0x00BEEFCAFE", "specified"),
            "crosslang_checksum": slot(cksum, "measured"),
            "cross_validated_bit_for_bit": slot(True, "derived",
                "first 8 values match substrate/splitmix64.py exactly; checksum matches 1388262917130611548"),
        },
        "reduction_gates": {
            "seq_tree_equal": slot(bool(g_seq_tree), "measured"),
            "seq_chunked_equal": slot(bool(g_seq_chunked), "measured"),
            "subleq_partition_identity": slot(bool(g_partition), "measured"),
            "subleq_taken_count": slot(taken_count, "measured"),
            "subleq_taken_count_ref": slot(taken_ref, "derived", "Python reference"),
            "gfMul_small": slot(bool(g_gfmul_small), "measured", "200*300==60000"),
            "gfMul_wrap": slot(bool(g_gfmul_wrap), "measured", "(p-1)*2 mod p == p-2"),
            "gfSub_wrap": slot(bool(g_gfsub_wrap), "measured", "(5-8) mod p == p-3"),
        },
        "sweep": {
            n: slot(s, "measured", f"seq-sum mod p at n={n}; ref {r}")
            for n, s, r in zip(sweep_ns, sweep_sums, sweep_ref)
        },
        "timing_protocol": {
            "warmup": slot(3, "specified"),
            "samples": slot(20, "specified"),
            "aggregation": slot("median", "specified"),
            "note": slot(
                "remorac (the available Remora implementation) exposes no wall-clock; "
                "the dialect has no time builtin (verified by grep of the runtime). "
                "All timings null, provenance unknown.", "specified"),
        },
        "timings_ns": {
            "seq_ns": slot(None, "unknown", "no clock in remorac dialect"),
            "tree_ns": slot(None, "unknown", "no clock in remorac dialect"),
            "chunked_ns": slot(None, "unknown", "no clock in remorac dialect"),
            "routed_ns": slot(None, "unknown", "no clock in remorac dialect"),
        },
        "environment": {
            "implementation": slot("remorac (costigan/remora), interp target", "measured"),
            "int_width": slot("i32 only (literals wrap mod 2^32)", "specified",
                              "per remorac docs; u64 emulated in bytes"),
        },
        "caveats": [
            slot("remorac is a Python re-imagining of Remora (ML-syntax), not the Kennedy Haskell implementation; "
                 "int is i32-only, so u64/Goldilocks are emulated byte-wise", "specified"),
            slot("No wall-clock builtin exists in the dialect; timing protocol values are null/unknown, not measured", "specified"),
            slot("iota requires a compile-time constant shape in remorac; stream sizes are fixed per program", "specified"),
            slot("remorac's whole-program typechecker rejects the monolithic program (binary map over "
                 "indexing functions; first-class (==); 9-element array results); the five split programs "
                 "are the executed artifacts", "specified"),
        ],
        "unresolved_slots": [
            slot("timed benchmark medians (no clock)", "unknown"),
            slot("sealed", "unknown"), slot("consensus", "unknown"),
            slot("commitment", "unknown"), slot("proof", "unknown"),
            slot("glyphs", "unknown"), slot("META", "unknown"),
            slot("Omega", "unknown"), slot("resonance", "unknown"),
            slot("worm_seal", "unknown"),
        ],
    }
    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2)
    print("wrote", OUT_JSON)


if __name__ == "__main__":
    main()
