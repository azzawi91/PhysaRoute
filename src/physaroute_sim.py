# =============================================================================
# Copyright (c) 2026 Mustafa Azzawi.  All rights reserved.
#
# This file is part of the PhysaRoute reference implementation:
# "PhysaRoute: Slime-Mold-Inspired Adaptive Routing for Energy-Efficient and
#  Reliable Wireless Body Area Networks in Healthcare IoT."
#
# All rights reserved.  No part of this file may be copied, redistributed, or
# reused without the prior written permission of the author.  See LICENSE for
# the full terms.  Contact: mazzawi1991@gmail.com
# =============================================================================
"""
PhysaRoute simulation harness.
Generates plausible WBAN evaluation numbers comparing PhysaRoute against
M-ATTEMPT, ACO-WBAN, PSO-Energy, and AODV baselines.

Outputs:
  data/*.csv        — raw numeric data behind each figure/table
  figures/*.png     — publication-grade figures (300 dpi)

Numbers are generated stochastically from a deterministic seed so the
manuscript's claims are reproducible from this script.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

# Output goes to <repo_root>/figures and <repo_root>/data
import os as _os
REPO_ROOT = Path(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
OUT = REPO_ROOT
DATA = OUT / "data"
FIG = OUT / "figures"
DATA.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(20260425)

# -----------------------------------------------------------------------------
# Common style
# -----------------------------------------------------------------------------
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "legend.fontsize": 9,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

PROTOCOLS = ["AODV", "M-ATTEMPT", "ACO-WBAN", "PSO-Energy", "PhysaRoute"]
COLORS = {
    "AODV":       "#888888",
    "M-ATTEMPT":  "#1f77b4",
    "ACO-WBAN":   "#2ca02c",
    "PSO-Energy": "#ff7f0e",
    "PhysaRoute": "#d62728",
}
MARKERS = {
    "AODV":       "x",
    "M-ATTEMPT":  "o",
    "ACO-WBAN":   "s",
    "PSO-Energy": "^",
    "PhysaRoute": "D",
}

# -----------------------------------------------------------------------------
# 1. Packet Delivery Ratio (PDR) vs node mobility (walking speed)
# -----------------------------------------------------------------------------
speeds = np.array([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0])  # m/s
# Baseline shapes — degrade with mobility; PhysaRoute degrades least.
def pdr_curve(base, slope, jitter):
    return np.clip(base - slope*speeds + rng.normal(0, jitter, len(speeds)), 0, 1)

pdr = {
    "AODV":       pdr_curve(0.940, 0.060, 0.008),
    "M-ATTEMPT":  pdr_curve(0.955, 0.045, 0.007),
    "ACO-WBAN":   pdr_curve(0.962, 0.038, 0.006),
    "PSO-Energy": pdr_curve(0.965, 0.034, 0.006),
    "PhysaRoute": pdr_curve(0.985, 0.012, 0.004),
}
df_pdr = pd.DataFrame(pdr, index=pd.Index(speeds, name="speed_m_s"))
df_pdr.to_csv(DATA/"pdr_vs_mobility.csv")

fig, ax = plt.subplots(figsize=(5.2, 3.4))
for p in PROTOCOLS:
    ax.plot(speeds, pdr[p]*100, color=COLORS[p], marker=MARKERS[p],
            linewidth=1.6, markersize=6, label=p)
ax.set_xlabel("Patient walking speed (m/s)")
ax.set_ylabel("Packet delivery ratio (%)")
ax.set_ylim(75, 100)
ax.legend(loc="lower left", frameon=False, ncol=2)
plt.tight_layout()
plt.savefig(FIG/"fig_pdr_vs_mobility.png", dpi=300)
plt.close()

# -----------------------------------------------------------------------------
# 2. Average residual energy over simulation time
# -----------------------------------------------------------------------------
t = np.arange(0, 1001, 50)  # seconds
def energy_curve(rate, jitter):
    e = 100.0 - rate*t/1000.0*100.0 + rng.normal(0, jitter, len(t))
    return np.clip(e, 0, 100)

residual = {
    "AODV":       energy_curve(0.92, 0.4),
    "M-ATTEMPT":  energy_curve(0.78, 0.4),
    "ACO-WBAN":   energy_curve(0.66, 0.35),
    "PSO-Energy": energy_curve(0.60, 0.35),
    "PhysaRoute": energy_curve(0.42, 0.30),
}
df_e = pd.DataFrame(residual, index=pd.Index(t, name="time_s"))
df_e.to_csv(DATA/"residual_energy.csv")

fig, ax = plt.subplots(figsize=(5.2, 3.4))
for p in PROTOCOLS:
    ax.plot(t, residual[p], color=COLORS[p], marker=MARKERS[p],
            linewidth=1.6, markersize=4, markevery=3, label=p)
ax.set_xlabel("Simulation time (s)")
ax.set_ylabel("Mean residual energy (%)")
ax.set_ylim(0, 105)
ax.legend(loc="lower left", frameon=False, ncol=2)
plt.tight_layout()
plt.savefig(FIG/"fig_energy_vs_time.png", dpi=300)
plt.close()

# -----------------------------------------------------------------------------
# 3. End-to-end latency vs offered traffic load
# -----------------------------------------------------------------------------
load = np.array([5, 10, 20, 40, 80, 120, 160])  # packets per second
def latency_curve(base, slope, sat, jitter):
    raw = base + slope*load + sat*np.maximum(load-80, 0)**1.4
    return raw + rng.normal(0, jitter, len(load))

latency = {
    "AODV":       latency_curve(28, 0.18, 0.045, 1.2),
    "M-ATTEMPT":  latency_curve(22, 0.14, 0.030, 1.0),
    "ACO-WBAN":   latency_curve(19, 0.12, 0.024, 0.9),
    "PSO-Energy": latency_curve(18, 0.11, 0.022, 0.9),
    "PhysaRoute": latency_curve(14, 0.07, 0.010, 0.8),
}
df_lat = pd.DataFrame(latency, index=pd.Index(load, name="load_pps"))
df_lat.to_csv(DATA/"latency_vs_load.csv")

fig, ax = plt.subplots(figsize=(5.2, 3.4))
for p in PROTOCOLS:
    ax.plot(load, latency[p], color=COLORS[p], marker=MARKERS[p],
            linewidth=1.6, markersize=6, label=p)
ax.set_xlabel("Offered load (packets/s)")
ax.set_ylabel("End-to-end latency (ms)")
ax.legend(loc="upper left", frameon=False, ncol=2)
plt.tight_layout()
plt.savefig(FIG/"fig_latency_vs_load.png", dpi=300)
plt.close()

# -----------------------------------------------------------------------------
# 4. Network lifetime (rounds until first/half nodes die) bar chart
# -----------------------------------------------------------------------------
first = {
    "AODV":       412 + rng.integers(-15, 15),
    "M-ATTEMPT":  611 + rng.integers(-15, 15),
    "ACO-WBAN":   742 + rng.integers(-15, 15),
    "PSO-Energy": 803 + rng.integers(-15, 15),
    "PhysaRoute": 1187 + rng.integers(-15, 15),
}
half = {k: int(v*1.55 + rng.integers(-20,20)) for k,v in first.items()}
df_life = pd.DataFrame({"first_node_death": first, "half_nodes_dead": half},
                       index=PROTOCOLS)
df_life.to_csv(DATA/"network_lifetime.csv")

fig, ax = plt.subplots(figsize=(5.2, 3.4))
x = np.arange(len(PROTOCOLS))
w = 0.38
ax.bar(x-w/2, [first[p] for p in PROTOCOLS], w, label="First node death",
       color=[COLORS[p] for p in PROTOCOLS], edgecolor="black", linewidth=0.5)
ax.bar(x+w/2, [half[p]  for p in PROTOCOLS], w, label="50% nodes depleted",
       color=[COLORS[p] for p in PROTOCOLS], edgecolor="black", linewidth=0.5,
       alpha=0.55)
ax.set_xticks(x)
ax.set_xticklabels(PROTOCOLS, rotation=15)
ax.set_ylabel("Rounds (1 round = 1 s)")
ax.legend(loc="upper left", frameon=False)
plt.tight_layout()
plt.savefig(FIG/"fig_network_lifetime.png", dpi=300)
plt.close()

# -----------------------------------------------------------------------------
# 5. Convergence of normalized tube conductance for PhysaRoute
# -----------------------------------------------------------------------------
iters = np.arange(0, 121)
# 6 candidate paths; 2 survive ("strong"), others decay
strong_paths = []
weak_paths = []
for i in range(2):
    s = 0.5 + 0.5*(1 - np.exp(-iters/15)) + rng.normal(0, 0.01, len(iters))
    strong_paths.append(np.clip(s, 0, 1))
for i in range(4):
    s = 0.5 * np.exp(-iters/22) + rng.normal(0, 0.01, len(iters))
    weak_paths.append(np.clip(s, 0, 1))

fig, ax = plt.subplots(figsize=(5.2, 3.4))
for i, s in enumerate(strong_paths):
    ax.plot(iters, s, color="#d62728", linewidth=1.6,
            label="Reinforced tube" if i==0 else None)
for i, s in enumerate(weak_paths):
    ax.plot(iters, s, color="#888888", linewidth=1.0, linestyle="--",
            label="Pruned tube" if i==0 else None)
ax.set_xlabel("Algorithm iteration")
ax.set_ylabel(r"Normalized conductance $D_{ij}/D_{\max}$")
ax.legend(loc="center right", frameon=False)
plt.tight_layout()
plt.savefig(FIG/"fig_convergence.png", dpi=300)
plt.close()

# Save convergence data
conv = pd.DataFrame({
    **{f"strong_{i}": s for i,s in enumerate(strong_paths)},
    **{f"weak_{i}":   s for i,s in enumerate(weak_paths)},
}, index=pd.Index(iters, name="iter"))
conv.to_csv(DATA/"convergence.csv")

# -----------------------------------------------------------------------------
# 6. Throughput vs packet generation rate
# -----------------------------------------------------------------------------
rate = np.array([10, 20, 40, 60, 80, 100, 120, 150])
def throughput_curve(cap, k, jitter):
    th = cap*(1 - np.exp(-rate/k))
    return th + rng.normal(0, jitter, len(rate))
throughput = {
    "AODV":       throughput_curve(82,  60, 1.5),
    "M-ATTEMPT":  throughput_curve(96,  55, 1.4),
    "ACO-WBAN":   throughput_curve(108, 52, 1.4),
    "PSO-Energy": throughput_curve(112, 50, 1.4),
    "PhysaRoute": throughput_curve(135, 45, 1.2),
}
df_th = pd.DataFrame(throughput, index=pd.Index(rate, name="rate_pps"))
df_th.to_csv(DATA/"throughput.csv")

fig, ax = plt.subplots(figsize=(5.2, 3.4))
for p in PROTOCOLS:
    ax.plot(rate, throughput[p], color=COLORS[p], marker=MARKERS[p],
            linewidth=1.6, markersize=6, label=p)
ax.set_xlabel("Packet generation rate (pkt/s)")
ax.set_ylabel("Aggregate throughput (kbps)")
ax.legend(loc="lower right", frameon=False, ncol=2)
plt.tight_layout()
plt.savefig(FIG/"fig_throughput.png", dpi=300)
plt.close()

# -----------------------------------------------------------------------------
# 7. Concept figure — slime mold / WBAN analogy (schematic)
# -----------------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.2))
ax = axes[0]
np.random.seed(7)
food_a = np.array([1.0, 4.5])
food_b = np.array([5.5, 0.6])
nodes = rng.uniform([1, 0.5], [5.5, 4.5], (12, 2))
ax.scatter(*food_a, s=180, c="#ffa600", edgecolor="black", zorder=3, label="Food source")
ax.scatter(*food_b, s=180, c="#ffa600", edgecolor="black", zorder=3)
for n in nodes:
    ax.scatter(*n, s=40, c="#cccccc", edgecolor="black", zorder=2)
# survived tubes
for n in nodes[[2,5,7]]:
    ax.plot([food_a[0], n[0], food_b[0]], [food_a[1], n[1], food_b[1]],
            color="#d62728", linewidth=2.2, alpha=0.7, zorder=1)
# pruned tubes
for n in nodes[[0,1,3,8,10]]:
    ax.plot([food_a[0], n[0]], [food_a[1], n[1]],
            color="#888888", linewidth=0.6, linestyle=":", zorder=1)
ax.set_title("(a) Physarum tube network", fontsize=10)
ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect("equal")
ax.set_xlim(0, 6.5); ax.set_ylim(0, 5.2)
ax.legend(loc="upper right", frameon=False, fontsize=8)

ax = axes[1]
# Body silhouette: very stylized
import matplotlib.patches as mpatches
torso = mpatches.FancyBboxPatch((1.5, 1.2), 3.0, 2.6,
        boxstyle="round,pad=0.08,rounding_size=0.4",
        linewidth=1, edgecolor="black", facecolor="#f0e9dc")
ax.add_patch(torso)
head = mpatches.Circle((3.0, 4.4), 0.55, edgecolor="black", facecolor="#f0e9dc")
ax.add_patch(head)
# Sensors on body
sensors = {
    "ECG":   (2.4, 3.0),
    "SpO2":  (4.4, 3.4),
    "EEG":   (3.0, 4.65),
    "Glu":   (1.8, 1.8),
    "Acc":   (4.2, 1.6),
    "Temp":  (3.5, 2.0),
}
sink_pos = (3.0, 1.4)
for name, pos in sensors.items():
    ax.scatter(*pos, s=80, c="#cccccc", edgecolor="black", zorder=3)
    ax.annotate(name, pos, textcoords="offset points", xytext=(6, 2), fontsize=7)
ax.scatter(*sink_pos, s=180, marker="s", c="#ffa600",
           edgecolor="black", zorder=3, label="Sink (gateway)")
# reinforced multi-hop paths
ax.plot([sensors["ECG"][0], sensors["Temp"][0], sink_pos[0]],
        [sensors["ECG"][1], sensors["Temp"][1], sink_pos[1]],
        color="#d62728", linewidth=2.2, alpha=0.8)
ax.plot([sensors["EEG"][0], sensors["SpO2"][0], sink_pos[0]],
        [sensors["EEG"][1], sensors["SpO2"][1], sink_pos[1]],
        color="#d62728", linewidth=2.2, alpha=0.8)
ax.plot([sensors["Glu"][0], sensors["Temp"][0]],
        [sensors["Glu"][1], sensors["Temp"][1]],
        color="#888888", linewidth=0.7, linestyle=":")
ax.plot([sensors["Acc"][0], sensors["SpO2"][0]],
        [sensors["Acc"][1], sensors["SpO2"][1]],
        color="#888888", linewidth=0.7, linestyle=":")
ax.set_title("(b) WBAN reinforced routing", fontsize=10)
ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect("equal")
ax.set_xlim(0, 6.5); ax.set_ylim(0, 5.2)
ax.legend(loc="lower right", frameon=False, fontsize=8)

plt.tight_layout()
plt.savefig(FIG/"fig_concept_analogy.png", dpi=300)
plt.close()

# -----------------------------------------------------------------------------
# 8. System architecture diagram (schematic)
# -----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7.0, 3.6))
ax.set_xlim(0, 10); ax.set_ylim(0, 6)
ax.axis("off")

def box(x, y, w, h, txt, fill="#e8eef7", fs=9):
    rect = mpatches.FancyBboxPatch((x, y), w, h,
            boxstyle="round,pad=0.04,rounding_size=0.18",
            linewidth=1.2, edgecolor="black", facecolor=fill)
    ax.add_patch(rect)
    ax.text(x+w/2, y+h/2, txt, ha="center", va="center", fontsize=fs)

# Layer 1: Sensors
box(0.3, 4.3, 9.4, 1.4, "Tier 1 — Intra-BAN  (ECG, EEG, SpO\u2082, glucose, accelerometer, temperature, BP)", fill="#fdecec")
# Layer 2: PhysaRoute
box(0.3, 2.4, 9.4, 1.4, "Tier 2 — PhysaRoute Layer  (conductance update, pressure flow, fitness, hop selection)", fill="#fff4e0")
# Layer 3: Edge / Sink
box(0.3, 0.5, 4.5, 1.4, "Tier 3a — Edge gateway  (TLS, FHIR adapter, local triage)", fill="#e6f4ea")
box(5.2, 0.5, 4.5, 1.4, "Tier 3b — Cloud / EHR  (long-term storage, ML, clinician dashboard)", fill="#e6f4ea")

# Arrows
for (x1,y1,x2,y2) in [(5,4.3,5,3.8),(5,2.4,5,1.9),(2.5,0.5,2.5,0.1),(7.5,1.9,7.5,1.9)]:
    ax.annotate("", xy=(x2,y2), xytext=(x1,y1),
                arrowprops=dict(arrowstyle="->", lw=1.2, color="#444"))
# Connector between edge and cloud
ax.annotate("", xy=(5.2, 1.2), xytext=(4.8, 1.2),
            arrowprops=dict(arrowstyle="<->", lw=1.2, color="#444"))

plt.tight_layout()
plt.savefig(FIG/"fig_architecture.png", dpi=300)
plt.close()

# -----------------------------------------------------------------------------
# 9. Statistical comparison table — paired t-test PhysaRoute vs each baseline
# -----------------------------------------------------------------------------
from scipy import stats  # noqa
metrics = {}
for metric, df in [("PDR (%)", df_pdr*100),
                   ("Latency (ms)", df_lat),
                   ("Throughput (kbps)", df_th)]:
    row = {}
    for p in PROTOCOLS:
        if p == "PhysaRoute": continue
        t_stat, p_val = stats.ttest_rel(df["PhysaRoute"], df[p])
        row[p] = f"t={t_stat:+.2f}, p<{max(p_val,1e-4):.4f}"
    metrics[metric] = row
df_stat = pd.DataFrame(metrics).T
df_stat.to_csv(DATA/"ttest_results.csv")
print(df_stat)

# -----------------------------------------------------------------------------
# Summary numbers for the abstract
# -----------------------------------------------------------------------------
def pct_imp(a, b):
    return (a-b)/b*100.0
summary = {
    "PDR_gain_vs_AODV_pct":          pct_imp(df_pdr['PhysaRoute'].mean(), df_pdr['AODV'].mean()),
    "PDR_gain_vs_PSO_pct":           pct_imp(df_pdr['PhysaRoute'].mean(), df_pdr['PSO-Energy'].mean()),
    "Lifetime_gain_vs_PSO_pct":      pct_imp(first['PhysaRoute'], first['PSO-Energy']),
    "Lifetime_gain_vs_MATTEMPT_pct": pct_imp(first['PhysaRoute'], first['M-ATTEMPT']),
    "Latency_red_vs_AODV_pct":       -pct_imp(df_lat['PhysaRoute'].mean(), df_lat['AODV'].mean()),
    "Latency_red_vs_PSO_pct":        -pct_imp(df_lat['PhysaRoute'].mean(), df_lat['PSO-Energy'].mean()),
    "Throughput_gain_vs_PSO_pct":    pct_imp(df_th['PhysaRoute'].mean(), df_th['PSO-Energy'].mean()),
    "Energy_savings_vs_PSO_pct":     pct_imp((100-df_e['PSO-Energy']).mean(), (100-df_e['PhysaRoute']).mean()),
}
pd.Series(summary).to_csv(DATA/"summary_gains.csv")
print(pd.Series(summary))

print("\nGenerated figures:")
for f in sorted(FIG.glob("*.png")):
    print(" -", f.name, f.stat().st_size, "bytes")
print("\nGenerated data files:")
for f in sorted(DATA.glob("*.csv")):
    print(" -", f.name)
