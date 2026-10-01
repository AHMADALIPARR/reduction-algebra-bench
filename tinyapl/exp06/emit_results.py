#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""Emit results/exp06_tinyapl.json from parsed sweep outputs.

Verify-before-record: every kernel escape must match the Python oracle
bit-for-bit AND the n=1024 stream checksum must equal the canonical
1388262917130611548, or the measurement is recorded as null with reason.
"""
import json
import statistics
import sys
sys.path.insert(0, '/tmp/langbuild')
sys.path.insert(0, '/home/hatch/workspace/reduction-algebra-bench/substrate')

from parse_sweep import parse_output, oracle, CANONICAL_CHECKSUM

KERNEL_ORDER = ['sum', 'product', 'min', 'max', 'scan', 'tree_reduction',
                'segmented_reduction', 'subleq_subtract', 'subleq_compare',
                'subleq_route', 'subleq_reduce', 'attention_pipeline',
                'goldilocks_subtract', 'goldilocks_multiply']


def pv(value, provenance):
    return {'value': value, 'provenance': provenance}


def main():
    out = {}
    for n in (128, 1024):
        out[n] = parse_output('/tmp/langbuild/sweep_%d.out' % n)

    # verify-before-record
    ok = True
    reasons = []
    for n in (128, 1024):
        o = out[n]
        exp = oracle(n)
        stream_val = (o['stream_limbs'][0] + o['stream_limbs'][1] * 65536 +
                      o['stream_limbs'][2] * 65536**2 + o['stream_limbs'][3] * 65536**3)
        if stream_val != exp['STREAM_CHECK']:
            ok = False
            reasons.append(f'n={n} stream checksum mismatch')
        if n == 1024 and stream_val != CANONICAL_CHECKSUM:
            ok = False
            reasons.append('n=1024 canonical checksum gate failed')
        for kname in KERNEL_ORDER:
            kd = o['kernels'].get(kname)
            if kd is None or len(kd['samples']) != 20:
                ok = False
                reasons.append(f'n={n} {kname}: missing samples')
                continue
            if kd['esc'] != exp.get(kname):
                ok = False
                reasons.append(f'n={n} {kname}: escape mismatch')

    measurements = []
    for n in (128, 1024):
        o = out[n]
        for kname in KERNEL_ORDER:
            kd = o['kernels'].get(kname, {})
            samples = kd.get('samples', [])
            if ok and len(samples) == 20:
                med = statistics.median(samples)
                measurements.append({
                    'n': pv(n, 'specified'),
                    'kernel': pv(kname, 'specified'),
                    'median_seconds': pv(med, 'measured'),
                    'samples': pv(len(samples), 'measured'),
                    'escape_verified': pv(True, 'derived'),
                })
            else:
                measurements.append({
                    'n': pv(n, 'specified'),
                    'kernel': pv(kname, 'specified'),
                    'median_seconds': pv(None, 'unknown'),
                    'samples': pv(len(samples), 'measured'),
                    'escape_verified': pv(False, 'derived'),
                    'null_reason': pv('; '.join(reasons) if reasons else 'incomplete sweep', 'specified'),
                })

    doc = {
        'schema': pv('reduction-algebra-bench/exp06/1', 'specified'),
        'experiment': pv('exp06_tinyapl', 'specified'),
        'language': {
            'name': pv('TinyAPL', 'specified'),
            'identity': pv('RubenVerg/TinyAPL: a tiny APL dialect interpreter in Haskell (NOT a C interpreter; the brief premise github.com/TinyAPL/TinyAPL 404s)', 'specified'),
            'version': pv('0.12.0.0 (native Linux binary)', 'measured'),
        },
        'prng': {
            'algorithm': pv('SplitMix64', 'specified'),
            'seed': pv('0x00BEEFCAFE', 'specified'),
            'variant': pv('counter-increment (canonical)', 'specified'),
            'crosslang_checksum': pv(CANONICAL_CHECKSUM, 'measured'),
            'stream_embedded_as_literals': pv(
                'SplitMix64 stream generated in Python (substrate) and embedded as APL literals; '
                'the interpreter xor-heavy stream gen is ~27 ms/element and xor is not used by any timed kernel. '
                'The APL MkStream dfn is present and self-test-verified, but not on the timed path.', 'specified'),
        },
        'field': {
            'modulus': pv('18446744069414584321 (2^64 - 2^32 + 1, Goldilocks)', 'specified'),
            'representation': pv('exact 4x16-bit limbs (f64 cannot represent p exactly)', 'specified'),
        },
        'subleq_predicate': pv('taken iff d <= 0 (unsigned reps: rep == 0 or rep > p//2)', 'specified'),
        'timing_protocol': {
            'warmup': pv(3, 'specified'),
            'samples': pv(20, 'specified'),
            'aggregation': pv('median', 'specified'),
            'clock': pv('⎕unix fractional seconds', 'measured'),
            'unrolled': pv('⍺⍺ function operands unsupported; 3+20 calls unrolled by Python codegen', 'specified'),
        },
        'verify_before_record': pv(ok, 'derived'),
        'null_reasons': pv(reasons, 'specified'),
        'measurements': measurements,
    }

    out_path = '/home/hatch/workspace/reduction-algebra-bench/results/exp06_tinyapl.json'
    json.dump(doc, open(out_path, 'w'), indent=2)
    print('wrote', out_path, 'verify_before_record =', ok)
    if not ok:
        print('reasons:', reasons)


if __name__ == '__main__':
    main()
