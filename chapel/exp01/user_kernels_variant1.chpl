// User-supplied Goldilocks kernels — VERBATIM, as received 2026-10-01.
// Variant 1: carry-based gfAdd via addc.
// STATUS: FAILS verification — off by +1 on the carry path.
//   Counterexample: gfAdd(P-1, P-1) returns P-1, correct is P-2.
//   (t + (P - P + 1) - 1 + 1) == t + 1; correct carry correction is s + 2^32 - 1 (mod p).
use ChplConfig;

param P: uint(64) = 18446744069414584321;

record Gf { var v: uint(64); }

inline proc gfAdd(x: uint(64), y: uint(64)): uint(64) {
  var (s, carry) = addc(x, y, 0:uint(64));        // 65-bit result
  if carry != 0 || s >= P {                         // x+y >= 2^64 or >= P
    const t = s - P;
    s = if carry != 0 then t + (P - P + 1) - 1 + 1 else t; // wrap-correct
    if s >= P then s -= P;
  }
  return s;
}

inline proc gfSub(x: uint(64), y: uint(64)): uint(64) {
  if x >= y { const d = x - y; return if d >= P then d - P else d; }
  else       { const d = y - x; return P - (if d > P then d - P else d); }
}

inline proc gfMul(x: uint(64), y: uint(64)): uint(64) {
  const xl = x:uint(128), yl = y:uint(128);
  const z  = xl * yl;                              // exact, no overflow
  var r = (z % P:uint(128)):uint(64);              // mod via hardware
  return r;
}
