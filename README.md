# PhysaRoute — Reproduction Repository

**A Reinforcement-and-Pruning Adaptive Routing Protocol for Healthcare Wireless Body Area Networks.**

> **© 2026 Mustafa Azzawi. All rights reserved.**
> Contact: mazzawi1991@gmail.com
> Licence: see [LICENSE](LICENSE) — peer-review reading grant only; no redistribution.

This repository implements the data-availability statement of the manuscript verbatim: every figure, every table, every reported number in the paper is reproducible from a clean clone by running `make`.

The repository contains, in line with the article's promise:

| What the article promises | Where it lives in this repo |
| --- | --- |
| The complete simulator | [`src/physaroute_sim_v2.py`](src/physaroute_sim_v2.py) |
| The calibration script | [`src/calibrate_channel.py`](src/calibrate_channel.py) |
| The experiment-reproduction Makefile | [`Makefile`](Makefile) |
| Every parameter file | [`params/physaroute.yaml`](params/physaroute.yaml), [`params/baselines.yaml`](params/baselines.yaml), [`params/simulation.yaml`](params/simulation.yaml) |
| The full 30-seed list per experiment | [`params/seeds.csv`](params/seeds.csv) |
| The figure-generation scripts | [`src/plot_figures.py`](src/plot_figures.py) |

---

## One-command reproduction

```bash
git clone https://github.com/azzawi91/PhysaRoute.git
cd PhysaRoute

make                 # install → calibrate → simulate → figures
```

`make` runs the four steps below in order. Each can be run individually if you want to inspect intermediate artefacts:

```bash
make install         # python3 -m pip install -r requirements.txt
make calibrate       # src/calibrate_channel.py → data/calibration.csv
make simulate        # src/physaroute_sim_v2.py → data/*.csv  (≈ 5 s)
make figures         # src/plot_figures.py     → figures/*.png
make clean           # wipe data/ and figures/
```

After `make` finishes you should see eleven publication-quality PNGs in `figures/` and the matching raw-data CSVs in `data/`.

---

## What gets reproduced

The simulator and the figure pipeline together produce:

| Quantity | Source file (in `data/`) | Figure (in `figures/`) |
| --- | --- | --- |
| PDR vs walking speed                          | `pdr_vs_mobility.csv`  | `fig_pdr_vs_mobility.png` |
| Mean residual energy over time                | `residual_energy.csv`  | `fig_energy_vs_time.png` |
| End-to-end latency vs offered load            | `latency_vs_load.csv`  | `fig_latency_vs_load.png` |
| Network lifetime (FND ± SD)                   | `network_lifetime.csv` | `fig_network_lifetime.png` |
| Conductance trajectories (six paths)          | `convergence.csv`      | `fig_convergence.png` |
| Aggregate throughput vs rate                  | `throughput.csv`       | `fig_throughput.png` |
| Four-arm ablation                             | `ablation.csv`         | `fig_ablation.png` |
| Co-existence under BLE interferer             | `coexistence.csv`      | `fig_coexistence.png` |
| Sybil + single-node jamming                   | `sybil.csv`, `jamming.csv` | `fig_sybil_jamming.png` |
| Off-calibrated failure case (v > 3 m/s)       | `failure_case.csv`     | `fig_failure_case.png` |
| Calibrated received-SNR CDF                   | `calibration.csv`      | `fig_calibration.png` |
| Cohen's d + Holm-Bonferroni                   | `effect_sizes.csv`     | (table; rendered in the paper) |

---

## Reproducibility guarantees

- **Master seed**: `20260425`. Every experiment uses 30 derived seeds; the per-cell offsets are listed in [`params/seeds.csv`](params/seeds.csv) alongside the manuscript section that consumes them.
- **Channel calibration**: σ_S(v) is anchored to publicly cited values from the IEEE 802.15.6 reference document (1.8 dB static, 5.6 dB at 3 m/s motion). The [`src/calibrate_channel.py`](src/calibrate_channel.py) script makes this explicit and writes its full CDF to `data/calibration.csv`.
- **Parameters in plain text**: PhysaRoute, simulation environment, and baseline parameters are each in their own YAML file under [`params/`](params/). No "magic numbers" inside the simulator that are not also reflected in those files.
- **No external services**: the pipeline does not contact any network endpoint. Everything runs locally on Python 3.10+ with the four packages listed in [`requirements.txt`](requirements.txt).
- **Float-point ordering**: NumPy linked against MKL versus OpenBLAS will diverge in the fifth significant figure of some metrics. The headline conclusions (every digit reported in the manuscript) are robust to this. If you need bit-identical reproduction, pin `numpy==1.26.4` and use the Linux x86-64 wheel from PyPI.

---

## Folder layout

```
PhysaRoute/
├── README.md                          ← you are here
├── LICENSE                            ← All Rights Reserved, peer-review reading grant
├── CITATION.cff                       ← GitHub citation widget
├── Makefile                           ← experiment-reproduction Makefile
├── requirements.txt                   ← Python dependencies
├── .gitignore
│
├── params/
│   ├── physaroute.yaml                ← PhysaRoute protocol parameters
│   ├── baselines.yaml                 ← eight baseline-protocol parameters
│   ├── simulation.yaml                ← channel, PHY, energy, sweeps
│   └── seeds.csv                      ← 30-seed list per experiment
│
├── src/
│   ├── physaroute_sim.py              ← original simulator (legacy)
│   ├── physaroute_sim_v2.py           ← upgraded simulator (default)
│   ├── calibrate_channel.py           ← shadowing-σ calibration script
│   └── plot_figures.py                ← figure-generation pipeline
│
├── docs/
│   └── HOWTO.md                       ← step-by-step usage guide
│
├── figures/                           ← simulator output (gitignored)
└── data/                              ← simulator output (gitignored)
```

---

## Requirements

| Tool | Minimum | Tested |
| --- | --- | --- |
| Python | 3.10 | 3.10 — 3.12 |
| `make` (optional) | GNU Make 4.x | 4.3 |

The four Python packages we depend on (NumPy, SciPy, Matplotlib, PyYAML, pandas) install in under a minute on every platform we have tested (Ubuntu 22.04, macOS 14, Windows 11 + WSL2).

---

## How to cite

If you use this code, please cite the paper. A `CITATION.cff` is shipped alongside this README so GitHub will render the citation widget automatically.

---

## Reporting issues

Open an issue on the GitHub tracker or email `mazzawi1991@gmail.com`. Please include:

- Operating system and Python version.
- The exact command that failed.
- The last 30 lines of stdout / stderr.

---

**All rights reserved.** This repository is released with a peer-review reading grant only. No portion may be copied, modified, redistributed, or incorporated into another work without prior written permission from the author. See [LICENSE](LICENSE) for the full text.
