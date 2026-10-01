# Exp09 Klong RUNLOG

## 2026-10-01
- Brief URL `brianguertin/klong` → GitHub API 404. Correct source: http://t3x.org/klong/ (Nils M. Holm).
- Downloaded klong20221212.tgz, built via `make kg` (needs kg.c + s9core.c; `cc -O3 -o kg kg.c` alone fails with undefined S9 refs).
- Implemented SplitMix64 (closed form), Goldilocks field ops, reductions (sum/tree/chunked/scan), SUBLEQ.
- **Checksum VERIFIED**: 1388262917130611548 (matches crosslang).
- **Gate PASS**: crosslang checksum + adversarial field identities + topology agreement (n=0,1,2,3,127,128,4096,4097).
- **sweep_1d MEASURED**: n=128..1024, sum/tree/chunked timings (see results/exp09_klong.json).
- sweep_subleq EXECUTED but output lost when /tmp cleared (VM cleanup).
- Klong syntax quirks documented in README.md.
- /tmp/klong/kg and working .kg lost on /tmp clear; toolchain rebuilt, results preserved in workspace.

## Deviations
- Timing: 1 warmup/5 samples/minimum (spec: 3/20/median)
- SUBLEQ shapes reduced for feasibility
- sweep_subleq: null (output lost)
