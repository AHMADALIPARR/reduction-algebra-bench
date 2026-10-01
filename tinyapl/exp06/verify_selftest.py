#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""Verify TinyAPL self-test output against substrate Python oracle."""
import subprocess, sys

sys.path.insert(0, '/home/hatch/workspace/reduction-algebra-bench/substrate')
from splitmix64 import splitmix64_stream

P = 18446744069414584321


def limbs(x):
    return [x & 0xFFFF, (x >> 16) & 0xFFFF, (x >> 32) & 0xFFFF, (x >> 48) & 0xFFFF]


def unlimb(l):
    return l[0] | (l[1] << 16) | (l[2] << 32) | (l[3] << 48)


def main():
    r = subprocess.run(['/tmp/langbuild/tinyapl-bin', '/tmp/langbuild/t_selftest.apl'],
                       capture_output=True, text=True, timeout=300)
    if r.stderr.strip():
        print('RUNTIME ERROR:', r.stderr.strip()[:500])
        sys.exit(1)
    lines = r.stdout.strip().split('\n')
    got = {}
    i = 0
    while i < len(lines):
        if lines[i].startswith('T_'):
            tag = lines[i]
            got[tag] = [int(lines[i + 1 + j]) for j in range(4)]
            i += 5
        else:
            i += 1

    vals = splitmix64_stream(n=8)
    exp = {
        'T_SUM': limbs(sum(vals) % P),
        'T_GFADD2': limbs(sum((2 * v) % P for v in vals) % P),
        'T_GFMULSELF': limbs(sum((v * v) % P for v in vals) % P),
        'T_MIN': limbs(min(vals)),
        'T_MAX': limbs(max(vals)),
        'T_TREEADD': limbs(sum(vals) % P),
        'T_TREEMUL': limbs(__import__('functools').reduce(lambda a, b: (a * b) % P, vals, 1)),
        'T_SHR': [2, 0, 0, 0],
        'T_XOR': [0, 0, 0, 0],
        'T_SUB': limbs(P - 2),      # (p-1)-1
        'T_ADDWRAP': limbs(0),        # ModP((p-1)+1) = ModP(p) = 0
    }
    ok = True
    for tag, want in exp.items():
        have = got.get(tag)
        # normalize: APL may print floats like 42320.0?
        have = [int(v) for v in have] if have else None
        status = 'OK ' if have == want else 'FAIL'
        if have != want:
            ok = False
        print(f'{status} {tag}: got {have} want {want} (int: {unlimb(have) if have else None} vs {unlimb(want)})')
    # checksum gate on stream head
    print('stream head:', vals[0], 'limbs:', limbs(vals[0]))
    print('ALL OK' if ok else 'MISMATCHES FOUND')


if __name__ == '__main__':
    main()
