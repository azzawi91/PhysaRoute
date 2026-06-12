# PhysaRoute — Step-by-Step Usage Guide

This guide walks you from a clean clone to a fully reproduced set of figures and CSV tables. End-to-end runtime on a modern laptop is roughly five minutes (most of which is the one-time dependency install).

> **© 2026 Mustafa Azzawi. All rights reserved.** See [`../LICENSE`](../LICENSE).

---

## Table of contents

1. [Prerequisites](#1-prerequisites)
2. [Clone and install](#2-clone-and-install)
3. [Calibrate the channel](#3-calibrate-the-channel)
4. [Run the simulator](#4-run-the-simulator)
5. [Generate figures](#5-generate-figures)
6. [Reproduce a specific figure or table](#6-reproduce-a-specific-figure-or-table)
7. [Seed list](#7-seed-list)
8. [Parameter files](#8-parameter-files)
9. [Troubleshooting](#9-troubleshooting)
10. [What each file does](#10-what-each-file-does)

---

## 1. Prerequisites

| Tool | Minimum | Tested | Install on Ubuntu |
| --- | --- | --- | --- |
| Python | 3.10 | 3.12 | `sudo apt install python3 python3-pip` |
| `make` (optional) | 4.3 | 4.4 | `sudo apt install make` |

On Windows the simplest path is **WSL2 with Ubuntu 22.04 LTS**; every command below works unchanged.

---

## 2. Clone and install

```bash
git clone https://github.com/azzawi91/PhysaRoute.git
cd PhysaRoute

make install
# equivalent to:
python3 -m pip install -r requirements.txt
```

Sanity check:

```bash
python3 -c "import numpy, scipy, matplotlib, yaml, pandas; print('python OK')"
```

---

## 3. Calibrate the channel

```bash
make calibrate
```

This runs `src/calibrate_channel.py`, which:

1. Reads `params/simulation.yaml`.
2. Computes σ_S(v) for v ∈ {0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0} m/s by linear interpolation between the σ_S = 1.8 dB (static) and σ_S = 5.6 dB (3 m/s motion) anchor points from the IEEE 802.15.6 reference document.
3. Generates the received-SNR CDF at each velocity using 5,000 samples.
4. Writes `data/calibration.csv` with columns `velocity_mps, sigma_S_dB, snr_dB, cdf`.

The calibration step exists independently of the simulator so reviewers can audit the channel-model assumptions in isolation.

---

## 4. Run the simulator

```bash
make simulate
```

This runs `src/physaroute_sim_v2.py`, which:

1. Seeds the RNG with `params/seeds.csv`'s master seed `20260425`.
2. Builds the 12-node simulated body-area network and runs all nine protocols (PhysaRoute + 8 baselines) plus four PhysaRoute ablation variants.
3. Sweeps the operating-point grid described in `params/simulation.yaml`.
4. Writes one CSV per experiment to `data/`.

Total wall-clock time: ≈ 5 s.

---

## 5. Generate figures

```bash
make figures
```

This runs `src/plot_figures.py`, which reads the CSVs in `data/` and writes 300-dpi PNGs to `figures/`. The figure pipeline is intentionally separate from the simulator so you can:

- Restyle the figures without re-running the simulation.
- Regenerate a single figure quickly during a polish pass.
- Audit the visual logic independently from the numerical logic.

---

## 6. Reproduce a specific figure or table

To regenerate a single figure:

```bash
python3 src/plot_figures.py --only pdr           # → figures/fig_pdr_vs_mobility.png
python3 src/plot_figures.py --only ablation
python3 src/plot_figures.py --only coexistence
python3 src/plot_figures.py --only sybil
python3 src/plot_figures.py --only failure
python3 src/plot_figures.py --only calibration
```

The full list of `--only` values: `pdr`, `energy`, `latency`, `throughput`, `lifetime`, `convergence`, `ablation`, `coexistence`, `sybil`, `failure`, `calibration`, `all`.

---

## 7. Seed list

`params/seeds.csv` documents every random seed used in the manuscript:

| Experiment | offset_base | n_seeds |
| --- | --- | --- |
| pdr_vs_mobility | 0 | 30 |
| residual_energy | 30 | 30 |
| network_lifetime | 60 | 30 |
| latency_vs_load | 90 | 30 |
| convergence | 120 | 30 |
| throughput | 150 | 30 |
| ablation | 200 | 30 |
| coexistence_0pct ... coexistence_75pct | 300, 330, 360, 390 | 30 each |
| failure_3_0mps ... failure_4_0mps | 420, 450, 480 | 30 each |
| sybil_0pct ... sybil_30pct | 500, 510, 520, 530 | 30 each |
| jamming_node7 | 540 | 30 |
| effect_sizes | 0 (shares pdr_vs_mobility) | 30 |

The actual per-run seed is `master_seed + offset_base + cell_index` where `cell_index` runs 0..29.

---

## 8. Parameter files

Three YAML files in `params/` capture every tunable:

- **`physaroute.yaml`** — μ, α, γ, β_1..β_4, θ, τ, τ_explore, D_min, and the L_ψ / ρ / δ_F constants used by the convergence analysis.
- **`simulation.yaml`** — channel model, calibration anchors, CR2032 budget, sensor count, sweeps.
- **`baselines.yaml`** — every parameter for the eight baseline protocols.

If a number in the paper does not have a parameter-file counterpart, it is a derived quantity. Open an issue if you find a mismatch.

---

## 9. Troubleshooting

### `ModuleNotFoundError: No module named 'yaml'`

Run `python3 -m pip install -r requirements.txt`. On PEP-668-marked systems append `--break-system-packages`, or create a virtual environment first.

### `make: command not found` on Windows native

Use WSL2, or invoke each step manually:

```bash
python3 src/calibrate_channel.py
python3 src/physaroute_sim_v2.py
python3 src/plot_figures.py
```

### Empty figures / blank PNGs

Ensure `make simulate` finished without traceback. If your Matplotlib backend complains, set `MPLBACKEND=Agg` before re-running.

### Slightly different numbers from the manuscript

NumPy linked against MKL vs OpenBLAS will diverge in the fifth significant figure. The headline conclusions hold either way. Pin `numpy==1.26.4` and use the Linux x86-64 wheel for bit-identical reproduction.

---

## 10. What each file does

### `src/calibrate_channel.py`
Implements the IEEE 802.15.6 CM3 on-body shadowing calibration. Inputs: `params/simulation.yaml`. Outputs: `data/calibration.csv` and (via `plot_figures.py`) `figures/fig_calibration.png`.

### `src/physaroute_sim_v2.py`
The event-driven simulator. Implements PhysaRoute and eight baselines under a shared channel, energy, and seed regime. Outputs eleven CSVs to `data/`.

### `src/plot_figures.py`
Reads CSVs from `data/`, writes 300-dpi PNGs to `figures/`. Supports per-figure regeneration via `--only`.

### `Makefile`
The single entry point promised in the manuscript's data-availability statement. Targets: `install`, `calibrate`, `simulate`, `figures`, `clean`, `all`, `help`.

---

If a step does not behave as described, file an issue on GitHub or email mazzawi1991@gmail.com with OS, Python version, and the exact failing command.

**All rights reserved.**
