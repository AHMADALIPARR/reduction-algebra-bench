#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""Parse TinyAPL exp06 sweep output, verify escapes vs oracle, emit results JSON."""
import json
import statistics
import sys
sys.path.insert(0, '/home/hatch/workspace/reduction-algebra-bench/substrate')
from splitmix64 import splitmix64_stream

P = 18446744069414584321
M64 = 2 ** 64
CANONICAL_CHECKSUM = 1388262917130611548


def gf_add(a, b):
    return (a + b) % P


def gf_mul(a, b):
    return (a * b) % P


def gf_sub(a, b):
    return (a - b) % M64  # raw 64-bit (Sub is mod 2^64, not mod p)


def oracle(n):
    """Expected escape values for each kernel."""
    vv = splitmix64_stream(n=n)
    ww = splitmix64_stream(n=n, seed=0x00BEEFCAFE + 0x9E3779B97F4A7C15)
    k = n.bit_length() - 1
    # tree helpers (pairwise, sequential within level = same as parallel)
    def tree_add(v):
        v = list(v)
        while len(v) > 1:
            v = [gf_add(v[i], v[i + 1]) for i in range(0, len(v), 2)]
        return v[0]
    def tree_mul(v):
        v = list(v)
        while len(v) > 1:
            v = [gf_mul(v[i], v[i + 1]) for i in range(0, len(v), 2)]
        return v[0]
    # scan (prefix sums mod p)
    scan = []
    acc = 0
    for x in vv:
        acc = gf_add(acc, x)
        scan.append(acc)
    # segmented (8 segments)
    m = n // 8
    segs = [sum(vv[i * m:(i + 1) * m]) % P for i in range(8)]
    # subleq
    d = [gf_sub(b, a) for a, b in zip(vv, ww)]  # ww - vv
    half = (P + 1) // 2
    mask = [1 if (x == 0 or x >= half) else 0 for x in d]
    routed = [x for x, mm in zip(d, mask) if mm]
    return {
        'STREAM_CHECK': sum(vv) % P,
        'sum': sum(vv) % P,
        'product': tree_mul(vv),
        'min': min(vv),
        'max': max(vv),
        'scan': sum(scan) % P,
        'tree_reduction': tree_add(vv),
        'segmented_reduction': sum(segs) % P,
        'subleq_subtract': sum(d) % P,
        'subleq_compare': sum(mask),
        'subleq_route': sum(routed) % P,
        'subleq_reduce': sum(routed) % P,
        'attention_pipeline': sum(routed) % P,
        'goldilocks_subtract': sum(d) % P,
        'goldilocks_multiply': sum(gf_mul(a, b) for a, b in zip(vv, ww)) % P,
    }


def parse_float(s):
    """Parse TinyAPL float output, handling ⏨ scientific notation."""
    s = s.replace('\u23e8', 'e').replace('\u00af', '-').replace('\u2212', '-')
    return float(s)


def parse_output(path):
    """Parse sweep .out into {n, stream_limbs, kernels: {name: {samples, esc}}}."""
    lines = [l.strip() for l in open(path, encoding='utf-8') if l.strip()]
    n = None
    stream_limbs = None
    kernels = {}
    cur = None
    i = 0
    while i < len(lines):
        l = lines[i]
        if l == 'EXP06_BEGIN':
            i += 1
            continue
        if l.startswith('N '):
            n = int(l.split()[1])
        elif l == 'STREAM_CHECK':
            stream_limbs = [int(lines[i + 1 + j]) for j in range(4)]
            i += 4
        elif l.startswith('K '):
            cur = l[2:]
            kernels[cur] = {'samples': [], 'esc': None}
        elif l.startswith('S ') or (cur and kernels[cur]['esc'] is None and
                                     len(kernels[cur]['samples']) < 20):
            # sample line: bare float (we emit via ⎕ ← t1-t0)
            try:
                v = parse_float(l[2:] if l.startswith('S ') else l)
                kernels[cur]['samples'].append(v)
                i += 1
                continue
            except ValueError:
                pass
        elif l.startswith('ESC '):
            name = l[4:]
            # next lines: 4 limbs (scalar) or 1 integer (count)
            # peek: subleq_compare is the only count
            if name == 'subleq_compare':
                kernels[name]['esc'] = int(lines[i + 1])
                i += 1
            else:
                limbs = [int(lines[i + 1 + j]) for j in range(4)]
                kernels[name]['esc'] = limbs[0] + limbs[1] * 65536 + limbs[2] * 65536**2 + limbs[3] * 65536**3
                i += 4
        i += 1
    return {'n': n, 'stream_limbs': stream_limbs, 'kernels': kernels}


def main():
    out128 = parse_output('/tmp/langbuild/sweep_128.out')
    out1024 = parse_output('/tmp/langbuild/sweep_1024.out')
    results = {'n128': out128, 'n1024': out1024}
    # verify
    for tag, out in [('128', out128), ('1024', out1024)]:
        n = out['n']
        exp = oracle(n)
        stream_val = (out['stream_limbs'][0] + out['stream_limbs'][1] * 65536 +
                      out['stream_limbs'][2] * 65536**2 + out['stream_limbs'][3] * 65536**3)
        print(f"n={tag} stream: got {stream_val}, expected {exp['STREAM_CHECK']}, match={stream_val == exp['STREAM_CHECK']}")
        if n == 1024:
            print(f"  canonical checksum match: {stream_val == CANONICAL_CHECKSUM}")
        for kname, kd in out['kernels'].items():
            e = exp.get(kname)
            ok = (kd['esc'] == e) if e is not None else None
            med = statistics.median(kd['samples']) if len(kd['samples']) == 20 else None
            print(f"  {kname}: samples={len(kd['samples'])} median={med} esc_match={ok}")
    json.dump(results, open('/tmp/langbuild/sweep_parsed.json', 'w'), indent=2)
    print('wrote sweep_parsed.json')


if __name__ == '__main__':
    main()
