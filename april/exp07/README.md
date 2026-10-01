# Exp07: April Track

## Status
- **Implementation**: Complete draft, UNEXECUTED
- **Gate**: NULL (not run)
- **Measurements**: NULL (not run)

## Toolchain
- **Required**: SBCL + Quicklisp + April (https://github.com/phantomics/april)
- **Status**: Not installed. `apt-get install sbcl` blocked (apt lock held by another
  process; `apt-get update` cannot run to locate the package).

## Design
The `exp07_april.lisp` implementation:
- Uses Common Lisp bignums for 64-bit-exact field arithmetic and SplitMix64
  (April's APL numbers are doubles; 2^53 mantissa cannot hold 2^64 reps exactly,
  so April is NOT used for modular arithmetic).
- Uses April for array TOPOLOGY: tree/segmented reduction shapes, scan, and the
  SUBLEQ predicate+select stage via APL compression.
- April reduction probes are tagged "probe" — never compared head-to-head with
  exact Lisp folds as if equivalent.

## Why Not Executed
SBCL is not available in this build environment and could not be installed
within the time-box. Without SBCL, Quicklisp and April cannot be loaded,
and the Lisp implementation cannot be verified.

## Results
See `results/exp07_april.json` (all nulls with reason).
