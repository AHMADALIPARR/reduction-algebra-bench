// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 SnapKitty Collective
/* Experiment 01 — Chapel vertical slice of the Reduction Algebra /
   SUBLEQ Attention Benchmark.

   Field arithmetic comes from the VERIFIED module GoldilocksKernels
   (goldilocks_kernels.chpl): gfAdd / gfSub / gfMul / branchTaken, each
   validated bit-for-bit against substrate/goldilocks.py. This program
   defines no field arithmetic of its own.

   Reads three deterministic vectors (a.txt, b.txt, c.txt — decimal
   canonical Goldilocks reps, one per line) from --vecdir, computes every
   op from spec/chapel_experiment_01.json with idiomatic Chapel (native
   reductions, forall), and prints `value <name> ...` lines plus
   `timing <name> <seconds>` lines (mean of --reps runs).

   Kernel choices (documented, all validated before timings are recorded):
   - sum: sequential gfAdd accumulation (scalar baseline).
   - tree_reduction: double-buffered binary tree with gfAdd, forall per
     level. Must equal sum (law L: tree/sequential equivalence).
   - min/max: native `min`/`max reduce` over canonical reps (exact).
   - scan: exact order-fixed prefix scan (Chapel's native `+ scan` wraps
     mod 2^64, not mod p, so its numbers would be invalid here and are
     not recorded).
   - segmented_reduction: forall over 4 segments of 250.
   - subleq_*: forall elementwise; subleq_reduce is sequential because
     branch-gated accumulation is order-significant.
*/
use IO;
use Time;
use GoldilocksKernels;

config const vecdir = ".";
config const reps = 5;

proc readVec(path: string, n: int): [] uint(64) {
  var V: [0..<n] uint(64);
  var f = openReader(path);
  for i in 0..<n {
    f.read(V[i]);
  }
  f.close();
  return V;
}

/* Double-buffered parallel tree sum with gfAdd. */
proc treeSum(X: [] uint(64)): uint(64) {
  const n = X.size;
  if n == 0 then return 0;
  var bufA = X;
  var bufB: [0..<n] uint(64);
  var m = n;
  var readFromA = true;
  while m > 1 {
    const nm = (m + 1) / 2;
    const mm = m;
    if readFromA {
      forall i in 0..<nm with (ref bufB) {
        bufB[i] = if 2*i+1 < mm then gfAdd(bufA[2*i], bufA[2*i+1])
                  else bufA[2*i];
      }
    } else {
      forall i in 0..<nm with (ref bufA) {
        bufA[i] = if 2*i+1 < mm then gfAdd(bufB[2*i], bufB[2*i+1])
                  else bufB[2*i];
      }
    }
    readFromA = !readFromA;
    m = nm;
  }
  return if readFromA then bufA[0] else bufB[0];
}

