#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""Generate TinyAPL exp06 sweep programs (one .apl per n).

Each program: embeds two seeded streams as literals, runs the 11 reduction
ops + attention + gf arithmetic with 3 warmup / 20 timed samples (median in
driver), and prints machine-readable K/S/ESC lines.
"""
import sys
sys.path.insert(0, '/home/hatch/workspace/reduction-algebra-bench/substrate')
from splitmix64 import splitmix64_stream

# import dfn emitter from gen_exp06 without running main()
src = open('/tmp/langbuild/gen_exp06.py').read().replace("\nmain()\n", "\n")
ns = {}
exec(src, ns)

LA = ns['LA']
QO = ns['QO']
V = ns['vec']
D = ns['D']
U = '\u2395'  # ⎕

P = 18446744069414584321


def limbs(x):
    return [x & 0xFFFF, (x >> 16) & 0xFFFF, (x >> 32) & 0xFFFF, (x >> 48) & 0xFFFF]


def avec(arr):
    return V(*[str(x) for x in arr])


def nest(vals):
    ls = [limbs(v) for v in vals]
    return V(avec([l[0] for l in ls]), avec([l[1] for l in ls]),
             avec([l[2] for l in ls]), avec([l[3] for l in ls]))


def emit_esc_scalar(tag, expr):
    """Escape for a scalar field-element result: print tag + 4 limbs."""
    return [
        QO + ' ' + LA + " '" + tag + "'",
        'er ' + LA + ' ' + expr,
        V('e0', 'e1', 'e2', 'e3') + ' ' + LA + ' er',
        QO + ' ' + LA + ' ' + ns['FST'] + ' e0',
        QO + ' ' + LA + ' ' + ns['FST'] + ' e1',
        QO + ' ' + LA + ' ' + ns['FST'] + ' e2',
        QO + ' ' + LA + ' ' + ns['FST'] + ' e3',
    ]


def build(n):
    ns['STMT'] = []
    ns['emit_dfns']()
    ns['emit_scan'](n)
    stmts = ns['STMT']

    k = n.bit_length() - 1
    assert n == 2 ** k

    # two independent streams
    vals_v = splitmix64_stream(n=n)
    vals_w = splitmix64_stream(n=n, seed=0x00BEEFCAFE + 0x9E3779B97F4A7C15)
    # note: splitmix64_stream signature may not take seed; adjust below if needed
    vv = nest(vals_v)
    ww = nest(vals_w)

    stmts.append(QO + ' ' + LA + " 'EXP06_BEGIN'")
    stmts.append(QO + ' ' + LA + " 'N %d'" % n)
    stmts.append('vv ' + LA + ' ' + vv)
    stmts.append('ww ' + LA + ' ' + ww)
    # stream checksum gate (SumModP of vv)
    stmts.extend(emit_esc_scalar('STREAM_CHECK', 'SumModP vv'))

    # kernel definitions: (name, timed_expr, esc_kind, esc_expr)
    # esc_kind: 'scalar' (4 limbs) or 'count' (integer)
    kernels = [
        ('sum', 'SumModP vv', 'scalar', 'SumModP vv'),
        ('product', 'PairGfMul ' + ns['POW'] + ' %d vv' % k, 'scalar',
         'PairGfMul ' + ns['POW'] + ' %d vv' % k),
        ('min', 'Min4 vv', 'scalar', 'Min4 vv'),
        ('max', 'Max4 vv', 'scalar', 'Max4 vv'),
        ('scan', 'Scan%d vv' % n, 'scalar', 'SumModP (Scan%d vv)' % n),
        ('tree_reduction', 'PairGfAdd ' + ns['POW'] + ' %d vv' % k, 'scalar',
         'PairGfAdd ' + ns['POW'] + ' %d vv' % k),
        ('segmented_reduction', '8 SegRed vv', 'scalar', 'SumModP (8 SegRed vv)'),
        ('subleq_subtract', 'ww Sub vv', 'scalar', 'SumModP (ww Sub vv)'),
        ('subleq_compare', 'Cmp dd', 'count', '+/, Cmp dd'),
        ('subleq_route', 'mm Route dd', 'scalar', 'SumModP (mm Route dd)'),
        ('subleq_reduce', 'SumModP rr', 'scalar', 'SumModP rr'),
        ('attention_pipeline', 'ww Attn vv', 'scalar', 'ww Attn vv'),
        ('goldilocks_subtract', 'ww Sub vv', 'scalar', 'SumModP (ww Sub vv)'),
        ('goldilocks_multiply', 'ww GfMul vv', 'scalar', 'SumModP (ww GfMul vv)'),
    ]

    # precompute subleq intermediates (not timed)
    stmts.append('dd ' + LA + ' ww Sub vv')
    stmts.append('mm ' + LA + ' Cmp dd')
    stmts.append('rr ' + LA + ' mm Route dd')

    for name, expr, esc_kind, esc_expr in kernels:
        stmts.append(QO + ' ' + LA + " 'K " + name + "'")
        # 3 warmup (untimed)
        for _ in range(3):
            stmts.append('r ' + LA + ' ' + expr)
        # 20 timed samples (unrolled)
        for _ in range(20):
            stmts.append('t0 ' + LA + ' ' + U + 'unix ' + D +
                         ' r ' + LA + ' ' + expr + D +
                         ' t1 ' + LA + ' ' + U + 'unix ' + D +
                         ' ' + QO + ' ' + LA + ' t1-t0')
        # escape
        if esc_kind == 'scalar':
            stmts.extend(emit_esc_scalar('ESC ' + name, esc_expr))
        else:
            stmts.append(QO + ' ' + LA + " 'ESC " + name + "'")
            stmts.append(QO + ' ' + LA + ' ' + esc_expr)

    stmts.append(QO + ' ' + LA + " 'EXP06_END'")
    return (' ' + D + ' ').join(stmts) + '\n'


if __name__ == '__main__':
    n = int(sys.argv[1])
    # check splitmix64_stream signature for seed support
    import inspect
    sig = inspect.signature(splitmix64_stream)
    if 'seed' not in sig.parameters:
        print('splitmix64_stream does not take seed; using offset stream', file=sys.stderr)
        # fallback: generate 2n and split
        vals = splitmix64_stream(n=2 * n)
        vals_v, vals_w = vals[:n], vals[n:]
        # monkey-patch by regenerating inside build: easier to inline here
        sys.exit(2)
    prog = build(n)
    out = '/tmp/langbuild/sweep_%d.apl' % n
    open(out, 'w', encoding='utf-8').write(prog)
    print('wrote', out, len(prog), 'chars')
