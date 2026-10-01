# Recursive Array Reduction Algebra Library — Executed Reference Core

A compact C reference implementation of a recursive array-operation AST for benchmarking SUBLEQ-style routing and Goldilocks-field reductions.

Implemented operation nodes: reduce, scan, fold, map, subtract, compare, select, route, contract, inner, outer, tree-reduce, segmented-reduce, field-add, field-sub, field-mul, field-reduce, SHA-256 seal.

The current executable benchmark uses the path:

`Array -> subtract -> compare -> select -> route -> Goldilocks field-reduce -> result`

Goldilocks prime: `2^64 - 2^32 + 1 = 18446744069414584321`.

The seal node uses OpenSSL SHA-256 over the evaluated child array bytes, so sealing is part of the recursive operation graph rather than an after-the-fact annotation.

## Build and execute

```sh
make
./test
./rarbench 4096 50
```

## Runtime availability

The requested Chapel, Wolfram, Remora, SaC, Singeli, TinyAPL, April, Nial, and Klong runtimes were not present in this execution environment, so no benchmark result for those languages is fabricated. The C reference core is fully compiled and executed here and can serve as the semantic oracle when those runtimes are added.