proc main() {
  const n = 1000;
  const A = readVec(vecdir + "/a.txt", n);
  const B = readVec(vecdir + "/b.txt", n);
  const C = readVec(vecdir + "/c.txt", n);

  var t: stopwatch;

  // --- sum: sequential baseline
  var sumV: uint(64) = 0;
  t.start();
  for r in 1..reps {
    sumV = 0;
    for x in A do sumV = gfAdd(sumV, x);
  }
  t.stop(); writeln("timing sum ", t.elapsed() / reps); t.clear();

  // --- product: scalar accumulation with verified gfMul
  var prodV: uint(64) = 1;
  t.start();
  for r in 1..reps {
    prodV = 1;
    for x in A do prodV = gfMul(prodV, x);
  }
  t.stop(); writeln("timing product ", t.elapsed() / reps); t.clear();

  // --- min / max: native reductions over canonical reps
  var minV: uint(64);
  t.start();
  for r in 1..reps { minV = min reduce A; }
  t.stop(); writeln("timing min ", t.elapsed() / reps); t.clear();
  var maxV: uint(64);
  t.start();
  for r in 1..reps { maxV = max reduce A; }
  t.stop(); writeln("timing max ", t.elapsed() / reps); t.clear();

  // --- scan: exact order-fixed prefix scan
  var scanV: [0..<n] uint(64);
  t.start();
  for r in 1..reps {
    var acc: uint(64) = 0;
    for i in 0..<n {
      acc = gfAdd(acc, A[i]);
      scanV[i] = acc;
    }
  }
  t.stop(); writeln("timing scan ", t.elapsed() / reps); t.clear();

  // --- tree_reduction: parallel tree (must equal sum)
  var treeV: uint(64) = 0;
  t.start();
  for r in 1..reps { treeV = treeSum(A); }
  t.stop(); writeln("timing tree_reduction ", t.elapsed() / reps); t.clear();

  // --- segmented_reduction: 4 segments of 250, forall over segments
  const segLen = 250;
  const nseg = n / segLen;
  var segV: [0..<nseg] uint(64);
  t.start();
  for r in 1..reps {
    forall s in 0..<nseg with (ref segV) {
      var acc: uint(64) = 0;
      for i in 0..<segLen do acc = gfAdd(acc, A[s*segLen + i]);
      segV[s] = acc;
    }
  }
  t.stop(); writeln("timing segmented_reduction ", t.elapsed() / reps); t.clear();

  // --- subleq_subtract: elementwise (B - A) mod p; gfSub(x,y) = x - y
  var subV: [0..<n] uint(64);
  t.start();
  for r in 1..reps {
    forall i in 0..<n with (ref subV) do subV[i] = gfSub(B[i], A[i]);
  }
  t.stop(); writeln("timing subleq_subtract ", t.elapsed() / reps); t.clear();

  // --- subleq_compare: branch predicate per element
  var cmpV: [0..<n] uint(64);
  t.start();
  for r in 1..reps {
    forall i in 0..<n with (ref cmpV) do
      cmpV[i] = if branchTaken(gfSub(B[i], A[i])) then 1 else 0;
  }
  t.stop(); writeln("timing subleq_compare ", t.elapsed() / reps); t.clear();

  // --- subleq_route: conditional select (branch ? diff : C)
  var routeV: [0..<n] uint(64);
  t.start();
  for r in 1..reps {
    forall i in 0..<n with (ref routeV) do
      routeV[i] = if cmpV[i] == 1 then subV[i] else C[i];
  }
  t.stop(); writeln("timing subleq_route ", t.elapsed() / reps); t.clear();

  // --- subleq_reduce: routed accumulation (order-significant, sequential)
  var redV: uint(64) = 0;
  t.start();
  for r in 1..reps {
    redV = 0;
    for i in 0..<n {
      const d = gfSub(B[i], A[i]);
      if branchTaken(d) then redV = gfAdd(redV, d);
    }
  }
  t.stop(); writeln("timing subleq_reduce ", t.elapsed() / reps); t.clear();

  // --- goldilocks_arithmetic: elementwise sub + mul
  var arithSub: [0..<n] uint(64);
  t.start();
  for r in 1..reps {
    forall i in 0..<n with (ref arithSub) do arithSub[i] = gfSub(B[i], A[i]);
  }
  t.stop(); writeln("timing arith_subleq_subtract ", t.elapsed() / reps); t.clear();
  var arithMul: [0..<n] uint(64);
  t.start();
  for r in 1..reps {
    forall i in 0..<n with (ref arithMul) do arithMul[i] = gfMul(A[i], B[i]);
  }
  t.stop(); writeln("timing arith_subleq_multiply ", t.elapsed() / reps); t.clear();

  // --- values (run_exp01.py validates every one against the scalar
  //     reference before any timing is recorded)
  writeln("value sum ", sumV);
  writeln("value product ", prodV);
  writeln("value min ", minV);
  writeln("value max ", maxV);
  write("value scan");
  for x in scanV do write(" ", x);
  writeln();
  writeln("value tree_reduction ", treeV);
  write("value segmented_reduction");
  for x in segV do write(" ", x);
  writeln();
  write("value subleq_subtract");
  for x in subV do write(" ", x);
  writeln();
  write("value subleq_compare");
  for x in cmpV do write(" ", x);
  writeln();
  write("value subleq_route");
  for x in routeV do write(" ", x);
  writeln();
  writeln("value subleq_reduce ", redV);
  writeln("value attention_subleq_reduce ", redV);
  write("value arith_subleq_subtract");
  for x in arithSub do write(" ", x);
  writeln();
  write("value arith_subleq_multiply");
  for x in arithMul do write(" ", x);
  writeln();
}
