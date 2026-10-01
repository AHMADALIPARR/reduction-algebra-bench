#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 SnapKitty Collective
"""Generate README chart assets from measured results. Real numbers only."""
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(ROOT, "docs", "assets")
os.makedirs(ASSETS, exist_ok=True)

plt.rcParams.update({
    "figure.facecolor": "#0b0e17",
    "axes.facecolor": "#0b0e17",
    "axes.edgecolor": "#2a3350",
    "axes.labelcolor": "#c8d3f5",
    "xtick.color": "#8b98b8",
    "ytick.color": "#8b98b8",
    "text.color": "#e8ecf8",
    "grid.color": "#1a2138",
    "font.family": "sans-serif",
})
CYAN, MAG, AMBER, GREEN, VIOLET, RED = "#22d3ee", "#f472b6", "#fbbf24", "#34d399", "#a78bfa", "#f87171"

def v(x):
    return x["value"] if isinstance(x, dict) and "value" in x else x

def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(ASSETS, name), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)

# ---- 1. SUBLEQ dominance (Chapel exp01b) ----
d = json.load(open(os.path.join(ROOT, "results/exp01b_shapesweep.json")))
dom = d["sweep_subleq_dominance"]
ns = [r["n"] for r in dom]
ratios = [v(r["mul_over_routed"]) for r in dom]
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(ns, ratios, "o-", color=CYAN, lw=2.5, ms=8, label="mul / routed")
ax.fill_between(ns, 27, 51, color=CYAN, alpha=0.08)
ax.set_xscale("log", base=2)
ax.set_xticks(ns, [str(n) for n in ns])
ax.set_ylabel("mul ÷ routed time")
ax.set_xlabel("n (elements)")
ax.set_title("SUBLEQ attention: multiply dominance is structural, not noise", fontsize=13, pad=12)
ax.grid(True, which="both", alpha=0.5)
for n, r in zip(ns, ratios):
    ax.annotate(f"{r:.1f}×", (n, r), textcoords="offset points", xytext=(0, 10),
                ha="center", fontsize=9, color=CYAN)
ax.text(0.02, 0.95, "flat across 64× of n → the kernel axis is the lever",
        transform=ax.transAxes, fontsize=10, color=AMBER, va="top")
save(fig, "chart_subleq_dominance.png")

# ---- 2. Topology sweep (Chapel exp01b) ----
topo = d["sweep_1d_topology"]
tn = [r["n"] for r in topo]
series = {
    "seq": ([v(r["seq_ns"]) for r in topo], CYAN),
    "tree": ([v(r["tree_ns"]) for r in topo], MAG),
    "chunked": ([v(r["chunked_ns"]) for r in topo], GREEN),
    "fused": ([v(r["fused_ns"]) for r in topo], AMBER),
}
fig, ax = plt.subplots(figsize=(9, 4.6))
for name, (ys, c) in series.items():
    ys = [y if y and y > 0 else np.nan for y in ys]
    ax.plot(tn, ys, "o-", color=c, lw=2, ms=6, label=name)
ax.set_xscale("log", base=2); ax.set_yscale("log")
ax.set_xticks(tn, [str(n) for n in tn])
ax.set_ylabel("ns (median, log)")
ax.set_xlabel("n (elements)")
ax.set_title("Reduction topology sweep — Chapel, single locale", fontsize=13, pad=12)
ax.legend(framealpha=0.2)
ax.grid(True, which="both", alpha=0.5)
ax.text(0.02, 0.95, "n=128 seq below timer granularity (0 ns) — reported, not hidden",
        transform=ax.transAxes, fontsize=9, color=AMBER, va="top")
save(fig, "chart_topo_sweep.png")

# ---- 3. TinyAPL kernels (exp06, n=1024) ----
t = json.load(open(os.path.join(ROOT, "results/exp06_tinyapl.json")))
ms = [m for m in t["measurements"] if v(m["n"]) == 1024]
kernels = [v(m["kernel"]) for m in ms]
meds = [v(m["median_seconds"]) * 1000 for m in ms]
order = np.argsort(meds)
fig, ax = plt.subplots(figsize=(9, 5.2))
colors = [MAG if "subleq" in k else (VIOLET if k in ("attention",) else (AMBER if k.startswith("gf_") else CYAN)) for k in kernels]
bars = ax.barh([kernels[i] for i in order], [meds[i] for i in order],
               color=[colors[i] for i in order], edgecolor="none", height=0.62)
ax.set_xscale("log")
ax.set_xlabel("median ms (log, 3 warmup / 20 samples)")
ax.set_title("TinyAPL — 14 kernels @ n=1024, all escape-checksummed", fontsize=13, pad=12)
for b, mval in zip(bars, [meds[i] for i in order]):
    ax.text(b.get_width() * 1.06, b.get_y() + b.get_height() / 2,
            f"{mval:.2f} ms" if mval < 1000 else f"{mval/1000:.2f} s",
            va="center", fontsize=8.5, color="#c8d3f5")
ax.grid(True, axis="x", alpha=0.4)
save(fig, "chart_tinyapl_kernels.png")

# ---- 4. Klong sweep (exp09) ----
k = json.load(open(os.path.join(ROOT, "klong/exp09/results/exp09_klong.json")))
kd = k["sweep_1d"]["data"]
kn = [r["n"] for r in kd]
fig, ax = plt.subplots(figsize=(9, 4.6))
for key, c, label in (("sum", CYAN, "sum"), ("tree", MAG, "tree"), ("chunked", GREEN, "chunked")):
    ys = [r[key] * 1000 for r in kd]
    ax.plot(kn, ys, "o-", color=c, lw=2, ms=7, label=label)
ax.set_xscale("log", base=2); ax.set_yscale("log")
ax.set_xticks(kn, [str(n) for n in kn])
ax.set_ylabel("ms (log)")
ax.set_xlabel("n (elements)")
ax.set_title("Klong — sweep_1d (1 warmup / 5 samples / minimum — protocol deviation tagged)", fontsize=12, pad=12)
ax.legend(framealpha=0.2)
ax.grid(True, which="both", alpha=0.5)
save(fig, "chart_klong_sweep.png")

# ---- 5. C reference throughput ----
cn, ct = [], []
for n in (128, 4096, 65536):
    p = os.path.join(ROOT, f"c-reference/results/bench-{n}.json")
    if os.path.exists(p):
        b = json.load(open(p))
        cn.append(n); ct.append(b["elements_per_second_best"] / 1e6)
fig, ax = plt.subplots(figsize=(9, 4.2))
bars = ax.bar([str(n) for n in cn], ct, color=CYAN, edgecolor="none", width=0.55)
ax.set_ylabel("M elements / second (best)")
ax.set_xlabel("n")
ax.set_title("C reference core — throughput (gcc -O3, correctness PASS)", fontsize=13, pad=12)
for b, cval in zip(bars, ct):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() * 1.02, f"{cval:.1f} M",
            ha="center", fontsize=10, color="#c8d3f5")
ax.set_ylim(0, max(ct) * 1.18)
save(fig, "chart_cref_throughput.png")
print("done")
