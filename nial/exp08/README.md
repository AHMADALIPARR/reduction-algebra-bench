# Exp08: Nial Track

## Status
- **Implementation**: Draft exists, UNEXECUTED
- **Gate**: NULL (not run)
- **Measurements**: NULL (not run)

## Toolchain
- **Source**: https://github.com/niallang/Nial_Development/releases/download/Originals/Linux64.zip
- **Binary**: `Linux/nial64` (Q'Nial)
- **Note**: The brief URL `nial-array-language/nial` was wrong (404). Correct is `niallang/Nial_Development`.

## Why Not Executed
1. The Q'Nial binary installs and runs (prints usage), but script invocation is unclear.
   - `./Linux/nial64 script.ndf` exits with code 1, no output.
   - `./Linux/nial64 -defs script.ndf` produces no output.
   - Piping via stdin prints usage.
2. The previous session (2026-10-01) reported successful basic measurements:
   - Nial ints are signed 64-bit with overflow FAULT (not wrap)
   - No integer bitwise ops (`bitxor` may not exist for ints)
   - `/` is division, not reduce
   - `pick` is 0-based infix
   - SplitMix64 needs 32-bit-limb emulation (to avoid overflow fault)
   But the working invocation and test scripts were in /tmp (cleared on VM restart).
3. The `exp08_nial.ndf` draft uses assumed primitives (fold, each, link, bitxor, etc.)
   that were never verified against the real toolchain. It needs a rewrite.

## What Would Be Needed
- Figure out Q'Nial script invocation (possibly needs interactive PTY, or a `load` command, or specific file format)
- Rewrite `exp08_nial.ndf` using only verified primitives
- Implement SplitMix64 with 32-bit limbs (to avoid 64-bit overflow fault)
- Verify crosslang checksum 1388262917130611548 before recording any timings

## Results
See `results/exp08_nial.json` (all nulls with reason).
