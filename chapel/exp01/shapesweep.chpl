// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 SnapKitty Collective
/* shapesweep.chpl — Experiment 01b: topology × shape sweep.

   Kernels: imported VERBATIM from the committed verified build via
   `use GoldilocksKernels` (gfAdd / gfSub / gfMul / branchTaken from
   chapel/exp01/goldilocks_kernels.chpl at commit 6ebbb5d). No field
   arithmetic is defined or edited in this file.

   Determinism source: SplitMix64, seed 0x00BEEFCAFE (Phase 0 spec).
   The Chapel stream is cross-validated bit-for-bit against
   substrate/splitmix64.py (first 8 values + cross-language checksum
   over 1024 values) BEFORE any timing is trusted — compare the
   CHECKSUM lines against the Python oracle's output.

   Timing protocol: 3 warmup, 20 measured, median reported
   (tagged "median20" in JSON; Exp 01 used mean-of-5 — protocols are
   NOT interchangeable, each timing is tagged).

   Documented deviations from the track-1 draft (the draft referenced
   identifiers from an uncommitted reductionBench.chpl and contained
   two defects):
   - draft reduceFusedIntent used `forall ... with (+ reduce acc)` where
     Chapel's `+` is wrapping add, not gfAdd — incorrect as written.
     Replaced with per-task sequential partials + a single gfAdd combine.
   - draft R7 used `if d <= 0` on uint(64) (always true) and returned a
     per-element array (no inter-element reduction). Replaced with the
     SPECIFIED predicate branchTaken(d) and scalar accumulation — a
     genuine reduction; per-element work is identical.
   - draft referenced Op.GfSum / refReduce / SubleqStats from the
     uncommitted draft; the driver below is written against the
     committed exp01.chpl building blocks (double-buffered treeSum
     algorithm copied verbatim, renamed reduceTree).
*/
use IO;
use Time;
use Sort;
use GoldilocksKernels;

param SEED: uint(64) = 0x00BEEFCAFE;

/* ---------- SplitMix64 (Phase 0 PRNG; cross-validated, see header) ---------- */
class SplitMix64 {
  var state: uint(64);
  proc init(seed: uint(64)) { this.state = seed; }
  proc next(): uint(64) {
    state += 0x9E3779B97F4A7C15:uint(64);
    var z = state;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9:uint(64);
    z = (z ^ (z >> 27)) * 0x94D049BB133111EB:uint(64);
    z = z ^ (z >> 31);
    return z % P;
  }
}

/* ---------- Reduction topologies (gfAdd-only; kernels untouched) ---------- */
proc reduceSeq(X: [] uint(64)): uint(64) {
  var acc: uint(64) = 0;
  for x in X do acc = gfAdd(acc, x);
  return acc;
}

/* Double-buffered parallel tree — algorithm copied verbatim from
   exp01.chpl treeSum (verified build), renamed reduceTree. */
