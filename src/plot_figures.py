#!/usr/bin/env python3
# =============================================================================
# Copyright (c) 2026 Mustafa Azzawi.  All rights reserved.
#
# plot_figures.py — Figure-generation pipeline.
#
# Reads CSVs from data/ and writes 300 dpi PNGs to figures/ at the typography
# used in the manuscript (sans-serif 8 pt axis labels, single-column width).
# Designed to be re-run independently of the simulator: the simulator owns
# the numerical work; this script owns the visual presentation.
#
# Usage:
#     python3 src/plot_figures.py                # produce every figure
#     python3 src/plot_figures.py --only pdr     # only one figure
#
# All rights reserved.  See LICENSE.
# =============================================================================
import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


HERE      = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
DATA_DIR  = REPO_ROOT / "data"
FIG_DIR   = REPO_ROOT / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


plt.rcParams.update({
    "font.family":      "sans-serif",
    "font.sans-serif":  ["Helvetica", "Arial", "DejaVu Sans"],
    "font.size":         8,
    "axes.titlesize":    9,
    "axes.labelsize":    8,
    "legend.fontsize":   7,
    "xtick.labelsize":   7,
    "ytick.labelsize":   7,
    "figure.dpi":      300,
    "savefig.dpi":     300,
    "savefig.bbox":    "tight",
    "axes.grid":      True,
    "grid.alpha":      0.3,
    "grid.linestyle": ":",
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "axes.linewidth":    0.6,
    "lines.linewidth":   1.0,
})

COLOR = {
    "PhysaRoute":      "#0072B2",
    "RL-WBAN":         "#56B4E9",
    "PZ-2021":         "#009E73",
    "DARE-IoT":        "#F0E442",
    "PSO-Energy":      "#E69F00",
    "GWO-WBAN":        "#CC79A7",
    "ACO-WBAN":        "#999999",
    "M-ATTEMPT":       "#D55E00",
    "AODV":            "#882255",
    "no-energy":       "#bbbbbb",
    "no-shadowing":    "#888888",
    "no-criticality":  "#555555",
    "no-explore":      "#222222",
}
PROTOCOLS = ["PhysaRoute", "RL-WBAN", "PZ-2021", "DARE-IoT",
             "PSO-Energy", "GWO-WBAN", "ACO-WBAN", "M-ATTEMPT", "AODV"]
FIGSIZE   = (3.4, 2.4)


def _read(name):
    with open(DATA_DIR / name) as f:
        return list(csv.DictReader(f))


def fig_pdr():
    rows = _read("pdr_vs_mobility.csv")
    by = {p: {} for p in PROTOCOLS}
    for r in rows:
        v = float(r["velocity_mps"])
        by[r["protocol"]].setdefault(v, []).append(float(r["pdr"]) * 100)
    vs = sorted(set(float(r["velocity_mps"]) for r in rows))
    fig, ax = plt.subplots(figsize=FIGSIZE)
    for p in PROTOCOLS:
        m = [np.mean(by[p][v]) for v in vs]
        ax.plot(vs, m, "-o", color=COLOR[p], label=p, markersize=3)
    ax.set_xlabel("Patient walking speed (m/s)")
    ax.set_ylabel("Packet delivery ratio (%)")
    ax.set_title("PDR vs mobility (calibrated CM3)")
    ax.legend(loc="lower left", ncol=2, fontsize=6, frameon=False)
    plt.savefig(FIG_DIR / "fig_pdr_vs_mobility.png")
    plt.close()


def fig_energy():
    rows = _read("residual_energy.csv")
    by = {p: [] for p in PROTOCOLS}
    for r in rows:
        by[r["protocol"]].append((float(r["time_s"]),
                                  float(r["residual_pct"])))
    fig, ax = plt.subplots(figsize=FIGSIZE)
    for p in PROTOCOLS:
        arr = np.array(by[p])
        ax.plot(arr[:, 0], arr[:, 1], "-o", color=COLOR[p],
                label=p, markersize=2.5)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Residual energy (% of 6 J budget)")
    ax.set_title("Energy retention over 1000 s")
    ax.legend(loc="upper right", ncol=2, fontsize=6, frameon=False)
    plt.savefig(FIG_DIR / "fig_energy_vs_time.png")
    plt.close()


def fig_latency():
    rows = _read("latency_vs_load.csv")
    by = {p: {} for p in PROTOCOLS}
    for r in rows:
        L = int(r["load_pkts"])
        by[r["protocol"]].setdefault(L, []).append(float(r["latency_ms"]))
    Ls = sorted(set(int(r["load_pkts"]) for r in rows))
    fig, ax = plt.subplots(figsize=FIGSIZE)
    for p in PROTOCOLS:
        m = [np.mean(by[p][L]) for L in Ls]
        ax.plot(Ls, m, "-o", color=COLOR[p], label=p, markersize=3)
    ax.set_xlabel("Offered load (packets/s)")
    ax.set_ylabel("End-to-end latency (ms)")
    ax.set_title("Latency vs load")
    ax.legend(loc="upper left", ncol=2, fontsize=6, frameon=False)
    plt.savefig(FIG_DIR / "fig_latency_vs_load.png")
    plt.close()


