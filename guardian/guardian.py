#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""Guardian process — ERE P1-P5 gate over agent-produced code.

For each deliverable the guardian runs the author's REAL Enochian
Reconstruction Engine gates (harness/gates.py from
snapkittywest/sovereign-chat-harness, local clone at
~/workspace/_ere_harness) over the (task prompt, produced code) pair:

  P1 verify(prompt)    prompt-coherence MetaSum check
  P2 verify(response)  response MetaSum check (+ Dream Cycle recovery)
  P3 curate            joint check, flags dream recovery
  P4 prove             joint entropy <= 0.20
  P5 seal              WORM SHA-256 receipt

Every verdict is appended to results/ere_guardian_log.jsonl (append-only).
A deliverable is committed only when verdict.allowed is True.

What the gates are: deterministic text -> SHA-256-seeded weight vector ->
MetaSum magnitude / entropy metrics. They judge textual coherence per the
author's specification; they do not execute code or prove semantic
correctness. Independent verification (review, compile/run attempts,
verify-before-record) runs alongside and is recorded separately.

Usage:
  guardian.py --agent NAME --prompt PROMPT.txt --code DIR --label LABEL
Exit: 0 = ALLOWED (sealed), 2 = BLOCKED.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.expanduser("~/workspace/_ere_harness"))
from harness.gates import verify  # noqa: E402  (author's real gates)

BENCH = os.path.expanduser("~/workspace/reduction-algebra-bench")
LOG = os.path.join(BENCH, "results", "ere_guardian_log.jsonl")

SKIP_DIRS = {"__pycache__", ".git", "node_modules", "target"}
SKIP_EXT = {".pyc", ".o", ".so"}


def read_code_tree(root: str) -> str:
    parts: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(filenames):
            if os.path.splitext(fn)[1] in SKIP_EXT:
                continue
            fp = os.path.join(dirpath, fn)
            rel = os.path.relpath(fp, root)
            try:
                with open(fp, "r", errors="replace") as f:
                    body = f.read()
            except OSError:
                continue
            parts.append(f"===== {rel} =====\n{body}")
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True)
    ap.add_argument("--prompt", required=True, help="task brief text file")
    ap.add_argument("--code", required=True, help="deliverable directory")
    ap.add_argument("--label", required=True)
    args = ap.parse_args()

    with open(args.prompt) as f:
        prompt = f.read()
    response = read_code_tree(args.code)
    if not response.strip():
        print("GUARDIAN: empty deliverable — BLOCKED")
        return 2

    verdict = verify(prompt, response)
    d = verdict.to_dict()

    entry = {
        "ts": time.time(),
        "agent": args.agent,
        "label": args.label,
        "code_sha256": hashlib.sha256(response.encode()).hexdigest(),
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "allowed": d["allowed"],
        "proof": d["proof"],
        "dream_cycles": d["dream_cycles"],
        "worm_seal": d["worm_seal"],
        "gates": d["gates"],
    }
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    print(f"GUARDIAN [{args.label}] by {args.agent}: "
          f"{'ALLOWED' if d['allowed'] else 'BLOCKED'} "
          f"(proof={d['proof']}, dreams={d['dream_cycles']}, seal={d['worm_seal'][:16]}...)")
    for g in d["gates"]:
        print(f"  {g['gate']} {g['label']:>7} passed={str(g['passed']):>5} "
              f"entropy={g['entropy']:.4f} :: {g['detail'][:80]}")
    return 0 if d["allowed"] else 2


if __name__ == "__main__":
    sys.exit(main())