proc reduceTree(X: [] uint(64)): uint(64) {
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

proc reduceChunked(X: [] uint(64)): uint(64) {
  const n = X.size;
  if n == 0 then return 0;
  const C = 4096;
  const nChunks = (n + C - 1) / C;
  var sums: [0..<nChunks] uint(64);
  forall c in 0..<nChunks with (ref sums) {
    var acc: uint(64) = 0;
    const lo = c*C;
    const hi = min(n, lo+C);
    for i in lo..<hi do acc = gfAdd(acc, X[i]);
    sums[c] = acc;
  }
  return reduceTree(sums);
}

/* Fused map-reduce: map x -> gfAdd(x,1) fused into per-task sequential
   partials, single gfAdd combine. (See header: draft's reduce-intent
   form was incorrect as written.) */
proc reduceFused(X: [] uint(64)): uint(64) {
  const n = X.size;
  if n == 0 then return 0;
  const nTasks = here.maxTaskPar;
  var partials: [0..<nTasks] uint(64);
  coforall t in 0..<nTasks with (ref partials) {
    var acc: uint(64) = 0;
    const chunk = (n + nTasks - 1) / nTasks;
    const lo = t*chunk;
    const hi = min(n, lo+chunk);
    for i in lo..<hi do acc = gfAdd(acc, gfAdd(X[i], 1));
    partials[t] = acc;
  }
  var total: uint(64) = 0;
  for p in partials do total = gfAdd(total, p);
  return total;
}

proc reduceSeqFusedRef(X: [] uint(64)): uint(64) {
  var acc: uint(64) = 0;
  for x in X do acc = gfAdd(acc, gfAdd(x, 1));
  return acc;
}

/* ---------- SUBLEQ routed reduction (R7, SPECIFIED predicate d<=0) ---------- */
record SubleqStats {
  var subtractions: int;
  var predicates: int;
  var branches: int;
  var takenBranches: int;
  var loads: int;
  var stores: int;
  var instructions: int; // specified count model: 4 per element
}

proc subleqRoutedGfReduce(K, Q, V: [] uint(64), ref stats: SubleqStats): uint(64) {
  const n = K.size;
  var acc: uint(64) = 0;
  var taken = 0;
  for i in 0..<n {
    const d = gfSub(K[i], Q[i]);
    if branchTaken(d) { acc = gfAdd(acc, V[i]); taken += 1; }
  }
  stats.subtractions = n;
  stats.predicates = n;
  stats.branches = n;
  stats.takenBranches = taken;
  stats.loads = 2*n + taken;
  stats.stores = 0;
  stats.instructions = 4*n;
  return acc;
}

proc subleqRoutedGfReduceRef(K, Q, V: [] uint(64)): uint(64) {
  var acc: uint(64) = 0;
  for i in 0..<K.size {
    const d = gfSub(K[i], Q[i]);
    if branchTaken(d) then acc = gfAdd(acc, V[i]);
  }
  return acc;
}

/* Atomic-free counter for the double-and-add gfMul's inner gfAdds.
   Per element: bit_length(y) doublings + popcount(y) conditional adds,
   exactly mirroring gfMul's loop. JSON separates these implementation
   ops from the algebraic op count (n gfMuls). */
proc countMulAdds(V: [] uint(64)): uint(64) {
  var total: uint(64) = 0;
  forall v in V with (+ reduce total) {
    var c: uint(64) = 0;
    var y = v;
    while y != 0 { c += 1 + (y & 1); y >>= 1; }
    total += c;
  }
  return total;
}

/* ---------- Timing: 3 warmup, 20 measured, median ----------
   (Dispatches through a select rather than a first-class function:
   keeps the timing loop in one place with zero cleverness.) */
record Timing {
  var median_ns: real;
  var min_ns: real;
  var max_ns: real;
  var mean_ns: real;
}

enum Kernel { seq, tree, chunked, fused, routed, mul }

/* Returns the kernel's result so the optimizer cannot discard the
   timed work. timeKernel folds every result into an escape checksum
   that is printed at the end of the run. */
proc runKernel(k: Kernel, X: [] uint(64),
               K: [] uint(64), Q: [] uint(64), V: [] uint(64),
               ref sink: [] uint(64)): uint(64) {
  select k {
    when Kernel.seq     do return reduceSeq(X);
    when Kernel.tree    do return reduceTree(X);
    when Kernel.chunked do return reduceChunked(X);
    when Kernel.fused   do return reduceFused(X);
    when Kernel.routed {
      var st = new SubleqStats();
      return subleqRoutedGfReduce(K, Q, V, st);
    }
    when Kernel.mul {
      var x: uint(64) = 0;
      forall i in 0..<K.size with (^ reduce x, ref sink) {
        sink[i] = gfMul(K[i], V[i]);
        x ^= sink[i];
      }
      return x;
    }
  }
  return 0; // unreachable: select over Kernel is exhaustive
}

proc timeKernel(k: Kernel, X: [] uint(64),
                K: [] uint(64), Q: [] uint(64), V: [] uint(64),
                ref sink: [] uint(64), ref escapes: uint(64)): Timing {
  for 1..3 do escapes = gfAdd(escapes, runKernel(k, X, K, Q, V, sink));
  var samples: [0..<20] real;
  var t: stopwatch;
  for s in 0..<20 {
    t.clear(); t.start();
    escapes = gfAdd(escapes, runKernel(k, X, K, Q, V, sink));
    t.stop();
    samples[s] = t.elapsed() * 1e9;
  }
  sort(samples);
  var mean = 0.0;
  for x in samples do mean += x;
  mean /= 20.0;
  return new Timing(samples[10], samples[0], samples[19], mean);
}

/* ---------- Cross-language checksum (Experiment-10 gate, early) ---------- */
proc emitChecksum() {
  const rng = new SplitMix64(SEED);
  var first8: [0..<8] uint(64);
  for i in 0..<8 do first8[i] = rng.next();
  var acc: uint(64) = 0;
  for i in 8..<1024 do acc = gfAdd(acc, rng.next());
  for x in first8 do acc = gfAdd(acc, x);
  write("CHECKSUM crosslang_checksum ", acc);
  write(" first8");
  for x in first8 do write(" ", x);
  writeln();
}

/* ---------- Sweep 1: [N] topology sweep, gf-sum ---------- */
proc sweep1D(): uint(64) {
  writeln("== [N] sweep: gf-sum, all topologies ==");
  var escapes: uint(64) = 0;
  for n in [128, 256, 512, 1024, 2048, 4096, 8192] {
    const rng = new SplitMix64(SEED);
    var X: [0..<n] uint(64);
    for i in 0..<n do X[i] = rng.next();
    // verify-before-record (mandatory)
    const refv = reduceSeq(X);
    const refFused = reduceSeqFusedRef(X);
    var ok = true;
    if reduceTree(X) != refv    { writeln("FAIL tree n=", n); ok = false; }
    if reduceChunked(X) != refv { writeln("FAIL chunked n=", n); ok = false; }
    if reduceFused(X) != refFused { writeln("FAIL fused n=", n); ok = false; }
    if !ok then continue;
    var empty: [0..<0] uint(64);
    const tSeq  = timeKernel(Kernel.seq, X, empty, empty, empty, empty, escapes);
    const tTree = timeKernel(Kernel.tree, X, empty, empty, empty, empty, escapes);
    const tChk  = timeKernel(Kernel.chunked, X, empty, empty, empty, empty, escapes);
    const tFus  = timeKernel(Kernel.fused, X, empty, empty, empty, empty, escapes);
    writef("N=%5i  seq_med=%r  tree_med=%r  chunk_med=%r  fused_med=%r  ns/elem_seq=%r\n",
           n, tSeq.median_ns, tTree.median_ns, tChk.median_ns, tFus.median_ns,
           tSeq.median_ns / n);
    writef("M1D n=%i seq=%r tree=%r chunked=%r fused=%r\n",
           n, tSeq.median_ns, tTree.median_ns, tChk.median_ns, tFus.median_ns);
  }
  return escapes;
}

/* ---------- Sweep 2: [B,N,D] SUBLEQ mul-vs-routed dominance ---------- */
proc sweepSubleq(): uint(64) {
  writeln("== [B,N,D] SUBLEQ sweep: mul vs reduce dominance test ==");
  var escapes: uint(64) = 0;
  for (b, n, d) in [(1,128,64), (1,512,64), (1,2048,64), (1,8192,64),
                    (2,1024,128), (4,1024,256)] {
    const total = b * n * d;
    const rng = new SplitMix64(SEED);
    var K, Q, V: [0..<total] uint(64);
    for i in 0..<total { K[i]=rng.next(); Q[i]=rng.next(); V[i]=rng.next(); }
    // verify-before-record
    var stats = new SubleqStats();
    const r1 = subleqRoutedGfReduce(K, Q, V, stats);
    const r2 = subleqRoutedGfReduceRef(K, Q, V);
    if r1 != r2 { writeln("FAIL routed b=", b, " n=", n, " d=", d); continue; }
    const mulAdds = countMulAdds(V);
    var noX: [0..<0] uint(64);
    var sink: [0..<total] uint(64);
    const tR = timeKernel(Kernel.routed, noX, K, Q, V, sink, escapes);
    const tM = timeKernel(Kernel.mul, noX, K, Q, V, sink, escapes);
    const ratio = tM.median_ns / tR.median_ns;
    writef("B=%i N=%5i D=%3i  mul_med=%r  routed_med=%r  ratio=%.2dr  taken=%i/%i  impl_gfAdds=%i\n",
           b, n, d, tM.median_ns, tR.median_ns, ratio,
           stats.takenBranches, total, mulAdds);
    writef("MSUB b=%i n=%i d=%i total=%i mul=%r routed=%r ratio=%r taken=%i impl_gfAdds=%i\n",
           b, n, d, total, tM.median_ns, tR.median_ns, ratio,
           stats.takenBranches, mulAdds);
  }
  return escapes;
}

proc main() {
  emitChecksum();
  var e1 = sweep1D();
  var e2 = sweepSubleq();
  writeln("escape_checksum ", gfAdd(e1, e2));
}