def fig_throughput():
    rows = _read("throughput.csv")
    by = {p: {} for p in PROTOCOLS}
    for r in rows:
        L = int(r["rate"])
        by[r["protocol"]].setdefault(L, []).append(float(r["throughput_kbps"]))
    Ls = sorted(set(int(r["rate"]) for r in rows))
    fig, ax = plt.subplots(figsize=FIGSIZE)
    for p in PROTOCOLS:
        m = [np.mean(by[p][L]) for L in Ls]
        ax.plot(Ls, m, "-o", color=COLOR[p], label=p, markersize=3)
    ax.set_xlabel("Rate (packets/s)")
    ax.set_ylabel("Throughput (kbps)")
    ax.set_title("Aggregate throughput")
    ax.legend(loc="upper left", ncol=2, fontsize=6, frameon=False)
    plt.savefig(FIG_DIR / "fig_throughput.png")
    plt.close()


def fig_lifetime():
    rows = _read("network_lifetime.csv")
    by = {p: [] for p in PROTOCOLS}
    for r in rows:
        by[r["protocol"]].append(float(r["lifetime_first_death_s"]))
    fig, ax = plt.subplots(figsize=FIGSIZE)
    xs = np.arange(len(PROTOCOLS))
    means = [np.mean(by[p]) for p in PROTOCOLS]
    sds   = [np.std(by[p], ddof=1) for p in PROTOCOLS]
    ax.bar(xs, means, yerr=sds, capsize=2,
           color=[COLOR[p] for p in PROTOCOLS],
           edgecolor="black", linewidth=0.4)
    ax.set_xticks(xs); ax.set_xticklabels(PROTOCOLS, rotation=35, ha="right")
    ax.set_ylabel("First-node-death (s)")
    ax.set_title("Network lifetime")
    plt.savefig(FIG_DIR / "fig_network_lifetime.png")
    plt.close()


def fig_convergence():
    rows = _read("convergence.csv")
    paths = defaultdict(list)
    for r in rows:
        paths[int(r["path"])].append((int(r["tick"]),
                                       float(r["conductance"])))
    fig, ax = plt.subplots(figsize=FIGSIZE)
    for k, pts in paths.items():
        pts.sort()
        ts = np.array([p[0] for p in pts]) * 0.1
        ds = np.array([p[1] for p in pts])
        ax.plot(ts, ds, label=f"path {k + 1}", linewidth=1.0)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel(r"Conductance $D_{ij}$")
    ax.set_title("Reinforcement-and-pruning convergence")
    ax.legend(loc="center right", fontsize=6, frameon=False)
    plt.savefig(FIG_DIR / "fig_convergence.png")
    plt.close()


def fig_ablation():
    rows = _read("ablation.csv")
    by = defaultdict(list)
    for r in rows:
        by[r["variant"]].append((float(r["pdr"]) * 100,
                                  float(r["lifetime_s"]),
                                  float(r["latency_ms"]),
                                  float(r["throughput_kbps"])))
    ABL = ["PhysaRoute", "no-energy", "no-shadowing", "no-criticality",
           "no-explore"]
    metrics = ["PDR (%)", "Lifetime/20 (s)", "Latency × 2 (ms)",
               "Throughput (kbps)"]
    fig, ax = plt.subplots(figsize=(4.0, 2.6))
    xs = np.arange(len(metrics))
    w = 0.15
    for i, v in enumerate(ABL):
        arr = np.array(by[v])
        m = [arr[:, 0].mean(), arr[:, 1].mean() / 20.0,
             arr[:, 2].mean() * 2.0, arr[:, 3].mean()]
        ax.bar(xs + (i - 2) * w, m, w, color=COLOR[v],
               edgecolor="black", linewidth=0.4, label=v)
    ax.set_xticks(xs); ax.set_xticklabels(metrics, fontsize=7)
    ax.set_title("Four-arm ablation")
    ax.legend(loc="upper right", fontsize=6, frameon=False)
    plt.savefig(FIG_DIR / "fig_ablation.png")
    plt.close()


def fig_coexistence():
    rows = _read("coexistence.csv")
    protos = ["PhysaRoute", "RL-WBAN", "DARE-IoT", "PSO-Energy",
              "M-ATTEMPT", "AODV"]
    by = {p: defaultdict(list) for p in protos}
    for r in rows:
        by[r["protocol"]][float(r["ble_airtime_frac"])].append(
            float(r["pdr"]) * 100)
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ats = [0.0, 0.25, 0.50, 0.75]
    for p in protos:
        m = [np.mean(by[p][a]) for a in ats]
        ax.plot([a * 100 for a in ats], m, "-o", color=COLOR[p],
                label=p, markersize=3)
    ax.set_xlabel("BLE airtime (%)")
    ax.set_ylabel("PDR (%)")
    ax.set_title("Co-existence under BLE interferer")
    ax.legend(loc="lower left", fontsize=6, frameon=False)
    plt.savefig(FIG_DIR / "fig_coexistence.png")
    plt.close()


