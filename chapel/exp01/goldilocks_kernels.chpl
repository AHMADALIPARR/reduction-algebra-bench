// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 SnapKitty Collective
/* Goldilocks field kernels for the Reduction Algebra / SUBLEQ Attention
   Benchmark — the VERIFIED set wired into Experiment 01.

   STATUS (verified 2026-10-01 against the exact Python scalar reference,
   substrate/goldilocks.py, over ~80k adversarial+random canonical pairs,
   0 errors each):

   - gfAdd: carry-free form supplied by the parent agent after both
     author variants failed verification. Replaces
     user_kernels_variant1.chpl and user_kernels_variant2.chpl PENDING
     THE AUTHOR'S FIX — the author was notified and may override this
     substitution. The two verbatim variant files are preserved in this
     directory with STATUS headers; they are NOT used by the build.
   - gfSub: kept VERBATIM from user_kernels_variant1.chpl (verified 0 errors).
     Argument order: gfSub(x, y) = (x - y) mod p. For SUBLEQ
     (mem[b] -= mem[a]) call gfSub(B[i], A[i]).
   - gfMul: variant 1's uint(128) form does NOT compile on Chapel 2.10
     (no 128-bit integer type exists) — a compile-time verification
     failure, not a math error. Replaced by double-and-add with gfAdd,
     verified 0 errors over the same corpus.

   Field convention: canonical reps 0..p-1; p = 2^64 - 2^32 + 1.
   Branch predicate (SUBLEQ): taken iff rep == 0 or rep > p//2 (signed <= 0).
*/
module GoldilocksKernels {

  param P: uint(64) = 18446744069414584321;
  param HALF: uint(64) = 9223372034707292160; // p//2
  param TWO32M1: uint(64) = 4294967295;       // 2^32 - 1

  /* gfAdd — verified-correct carry-free addition mod p.
     Wrapping add: s = x+y (mod 2^64).
     No carry (s >= x): true sum s < 2^64; result = s>=P ? s-P : s.
     Carry (s < x): true sum = 2^64+s; since 2^64 = 2^32-1 (mod p),
       result = s + (2^32-1), which is < p in the carry case, hence exact.
     (The inner `u < s` re-wrap branch is unreachable for canonical inputs
     — s <= 2^64-2^33 there — but harmless; kept verbatim as verified.) */
  inline proc gfAdd(x: uint(64), y: uint(64)): uint(64) {
    const s = x + y;                          // wrapping
    if s < x {                                // carry: true sum = 2^64 + s; 2^64 ≡ 2^32-1 (mod p)
      const u = s + 0xFFFFFFFF:uint(64);
      if u < s then return u + 0xFFFFFFFF:uint(64);  // < 2^33-2 < p, exact
      return if u >= P then u - P else u;
    }
    return if s >= P then s - P else s;
  }

  /* gfSub — verbatim from user_kernels_variant1.chpl (verified).
     Returns (x - y) mod p. */
  inline proc gfSub(x: uint(64), y: uint(64)): uint(64) {
    if x >= y { const d = x - y; return if d >= P then d - P else d; }
    else       { const d = y - x; return P - (if d > P then d - P else d); }
  }

  /* gfMul — double-and-add via gfAdd (verified).
     Variant 1 used uint(128), which Chapel 2.10 does not provide. */
  proc gfMul(x: uint(64), y: uint(64)): uint(64) {
    var r: uint(64) = 0;
    var xx = x;
    var yy = y;
    while yy != 0 {
      if (yy & 1) != 0 then r = gfAdd(r, xx);
      xx = gfAdd(xx, xx);
      yy >>= 1;
    }
    return r;
  }

  /* SUBLEQ branch predicate on a canonical rep: taken iff <= 0 signed. */
  inline proc branchTaken(rep: uint(64)): bool {
    return rep == 0 || rep > HALF;
  }
}
