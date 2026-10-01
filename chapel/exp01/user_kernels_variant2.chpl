// User-supplied Goldilocks kernel — VERBATIM, as received 2026-10-01.
// Variant 2: carry-free gfAdd attempt.
// STATUS: FAILS verification — catastrophically.
//   Counterexample: gfAdd(0, 0) returns 4294967295 (2^32 - 1), correct is 0.
param P: uint(64) = 18446744069414584321;

// add without 128-bit: p + x mod 2^64 wraps predictably since p ≡ 2^64 - 2^32 + 1
inline proc gfAdd(a: uint(64), b: uint(64)): uint(64) {
  const s  = a + b;                    // mod 2^64 wrap possible
  const s' = s - P;                    // two's-complement borrow if s < P
  return if s < a then (if s' > s then s' else P - (P - s))  // wrapped path
         else (if s' > s then s');                    // normal path
}