def fig_sybil_jamming():
    rs = _read("sybil.csv")
    jr = _read("jamming.csv")
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(6.0, 2.4))
    protos_s = ["PhysaRoute", "RL-WBAN", "DARE-IoT", "PSO-Energy"]
    by = {p: defaultdict(list) for p in protos_s}
    for r in rs:
        by[r["protocol"]][float(r["compromised_frac"])].append(
            float(r["pdr"]) * 100)
    for p in protos_s:
        m = [np.mean(by[p][f]) for f in [0.0, 0.10, 0.20, 0.30]]
        axL.plot([0, 10, 20, 30], m, "-o", color=COLOR[p], label=p,
                 markersize=3)
    axL.set_xlabel("Compromised neighbours (%)")
    axL.set_ylabel("PDR (%)")
    axL.set_title("Sybil resistance")
    axL.legend(loc="lower left", fontsize=6, frameon=False)

    protos_j = ["PhysaRoute", "RL-WBAN", "DARE-IoT", "PSO-Energy",
                "M-ATTEMPT", "AODV"]
    by2 = defaultdict(list)
    for r in jr:
        by2[r["protocol"]].append(float(r["pdr"]) * 100)
    xs = np.arange(len(protos_j))
    means = [np.mean(by2[p]) for p in protos_j]
    sds   = [np.std(by2[p], ddof=1) for p in protos_j]
    axR.bar(xs, means, yerr=sds, capsize=2,
            color=[COLOR[p] for p in protos_j], edgecolor="black",
            linewidth=0.4)
    axR.set_xticks(xs); axR.set_xticklabels(protos_j, rotation=35, ha="right")
    axR.set_ylabel("PDR (%) under jamming")
    axR.set_title("Single-node jamming")
    plt.savefig(FIG_DIR / "fig_sybil_jamming.png")
    plt.close()


def fig_failure():
    rows = _read("failure_case.csv")
    by = {p: defaultdict(list) for p in PROTOCOLS}
    for r in rows:
        by[r["protocol"]][float(r["velocity_mps"])].append(
            float(r["pdr"]) * 100)
    fig, ax = plt.subplots(figsize=FIGSIZE)
    vs = [3.0, 3.5, 4.0]
    for p in PROTOCOLS:
        m = [np.mean(by[p][v]) for v in vs]
        ax.plot(vs, m, "-o", color=COLOR[p], label=p, markersize=3)
    ax.set_xlabel("Walking speed (m/s) — off-calibrated")
    ax.set_ylabel("PDR (%)")
    ax.set_title("Failure-case regime (v > 3 m/s)")
    ax.legend(loc="lower left", ncol=2, fontsize=6, frameon=False)
    ax.axvspan(3.0, 4.0, color="red", alpha=0.05)
    plt.savefig(FIG_DIR / "fig_failure_case.png")
    plt.close()


def fig_calibration():
    rows = _read("calibration.csv")
    sigma_at = {}
    by = defaultdict(list)
    for r in rows:
        v = float(r["velocity_mps"])
        by[v].append((float(r["snr_dB"]), float(r["cdf"])))
        sigma_at[v] = float(r.get("sigma_S_dB",
                                  1.8 + (5.6 - 1.8) * v / 3.0))
    fig, ax = plt.subplots(figsize=FIGSIZE)
    for v in sorted(by.keys()):
        pts = sorted(by[v])
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        ax.plot(xs, ys, linewidth=1.2,
                label=f"v = {v:.1f} m/s, σ = {sigma_at[v]:.2f} dB")
    ax.set_xlabel("Received SNR (dB)")
    ax.set_ylabel("CDF")
    ax.set_title("Calibrated CM3 shadowing")
    ax.legend(loc="lower right", fontsize=6, frameon=False)
    plt.savefig(FIG_DIR / "fig_calibration.png")
    plt.close()


FIGURES = {
    "pdr":          fig_pdr,
    "energy":       fig_energy,
    "latency":      fig_latency,
    "throughput":   fig_throughput,
    "lifetime":     fig_lifetime,
    "convergence":  fig_convergence,
    "ablation":     fig_ablation,
    "coexistence":  fig_coexistence,
    "sybil":        fig_sybil_jamming,
    "failure":      fig_failure,
    "calibration":  fig_calibration,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=list(FIGURES.keys()) + ["all"],
                    default="all")
    args = ap.parse_args()
    targets = [args.only] if args.only != "all" else list(FIGURES.keys())
    for name in targets:
        try:
            FIGURES[name]()
            print(f"  ✓ figures/{name}.png")
        except FileNotFoundError as e:
            print(f"  ✗ {name}: missing CSV ({e}). Run the simulator first.")


if __name__ == "__main__":
    main()
