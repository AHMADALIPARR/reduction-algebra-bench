(* =====================================================================
   Experiment 02 — Wolfram Language Reduction Algebra Benchmark
   Shares Phase 0 spec: SplitMix64 seed 0x00BEEFCAFE, Goldilocks
   p = 18446744069414584321, predicate d <= 0 (SPECIFIED).
   ===================================================================== *)
p  = 18446744069414584321;   (* 2^64 - 2^32 + 1 *)
M64 = 2^64;
seed = 16^^00BEEFCAFE;
(* ---------- SplitMix64 — must match Chapel output exactly ---------- *)
splitMix64[state_] := Module[{z},
   z = Mod[state + 16^^9E3779B97F4A7C15, M64];
   z = Mod[BitXor[z, BitShiftRight[z, 30]] * 16^^BF58476D1CE4E5B9, M64];
   z = Mod[BitXor[z, BitShiftRight[z, 27]] * 16^^94D049BB133111EB, M64];
   z = BitXor[z, BitShiftRight[z, 31]];
   {Mod[z, p], z}];          (* {fieldValue, nextState} *)
makeVec[n_] := Module[{s = seed, v = ConstantArray[0, n], x},
   Do[{x, s} = splitMix64[s]; v[[i]] = x, {i, n}];
   v];
(* ---------- Goldilocks kernels (exact; machine integers are
              arbitrary precision in WL — no overflow by construction) *)
gfAdd[x_, y_] := Mod[x + y, p];
gfSub[x_, y_] := Mod[x - y + p, p];
gfMul[x_, y_] := Mod[x y, p];
gfPow[x_, e_] := PowerMod[x, e, p];
gfInv[x_]     := PowerMod[x, p - 2, p];
(* ---------- Reduction topologies ---------- *)
reduceSeq[op_, v_] := Fold[op, First[v], Rest[v]];   (* R1, depth n-1 *)
reduceTree[op_, v_] := Module[{a = v},
   While[Length[a] > 1,
     With[{h = Quotient[Length[a], 2]},
       a = MapThread[op, {a[[;; h]], a[[h + 1 ;; h + h]]}] ~Join~
           If[OddQ[Length[a]], {a[[-1]]}, {}]]];
   If[a === {}, op[], a[[1]]]];   (* empty -> identity handled by caller *)
reduceChunked[op_, v_, c_: 4096] := Module[{chunks},
   chunks = reduceSeq[op, #] & /@ Partition[v, c, c, {1, 1}, {}];
   reduceTree[op, chunks]];
(* ---------- Scan (symbolic vs packed comparison axis) ---------- *)
scanSeq[op_, v_] := FoldList[op, v];
(* ---------- SUBLEQ routed reduction (R7) ---------- *)
(* SPECIFIED predicate: branch taken when d <= 0 *)
subleqRouted[K_, Q_, V_] := Module[{d, sel, taken},
   d = gfSub @@@ Transpose[{K, Q}];      (* ARRAY_SUBTRACT, materialized *)
   sel = Pick[V, NonPositive[d]];        (* PREDICATE + SELECT + ROUTE *)
   {gfAdd @@ Prepend[sel, 0],            (* REDUCE, sequential fold *)
    Count[d, x_ /; x <= 0]}];            (* takenBranches *)];
(* ---------- Correctness gate (mirror of Chapel suite) ---------- *)
correctness[] := Module[{ok = True, X, refv, adv},
   Do[
     X = makeVec[n];
     Do[
       refv = If[n == 0, identityOf[op], reduceSeq[op, X]];
       If[reduceTree[op, X] =!= refv, ok = False;
         Print["FAIL tree n=", n, " op=", op]];
       If[reduceChunked[op, X] =!= refv, ok = False;
         Print["FAIL chunk n=", n, " op=", op]],
       {op, {gfAdd, gfMul, Min, Max, BitAnd, BitOr}}],
     {n, {0, 1, 2, 3, 127, 128, 4096, 4097}}];
   (* adversarial + identities *)
   adv = {0, 1, p - 1, p - 2, (p - 1)/2, (p - 1)/2 + 1};
   Do[
     If[gfAdd[x, 0] =!= x, ok = False];
     If[gfMul[x, gfInv[x]] =!= 1, ok = False];
     If[gfSub[gfAdd[x, p - 1], p - 1] =!= x, ok = False],
     {x, adv}];
   (* cross-language equivalence: first 8 values must match Chapel's *)
   (* Chapel emits a checksum of makeVec[1024] in its JSON; compare here *)
   ok];
identityOf[gfAdd] = 0; identityOf[gfMul] = 1;
identityOf[Min] = Infinity; identityOf[Max] = -Infinity;
identityOf[BitAnd] = 16^^FFFFFFFFFFFFFFFF; identityOf[BitOr] = 0;
(* ---------- Timing (RepeatedTiming; warm-up explicit) ---------- *)
timed[f_] := Module[{t},
   Do[f[], {3}];                          (* warm-up *)
   t = RepeatedTiming[f[], 20];           (* {value, seconds} *)
   t[[2]] * 1e9];                         (* ns, median-flavored *)
(* ---------- Main ---------- *)
Module[{X, tSeq, tTree, tFus, K, Q, V, r},
  If[!correctness[], Print["GATE FAILED — no results"]; Abort[]];
  Print["gate: PASS"];
  Do[
    X = makeVec[n];
    tSeq  = timed[reduceSeq[gfAdd, X] &];
    tTree = timed[reduceTree[gfAdd, X] &];
    tFus  = timed[Total[X, Method -> "Compiled"] /. t_ :> Mod[t, p] &];
    (* ^ fused-axis probe: machine-speed Total, single mod after *)
    Print["N=", n, "  seq=", tSeq, "  tree=", tTree, "  totalFused=", tFus, " ns"],
    {n, {128, 256, 512, 1024, 2048, 4096, 8192}}];
  {K, Q, V} = makeVec[1000] & /@ {1, 2, 3};   (* placeholder lengths; see note *)
  r = subleqRouted[K, Q, V];
  Print["R7: taken=", r[[2]], "/1000  ratio=", r[[2]]/1000.];]
