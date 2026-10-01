#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""Generate exp06_tinyapl.apl (TinyAPL, 16-bit-limb exact u64 arithmetic).

All APL source is emitted as ASCII with \\uXXXX escapes, then encoded to
UTF-8, so no editor/terminal glyph mangling can corrupt the program.
Usage:
  gen_exp06.py selftest   -> /tmp/langbuild/t_selftest.apl
  gen_exp06.py full       -> tinyapl/exp06/exp06_tinyapl.apl
"""
import sys

# --- glyph aliases (ASCII source, exact code points) ---
LA = '\u2190'      # assignment
D = '\u22c4'       # statement separator / vector element separator
V0 = '\u27e8'
V1 = '\u27e9'
QO = '\u2395'      # quad output
FST = '\u2283'     # first / disclose
RHO = '\u2374'     # reshape
IOTA = '\u2373'
EACH = '\u00a8'
CAT = '\u236a'     # catenate
DROP = '\u2193'
TAKE = '\u2191'
SQUAD = '\u2337'   # index
FLOOR = '\u230a'
CEIL = '\u2308'
TALLY = '\u2262'     # tally
CF = '\u233f'        # compress (dyadic)
RES = '|'          # residue
NE = '\u2260'
AND = '\u2227'
OR = '\u2228'
NEG = '\u00af'     # high minus
MUL = '\u00d7'
RAV = ','            # ravel
ENC = '\u22a4'       # encode (dyadic)
TR = '\u2349'        # transpose (monadic)
DIV = '\u00f7'
POW = '\u2363'     # power operator
AL = '\u237a'
OM = '\u2375'

P = 18446744069414584321
SEED = 0x00BEEFCAFE
INCR = 0x9E3779B97F4A7C15
M1 = 0xBF58476D1CE4E5B9
M2 = 0x94D049BB133111EB


def limbs(x):
    return [x & 0xFFFF, (x >> 16) & 0xFFFF, (x >> 32) & 0xFFFF, (x >> 48) & 0xFFFF]


def vec(*elts):
    return V0 + (' ' + D + ' ').join(elts) + V1


STMT = []


def s(x):
    STMT.append(x)


def dfn(*parts):
    return '{ ' + (' ' + D + ' ').join(parts) + ' }'


def emit_dfns():
    # PassW: one carry-normalization pass over nested k limbs (any k>=1)
    s('PassW ' + LA + ' ' + dfn(
        'n ' + LA + ' ' + TALLY + ' ' + FST + ' ' + OM,
        'z ' + LA + ' n ' + RHO + ' 0',
        'c ' + LA + ' { ' + FLOOR + ' ' + OM + ' ' + DIV + ' 65536 }' + EACH + ' ' + OM,
        'm ' + LA + ' { 65536 ' + RES + ' ' + OM + ' }' + EACH + ' ' + OM,
        'm + ' + vec('z') + ' ' + CAT + ' ' + NEG + '1 ' + DROP + ' c',
    ))
    # Add: nested k-limb add, mod 2^(16k)
    s('Add ' + LA + ' { PassW ' + POW + ' 6 (' + AL + ' + ' + OM + ') }')
    # Sub: a - b mod 2^(16k) via (65535-b)+1
    s('Sub ' + LA + ' ' + dfn(
        'n ' + LA + ' ' + TALLY + ' ' + FST + ' ' + OM,
        'z ' + LA + ' n ' + RHO + ' 0',
        'nb ' + LA + ' { 65535 - ' + OM + ' }' + EACH + ' ' + OM,
        'one ' + LA + ' ' + vec('n ' + RHO + ' 1') + ' ' + CAT + ' ' + NEG + '1 ' + DROP + ' { z }' + EACH + ' ' + OM,
        AL + ' Add (one Add nb)',
    ))
    # X1: bitwise xor of two n-vectors of 16-bit limbs, via ARITHMETIC bit
    # extraction (APL != is not-equal, not bitwise xor; dyadic encode is too
    # slow in this interpreter). Bits as a 16*n matrix, LSB-first rows.
    s('X1 ' + LA + ' ' + dfn(
        'n ' + LA + ' ' + TALLY + ' ' + AL,
        'p ' + LA + ' 2 * ' + IOTA + ' 16',
        'd ' + LA + ' ' + TR + ' (' + vec('n', '16') + ' ' + RHO + ' p)',
        'ba ' + LA + ' 2 | ' + FLOOR + ' ((' + vec('16', 'n') + ' ' + RHO + ' ' + AL + ') ' + DIV + ' d)',
        'bb ' + LA + ' 2 | ' + FLOOR + ' ((' + vec('16', 'n') + ' ' + RHO + ' ' + OM + ') ' + DIV + ' d)',
        '+/ (p ' + MUL + ' (ba ' + NE + ' bb))',
    ))
    s('Xor ' + LA + ' ' + dfn(
        vec('a0', 'a1', 'a2', 'a3') + ' ' + LA + ' ' + AL,
        vec('b0', 'b1', 'b2', 'b3') + ' ' + LA + ' ' + OM,
        vec('a0 X1 b0', 'a1 X1 b1', 'a2 X1 b2', 'a3 X1 b3'),
    ))
    # Shr: logical right shift of 4-limb value by scalar k (0<=k<64)
    shr = [
        'k ' + LA + ' ' + OM,
        'w ' + LA + ' ' + FLOOR + ' k ' + DIV + ' 16',
        'bb ' + LA + ' 16 ' + RES + ' k',
        'n ' + LA + ' ' + TALLY + ' ' + FST + ' ' + AL,
        'z ' + LA + ' n ' + RHO + ' 0',
        'pad ' + LA + ' ' + vec('z', 'z', 'z', 'z'),
        'arga ' + LA + ' 4 ' + TAKE + ' ((w ' + DROP + ' ' + AL + ') ' + CAT + ' pad)',
        'argb ' + LA + ' 4 ' + TAKE + ' (((w + 1) ' + DROP + ' ' + AL + ') ' + CAT + ' pad)',
        vec('a0', 'a1', 'a2', 'a3') + ' ' + LA + ' arga',
        vec('b0', 'b1', 'b2', 'b3') + ' ' + LA + ' argb',
        'pw ' + LA + ' 2 * bb',
        'qw ' + LA + ' 2 * (16 - bb)',
    ]
    for i in range(4):
        shr.append('r%d ' % i + LA + ' 65536 ' + RES + ' ((' + FLOOR + ' a%d ' % i + DIV +
                   ' pw) + (65536 ' + RES + ' (b%d ' % i + MUL + ' qw)))')
    shr.append(vec('r0', 'r1', 'r2', 'r3'))
    s('Shr ' + LA + ' ' + dfn(*shr))
    # Mul: 4-limb schoolbook multiply, low 4 limbs (mod 2^64)
    s('Mul ' + LA + ' ' + dfn(
        vec('a0', 'a1', 'a2', 'a3') + ' ' + LA + ' ' + AL,
        vec('b0', 'b1', 'b2', 'b3') + ' ' + LA + ' ' + OM,
        'w0 ' + LA + ' a0 ' + MUL + ' b0',
        'w1 ' + LA + ' (a0 ' + MUL + ' b1) + (a1 ' + MUL + ' b0)',
        'w2 ' + LA + ' (a0 ' + MUL + ' b2) + (a1 ' + MUL + ' b1) + (a2 ' + MUL + ' b0)',
        'w3 ' + LA + ' (a0 ' + MUL + ' b3) + (a1 ' + MUL + ' b2) + (a2 ' + MUL + ' b1) + (a3 ' + MUL + ' b0)',
        'PassW ' + POW + ' 6 ' + vec('w0', 'w1', 'w2', 'w3'),
    ))
    # Ge4 / Ge5: lexicographic >= on k limbs, MSB last.
    # result = g[k-1] OR (e[k-1] AND (g[k-2] OR (e[k-2] AND (... (g0 OR e0)))))
    for k in (4, 5):
        parts = [vec(*['a%d' % i for i in range(k)]) + ' ' + LA + ' ' + AL,
                 vec(*['b%d' % i for i in range(k)]) + ' ' + LA + ' ' + OM]
        for i in range(k):
            parts.append('g%d ' % i + LA + ' a%d > b%d' % (i, i))
            parts.append('e%d ' % i + LA + ' a%d = b%d' % (i, i))
        e = '(g0 ' + OR + ' e0)'
        for i in range(1, k):
            e = '(g%d ' % i + OR + ' (e%d ' % i + AND + ' ' + e + '))'
        parts.append(e)
        s('Ge%d ' % k + LA + ' ' + dfn(*parts))
    # ModP: conditional subtract of p; arg is 4 limbs with value < 2p
    s('ModP ' + LA + ' ' + dfn(
        'n ' + LA + ' ' + TALLY + ' ' + FST + ' ' + OM,
        'z ' + LA + ' n ' + RHO + ' 0',
        'p4 ' + LA + ' ' + vec('n ' + RHO + ' 1', 'z', 'n ' + RHO + ' 65535', 'n ' + RHO + ' 65535'),
        'ge ' + LA + ' ' + OM + ' Ge4 p4',
        'mp ' + LA + ' { ge ' + MUL + ' ' + OM + ' }' + EACH + ' p4',
        OM + ' Sub mp',
    ))
    # GfAdd: (a+b) mod p, via 5 limbs then single conditional subtract
    s('GfAdd ' + LA + ' ' + dfn(
        vec('a0', 'a1', 'a2', 'a3') + ' ' + LA + ' ' + AL,
        vec('b0', 'b1', 'b2', 'b3') + ' ' + LA + ' ' + OM,
        'n ' + LA + ' ' + TALLY + ' a0',
        'z ' + LA + ' n ' + RHO + ' 0',
        'a5 ' + LA + ' ' + vec('a0', 'a1', 'a2', 'a3', 'z'),
        'b5 ' + LA + ' ' + vec('b0', 'b1', 'b2', 'b3', 'z'),
        's5 ' + LA + ' a5 Add b5',
        'p5 ' + LA + ' ' + vec('n ' + RHO + ' 1', 'z', 'n ' + RHO + ' 65535', 'n ' + RHO + ' 65535', 'z'),
        'ge ' + LA + ' s5 Ge5 p5',
        'mp ' + LA + ' { ge ' + MUL + ' ' + OM + ' }' + EACH + ' p5',
        'r5 ' + LA + ' s5 Sub mp',
        '4 ' + TAKE + ' r5',
    ))
    # GfMul: (a*b) mod p. 8-limb schoolbook, fold 2^64 -> 2^32-1 twice, final.
    gm = [
        vec('a0', 'a1', 'a2', 'a3') + ' ' + LA + ' ' + AL,
        vec('b0', 'b1', 'b2', 'b3') + ' ' + LA + ' ' + OM,
        'n ' + LA + ' ' + TALLY + ' a0',
        'z ' + LA + ' n ' + RHO + ' 0',
        'w0 ' + LA + ' a0 ' + MUL + ' b0',
        'w1 ' + LA + ' (a0 ' + MUL + ' b1) + (a1 ' + MUL + ' b0)',
        'w2 ' + LA + ' (a0 ' + MUL + ' b2) + (a1 ' + MUL + ' b1) + (a2 ' + MUL + ' b0)',
        'w3 ' + LA + ' (a0 ' + MUL + ' b3) + (a1 ' + MUL + ' b2) + (a2 ' + MUL + ' b1) + (a3 ' + MUL + ' b0)',
        'w4 ' + LA + ' (a1 ' + MUL + ' b3) + (a2 ' + MUL + ' b2) + (a3 ' + MUL + ' b1)',
        'w5 ' + LA + ' (a2 ' + MUL + ' b3) + (a3 ' + MUL + ' b2)',
        'w6 ' + LA + ' a3 ' + MUL + ' b3',
        'ww ' + LA + ' PassW ' + POW + ' 6 ' + vec('w0', 'w1', 'w2', 'w3', 'w4', 'w5', 'w6', 'z'),
        vec('t0', 't1', 't2', 't3', 't4', 't5', 't6', 't7') + ' ' + LA + ' ww',
        # fold 1: V1 = (H<<32 - H) + L ; H = t4..t7, L = t0..t3
        'hsh ' + LA + ' ' + vec('z', 'z', 't4', 't5', 't6', 't7', 'z', 'z'),
        'hh ' + LA + ' ' + vec('t4', 't5', 't6', 't7', 'z', 'z', 'z', 'z'),
        's1 ' + LA + ' hsh Sub hh',
        'l8 ' + LA + ' ' + vec('t0', 't1', 't2', 't3', 'z', 'z', 'z', 'z'),
        'v1 ' + LA + ' s1 Add l8',
        vec('v0', 'v1', 'v2', 'v3', 'v4', 'v5', 'v6', 'v7') + ' ' + LA + ' v1',
        # fold 2: V2 = (H2<<32 - H2) + L2 ; H2 = v4..v7 (< 2^33), L2 = v0..v3
        'h2sh ' + LA + ' ' + vec('z', 'z', 'v4', 'v5', 'v6', 'v7', 'z', 'z'),
        'h2 ' + LA + ' ' + vec('v4', 'v5', 'v6', 'v7', 'z', 'z', 'z', 'z'),
        's2 ' + LA + ' h2sh Sub h2',
        'l28 ' + LA + ' ' + vec('v0', 'v1', 'v2', 'v3', 'z', 'z', 'z', 'z'),
        'v2 ' + LA + ' s2 Add l28',
        vec('u0', 'u1', 'u2', 'u3', 'u4', 'u5', 'u6', 'u7') + ' ' + LA + ' v2',
        # fold 3: V3 = u4*(2^32-1) + (u0..u3) ; u4 < 4 so u4*(2^32-1) < 2^34 exact
        'ft ' + LA + ' u4 ' + MUL + ' 4294967295',
        'f0 ' + LA + ' 65536 ' + RES + ' ft',
        'f1 ' + LA + ' 65536 ' + RES + ' ' + FLOOR + ' ft ' + DIV + ' 65536',
        'f2 ' + LA + ' ' + FLOOR + ' ft ' + DIV + ' 4294967296',
        'x5 ' + LA + ' ' + vec('f0', 'f1', 'f2', 'z', 'z'),
        'l5 ' + LA + ' ' + vec('u0', 'u1', 'u2', 'u3', 'z'),
        'v3 ' + LA + ' l5 Add x5',
        'p5 ' + LA + ' ' + vec('n ' + RHO + ' 1', 'z', 'n ' + RHO + ' 65535', 'n ' + RHO + ' 65535', 'z'),
        'ge ' + LA + ' v3 Ge5 p5',
        'mp ' + LA + ' { ge ' + MUL + ' ' + OM + ' }' + EACH + ' p5',
        'r5 ' + LA + ' v3 Sub mp',
        '4 ' + TAKE + ' r5',
    ]
    s('GfMul ' + LA + ' ' + dfn(*gm))
    # MkStream: first n SplitMix64 field values (counter-increment variant),
    # as nested 4 limbs of n-vectors. idx = 1..n (state advances before mix).
    c1l, m1l, m2l, sel = limbs(INCR), limbs(M1), limbs(M2), limbs(SEED)
    ms = [
        'n ' + LA + ' ' + OM,
        'idx ' + LA + ' 1 + ' + IOTA + ' n',
        'i0 ' + LA + ' 65536 ' + RES + ' idx',
        'i1 ' + LA + ' ' + FLOOR + ' idx ' + DIV + ' 65536',
        'iv ' + LA + ' ' + vec('i0', 'i1', 'n ' + RHO + ' 0', 'n ' + RHO + ' 0'),
        'c1 ' + LA + ' ' + vec(*['n ' + RHO + ' %d' % v for v in c1l]),
        'se ' + LA + ' ' + vec(*['n ' + RHO + ' %d' % v for v in sel]),
        'st ' + LA + ' (iv Mul c1) Add se',
        'm1 ' + LA + ' ' + vec(*['n ' + RHO + ' %d' % v for v in m1l]),
        'm2 ' + LA + ' ' + vec(*['n ' + RHO + ' %d' % v for v in m2l]),
        'zv ' + LA + ' st',
        'zv ' + LA + ' (zv Xor (zv Shr 30)) Mul m1',
        'zv ' + LA + ' (zv Xor (zv Shr 27)) Mul m2',
        'zv ' + LA + ' zv Xor (zv Shr 31)',
        'p4 ' + LA + ' ' + vec('n ' + RHO + ' 1', 'n ' + RHO + ' 0', 'n ' + RHO + ' 65535', 'n ' + RHO + ' 65535'),
        'ge ' + LA + ' zv Ge4 p4',
        'mp ' + LA + ' { ge ' + MUL + ' ' + OM + ' }' + EACH + ' p4',
        'zv Sub mp',
    ]
    s('MkStream ' + LA + ' ' + dfn(*ms))
    # SumModP: sum of n limb-values mod p (fused: raw accumulate, one mod)
    sm = [
        vec('l0', 'l1', 'l2', 'l3') + ' ' + LA + ' ' + OM,
        's0 ' + LA + ' , +/ l0',
        's1 ' + LA + ' , +/ l1',
        's2 ' + LA + ' , +/ l2',
        's3 ' + LA + ' , +/ l3',
        'c0 ' + LA + ' ' + FLOOR + ' s0 ' + DIV + ' 65536',
        'm0 ' + LA + ' 65536 ' + RES + ' s0',
        't1 ' + LA + ' s1 + c0',
        'c1 ' + LA + ' ' + FLOOR + ' t1 ' + DIV + ' 65536',
        'm1 ' + LA + ' 65536 ' + RES + ' t1',
        't2 ' + LA + ' s2 + c1',
        'c2 ' + LA + ' ' + FLOOR + ' t2 ' + DIV + ' 65536',
        'm2 ' + LA + ' 65536 ' + RES + ' t2',
        't3 ' + LA + ' s3 + c2',
        'c3 ' + LA + ' ' + FLOOR + ' t3 ' + DIV + ' 65536',
        'm3 ' + LA + ' 65536 ' + RES + ' t3',
        # S = c3*2^64 + L ; S mod p = (c3*(2^32-1) + L) mod p ; c3 < 2^14
        'x ' + LA + ' c3 ' + MUL + ' 4294967295',
        'q0 ' + LA + ' 4294967296 ' + RES + ' x',
        'q1 ' + LA + ' ' + FLOOR + ' x ' + DIV + ' 4294967296',
        'f0 ' + LA + ' 65536 ' + RES + ' q0',
        'f1 ' + LA + ' ' + FLOOR + ' q0 ' + DIV + ' 65536',
        'f2 ' + LA + ' 65536 ' + RES + ' q1',
        'f3 ' + LA + ' ' + FLOOR + ' q1 ' + DIV + ' 65536',
        'z ' + LA + ' 1 ' + RHO + ' 0',
        'y5 ' + LA + ' ' + vec('m0', 'm1', 'm2', 'm3', 'z') + ' Add ' + vec('f0', 'f1', 'f2', 'f3', 'z'),
        'p5 ' + LA + ' ' + vec('1 ' + RHO + ' 1', '1 ' + RHO + ' 0', '1 ' + RHO + ' 65535', '1 ' + RHO + ' 65535', '1 ' + RHO + ' 0'),
        'ge ' + LA + ' y5 Ge5 p5',
        'mp ' + LA + ' { ge ' + MUL + ' ' + OM + ' }' + EACH + ' p5',
        'r5 ' + LA + ' y5 Sub mp',
        '4 ' + TAKE + ' r5',
    ]
    s('SumModP ' + LA + ' ' + dfn(*sm))
    # Min4/Max4: lexicographic min/max via 4 filter cascades (O(n), tiny const)
    for fname, fop in (('Min4', FLOOR + '/'), ('Max4', CEIL + '/')):
        parts = [vec('l0', 'l1', 'l2', 'l3') + ' ' + LA + ' ' + OM]
        # round on l3 -> keep l2,l1,l0 ; record m3
        parts += [
            'k ' + LA + ' l3 = ' + fop + ' l3',
            'm3 ' + LA + ' ' + FST + ' (k ' + CF + ' l3)',
            'l2 ' + LA + ' k ' + CF + ' l2',
            'l1 ' + LA + ' k ' + CF + ' l1',
            'l0 ' + LA + ' k ' + CF + ' l0',
            'k ' + LA + ' l2 = ' + fop + ' l2',
            'm2 ' + LA + ' ' + FST + ' (k ' + CF + ' l2)',
            'l1 ' + LA + ' k ' + CF + ' l1',
            'l0 ' + LA + ' k ' + CF + ' l0',
            'k ' + LA + ' l1 = ' + fop + ' l1',
            'm1 ' + LA + ' ' + FST + ' (k ' + CF + ' l1)',
            'l0 ' + LA + ' k ' + CF + ' l0',
            'm0 ' + LA + ' ' + fop + ' l0',
            vec(', m0', ', m1', ', m2', ', m3'),
        ]
        s(fname + ' ' + LA + ' ' + dfn(*parts))
    # PairGfAdd: pairwise gf-add of adjacent values (n even -> n/2 values).
    # NOTE: must route through GfAdd (5-limb carry path); a raw PassW+ModP
    # on the 4-limb pairwise sums would drop the bit-64 carry (sums reach 2p-2).
    pgm = [
        vec('l0', 'l1', 'l2', 'l3') + ' ' + LA + ' ' + OM,
        'm ' + LA + ' (' + TALLY + ' l0) ' + DIV + ' 2',
    ]
    for tag, idx in (('A', '0'), ('B', '1')):
        pgm.append(('pa' if tag == 'A' else 'pb') + ' ' + LA + ' ' + vec(
            *[idx + ' ' + SQUAD + ' ' + vec('2', 'm') + ' ' + RHO + ' l%d' % i for i in range(4)]))
    pgm.append('pa GfAdd pb')
    s('PairGfAdd ' + LA + ' ' + dfn(*pgm))
    # PairGfMul: pairwise gf-mul of adjacent values
    pgm = [
        vec('l0', 'l1', 'l2', 'l3') + ' ' + LA + ' ' + OM,
        'm ' + LA + ' (' + TALLY + ' l0) ' + DIV + ' 2',
    ]
    for tag, idx in (('A', '0'), ('B', '1')):
        pgm.append(('pa' if tag=='A' else 'pb') + ' ' + LA + ' ' + vec(
            *[idx + ' ' + SQUAD + ' ' + vec('2', 'm') + ' ' + RHO + ' l%d' % i for i in range(4)]))
    pgm.append('pa GfMul pb')
    s('PairGfMul ' + LA + ' ' + dfn(*pgm))

    # ShrV: shift an n-vector right by s positions, zero-fill (for scan)
    s('ShrV ' + LA + ' ' + dfn(
        's ' + LA + ' ' + AL,
        '(s ' + RHO + ' 0) ' + CAT + ' ((0 - s) ' + DROP + ' ' + OM + ')',
    ))
    # Cmp: SUBLEQ compare; taken iff d==0 or d >= (p+1)/2 (SPECIFIED d<=0).
    # Returns 0/1 mask (n-vector).
    s('Cmp ' + LA + ' ' + dfn(
        vec('l0', 'l1', 'l2', 'l3') + ' ' + LA + ' ' + OM,
        'n ' + LA + ' ' + TALLY + ' l0',
        'h ' + LA + ' ' + vec('n ' + RHO + ' 1', 'n ' + RHO + ' 32768',
                             'n ' + RHO + ' 65535', 'n ' + RHO + ' 32767'),
        'nz ' + LA + ' (l0 ' + NE + ' 0) ' + OR + ' (l1 ' + NE + ' 0) ' + OR
        + ' (l2 ' + NE + ' 0) ' + OR + ' (l3 ' + NE + ' 0)',
        '(~ nz) ' + OR + ' (' + OM + ' Ge4 h)',
    ))
    # Route: compress nested 4-vector by 0/1 mask (SUBLEQ route)
    s('Route ' + LA + ' ' + dfn(
        'm ' + LA + ' ' + AL,
        vec('l0', 'l1', 'l2', 'l3') + ' ' + LA + ' ' + OM,
        vec('m ' + CF + ' l0', 'm ' + CF + ' l1', 'm ' + CF + ' l2', 'm ' + CF + ' l3'),
    ))
    # SegRed: segmented reduction; k segments (k = left arg), returns k
    # field elements as nested 4 of k-vectors.
    s('SegRed ' + LA + ' ' + dfn(
        'k ' + LA + ' ' + AL,
        vec('l0', 'l1', 'l2', 'l3') + ' ' + LA + ' ' + OM,
        'm ' + LA + ' (' + TALLY + ' l0) ' + DIV + ' k',
        's0 ' + LA + ' +/ ' + TR + ' (' + vec('k', 'm') + ' ' + RHO + ' l0)',
        's1 ' + LA + ' +/ ' + TR + ' (' + vec('k', 'm') + ' ' + RHO + ' l1)',
        's2 ' + LA + ' +/ ' + TR + ' (' + vec('k', 'm') + ' ' + RHO + ' l2)',
        's3 ' + LA + ' +/ ' + TR + ' (' + vec('k', 'm') + ' ' + RHO + ' l3)',
        # mod-p fold on k-vectors (SumModP tail with z = k⍴0)
        'c0 ' + LA + ' ' + FLOOR + ' s0 ' + DIV + ' 65536',
        'q0 ' + LA + ' 65536 | '+ 's0',
        't1 ' + LA + ' s1 + c0',
        'c1 ' + LA + ' ' + FLOOR + ' t1 ' + DIV + ' 65536',
        'q1 ' + LA + ' 65536 | '+ 't1',
        't2 ' + LA + ' s2 + c1',
        'c2 ' + LA + ' ' + FLOOR + ' t2 ' + DIV + ' 65536',
        'q2 ' + LA + ' 65536 | '+ 't2',
        't3 ' + LA + ' s3 + c2',
        'c3 ' + LA + ' ' + FLOOR + ' t3 ' + DIV + ' 65536',
        'q3 ' + LA + ' 65536 | '+ 't3',
        'x ' + LA + ' c3 ' + MUL + ' 4294967295',
        'r0 ' + LA + ' 4294967296 | '+ 'x',
        'r1 ' + LA + ' ' + FLOOR + ' x ' + DIV + ' 4294967296',
        'f0 ' + LA + ' 65536 | '+ 'r0',
        'f1 ' + LA + ' ' + FLOOR + ' r0 ' + DIV + ' 65536',
        'f2 ' + LA + ' 65536 | '+ 'r1',
        'f3 ' + LA + ' ' + FLOOR + ' r1 ' + DIV + ' 65536',
        'z ' + LA + ' k ' + RHO + ' 0',
        'y5 ' + LA + ' ' + vec('q0', 'q1', 'q2', 'q3', 'z') + ' Add ' + vec('f0', 'f1', 'f2', 'f3', 'z'),
        'p5 ' + LA + ' ' + vec('k ' + RHO + ' 1', 'z', 'k ' + RHO + ' 65535', 'k ' + RHO + ' 65535', 'z'),
        'ge ' + LA + ' y5 Ge5 p5',
        'mp ' + LA + ' { ge ' + MUL + ' ' + OM + ' }' + EACH + ' p5',
        'r5 ' + LA + ' y5 Sub mp',
        '4 ' + TAKE + ' r5',
    ))
    # Attn: SUBLEQ attention pipeline (subtract -> compare -> route -> reduce)
    s('Attn ' + LA + ' ' + dfn(
        vec('a0', 'a1', 'a2', 'a3') + ' ' + LA + ' ' + AL,
        vec('b0', 'b1', 'b2', 'b3') + ' ' + LA + ' ' + OM,
        'd ' + LA + ' ' + vec('a0', 'a1', 'a2', 'a3') + ' Sub ' + vec('b0', 'b1', 'b2', 'b3'),
        'm ' + LA + ' Cmp d',
        'r ' + LA + ' m Route d',
        'SumModP r',
    ))


def emit_scan(n):
    """Unrolled parallel-prefix scan (mod p) for n = 2^k. Defines ScanN."""
    k = n.bit_length() - 1
    assert n == 2 ** k
    parts = [vec('l0', 'l1', 'l2', 'l3') + ' ' + LA + ' ' + OM]
    for r in range(k):
        sh = 2 ** r
        parts.append('a ' + LA + ' ' + vec(*['%d ShrV l%d' % (sh, i) for i in range(4)]))
        parts.append(vec('l0', 'l1', 'l2', 'l3') + ' ' + LA + ' '
                     + vec('l0', 'l1', 'l2', 'l3') + ' GfAdd a')
    s('Scan%d' % n + ' ' + LA + ' ' + dfn(*parts))


def plimb(tag, rhs):
    """rhs is an expression: emit rr <- rhs, then print tag + 4 limb scalars."""
    s(QO + ' ' + LA + ' ' + "'" + tag + "'")
    s('rr ' + LA + ' ' + rhs)
    s(vec('e0', 'e1', 'e2', 'e3') + ' ' + LA + ' rr')
    for i in range(4):
        s(QO + ' ' + LA + ' ' + FST + ' e%d' % i)


def emit_selftest():
    emit_dfns()
    s('vv ' + LA + ' MkStream 8')
    plimb('T_SUM', 'SumModP vv')
    plimb('T_GFADD2', 'SumModP (vv GfAdd vv)')
    plimb('T_GFMULSELF', 'SumModP (vv GfMul vv)')
    plimb('T_MIN', 'Min4 vv')
    plimb('T_MAX', 'Max4 vv')
    plimb('T_TREEADD', 'PairGfAdd ' + POW + ' 3 vv')
    plimb('T_TREEMUL', 'PairGfMul ' + POW + ' 3 vv')
    s('xx ' + LA + ' ' + vec(', 5', ', 0', ', 0', ', 0'))
    plimb('T_SHR', 'xx Shr 1')
    plimb('T_XOR', 'xx Xor xx')
    s('pm1 ' + LA + ' ' + vec(', 0', ', 0', ', 65535', ', 65535'))
    s('one ' + LA + ' ' + vec(', 1', ', 0', ', 0', ', 0'))
    plimb('T_SUB', 'pm1 Sub one')          # (p-1)-1 = p-2
    plimb('T_ADDWRAP', 'ModP (pm1 Add one)')  # (p-1)+1 = p -> 0


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'selftest'
    global STMT
    STMT = []
    if mode == 'selftest':
        emit_selftest()
        open('/tmp/langbuild/t_selftest.apl', 'w', encoding='utf-8').write(
            (' ' + D + ' ').join(STMT) + '\n')
    else:
        emit_dfns()
        open('/home/hatch/workspace/reduction-algebra-bench/tinyapl/exp06/exp06_tinyapl.apl',
             'w', encoding='utf-8').write((' ' + D + ' ').join(STMT) + '\n')
    print('wrote %s, %d stmts' % (mode, len(STMT)))


main()
