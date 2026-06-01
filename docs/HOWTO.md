# PhysaRoute — Step-by-Step Usage Guide

This guide takes you from a fresh clone to a fully reproduced set of figures and CSV tables. Allow ~5 minutes on a modern laptop.

> **© 2026 Mustafa Azzawi. All rights reserved.** See [`../LICENSE`](../LICENSE).

---

## Table of contents

1. [Prerequisites](#1-prerequisites)
2. [Clone and install](#2-clone-and-install)
3. [Run the simulator (figures + CSV)](#3-run-the-simulator)
4. [Reproduce specific figures or tables](#4-reproduce-specific-figures-or-tables)
5. [Seed list](#5-seed-list)
6. [Troubleshooting](#6-troubleshooting)
7. [What each file does](#7-what-each-file-does)

---

## 1. Prerequisites

| Tool | Minimum | Tested with | Install on Ubuntu |
| --- | --- | --- | --- |
| Python | 3.10 | 3.12 | `sudo apt install python3 python3-pip` |
| `make` (optional) | GNU Make 4.3 | 4.4 | `sudo apt install make` |

On Windows, the simplest path is **WSL2 with Ubuntu 22.04 LTS** — every command below works unchanged. Native Windows works too if you have Python installed; just substitute `\` for `/` in paths.

---

## 2. Clone and install

```bash
git clone https://github.com/mazzawi/physaroute.git
cd physaroute/practical

# One-shot install of Python dependencies:
make install

# Equivalent manual command:
python3 -m pip install -r requirements.txt
```

`make install` is idempotent — safe to re-run after `git pull`.

### Sanity check

```bash
python3 -c "import numpy, scipy, matplotlib, pandas; print('python OK')"
```

Should print `python OK`.

---

## 3. Run the simulator

```bash
make simulate
```

This calls `python3 src/physaroute_sim.py`, which:

1. Seeds the RNG with master seed `20260425`.
2. Builds the 12-node simulated WBAN topology.
3. Runs all protocols (PhysaRoute, AODV, M-ATTEMPT, ACO-WBAN, GWO-WBAN, PSO-Energy, DARE-IoT, PZ-2021, RL-WBAN) for 30 seeded runs each, at the operating-point grid.
4. Writes the eight publication figures into `figures/` (300 dpi PNG).
5. Writes the eight CSV datasets into `data/`.

### Expected runtime

| Hardware | Wall-clock |
| --- | --- |
| Apple M2 Pro | ~ 4 min |
| Intel i7-12700 (8P+4E) | ~ 5 min |
| GitHub Actions `ubuntu-latest` | ~ 9 min |

### Expected outputs

After `make simulate` you should see:

```
figures/
├── fig_pdr_vs_mobility.png       (≈ 80 KB)
├── fig_energy_vs_time.png        (≈ 85 KB)
├── fig_latency_vs_load.png       (≈ 80 KB)
├── fig_network_lifetime.png      (≈ 75 KB)
├── fig_convergence.png           (≈ 70 KB)
├── fig_throughput.png            (≈ 75 KB)
├── fig_concept_analogy.png       (≈ 110 KB)
└── fig_architecture.png          (≈ 95 KB)

data/
├── pdr_vs_mobility.csv
├── residual_energy.csv
├── latency_vs_load.csv
├── network_lifetime.csv
├── convergence.csv
├── throughput.csv
├── ttest_results.csv
└── summary_gains.csv
```

If any file is missing, see [Troubleshooting](#6-troubleshooting).

---

## 4. Reproduce specific figures or tables

| Figure or table | Command | Source file |
| --- | --- | --- |
| Fig. 4 — PDR vs mobility | `python3 src/physaroute_sim.py --only pdr` | `pdr_vs_mobility.csv` |
| Fig. 5 — Residual energy | `python3 src/physaroute_sim.py --only energy` | `residual_energy.csv` |
| Fig. 6 — Network lifetime | `python3 src/physaroute_sim.py --only lifetime` | `network_lifetime.csv` |
| Fig. 7 — Latency vs load | `python3 src/physaroute_sim.py --only latency` | `latency_vs_load.csv` |
| Fig. 8 — Convergence | `python3 src/physaroute_sim.py --only convergence` | `convergence.csv` |
| Fig. 9 — Throughput | `python3 src/physaroute_sim.py --only throughput` | `throughput.csv` |
| Table III — Paired t-tests | `python3 src/physaroute_sim.py --only stats` | `ttest_results.csv` |
| Table IV — ICU 72-hour | `python3 src/physaroute_sim.py --only clinical` | (computed inline) |

The `--only` flags are documented in the simulator's `--help`. Running with no flag (`make simulate`) reproduces everything.

---

## 5. Seed list

Every result uses the master seed `20260425`. Each experiment consumes 30 derived seeds:

| Experiment | Seeds (master + offset) |
| --- | --- |
| Fig. 4 — PDR vs mobility | 0 – 29 |
| Fig. 5 — Residual energy | 30 – 59 |
| Fig. 6 — Network lifetime | 60 – 89 |
| Fig. 7 — Latency vs load | 90 – 119 |
| Fig. 8 — Convergence | 120 – 149 |
| Fig. 9 — Throughput | 150 – 179 |
| Table III — Paired t-test | 0 – 29 |
| Table IV — ICU 72-hour | 180 – 209 |
| Extended baselines | 210 – 239 |
| Effect sizes / Holm correction | 0 – 29, 180 – 209 |

To reproduce a single seed for debugging:

```bash
python3 src/physaroute_sim.py --seed 20260425 --offset 12
```

---

## 6. Troubleshooting

### `ModuleNotFoundError: No module named 'numpy'` (or scipy, matplotlib, pandas)

Run `python3 -m pip install -r requirements.txt`. On PEP-668-marked systems (Debian 12+, Ubuntu 24.04+) add `--break-system-packages` or use a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Empty figures or all-zero CSVs

Check that the simulator finished without traceback:

```bash
python3 src/physaroute_sim.py 2>&1 | tail -30
```

If the simulator finished but the figures are blank, your Matplotlib backend may need to be set:

```bash
export MPLBACKEND=Agg
make simulate
```

### `Permission denied` writing to `figures/` or `data/`

The folders are created by the simulator on first run. If they exist but are read-only, fix permissions:

```bash
chmod -R u+rw figures/ data/
```

### Figures match but numbers differ slightly

Floating-point reproducibility across BLAS implementations: NumPy linked against MKL versus OpenBLAS will diverge in the 5th significant figure. The headline conclusions are robust to this.

---

## 7. What each file does

### `src/physaroute_sim.py`
The event-driven WBAN simulator. Implements:
- IEEE 802.15.6 CM3 on-body channel model (path loss, log-normal shadowing).
- CR2032 daily-budget energy accounting (`E_tx = L_pkt (E_elec + ε_amp d^k)`).
- PhysaRoute conductance update with softmax forwarding.
- The seven baseline protocols.
- The figure-generation and CSV-writing logic.

---

If you find a step that does not work as described, please open an issue or email mazzawi1991@gmail.com with the OS, Python version, and the exact failing command.

**All rights reserved.**
