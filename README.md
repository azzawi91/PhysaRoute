# PhysaRoute — Reference Implementation

**Slime-Mold–Inspired Adaptive Routing for Energy-Efficient and Reliable Wireless Body Area Networks in Healthcare IoT**

Reference implementation and simulator for the PhysaRoute adaptive routing protocol. The simulator reproduces every figure and statistical table presented in the accompanying research work from a single master seed.

> **© 2026 Mustafa Azzawi. All rights reserved.**
> Contact: mazzawi1991@gmail.com
> See [LICENSE](LICENSE) for the full terms — this is **not** an open-source release; reuse requires the author's written permission.

---

## What is in this repository

| Folder | What it contains |
| --- | --- |
| `src/` | The Python event-driven WBAN simulator (`physaroute_sim.py`) that produces every figure and CSV reported in the research. |
| `docs/` | Step-by-step usage guide ([`HOWTO.md`](docs/HOWTO.md)). |
| `figures/` | Output target for figures (PNG, 300 dpi). Git-ignored. |
| `data/` | Output target for CSV data and statistical tables. Git-ignored. |
| `CITATION.cff` | GitHub-rendered citation metadata. |
| `Makefile` | One-command build (`make` → install + simulate). |

---

## Quick start

```bash
git clone https://github.com/mazzawi/physaroute.git
cd physaroute/practical

make                 # install deps + run the simulator
# or, individually:
make install         # install Python dependencies
make simulate        # run the simulator → figures/ and data/
make clean           # wipe generated artefacts
```

For a guided walkthrough see [docs/HOWTO.md](docs/HOWTO.md).

---

## What the simulator reproduces

The PhysaRoute conductance-update dynamic is benchmarked against eight WBAN routing baselines on a 12-node simulated body network under the IEEE 802.15.6 CM3 channel:

| Metric | PhysaRoute gain |
| --- | --- |
| Packet delivery ratio | **+13.6 %** over AODV; +3.8 % over the strongest baseline (averaged across 0–3 m/s mobility) |
| Time to first node death | **1.96 ×** over M-ATTEMPT; 1.21 × over RL-WBAN |
| End-to-end latency | **−30 to −56 %** depending on offered load |
| Saturation throughput | **+25.8 %** over PSO-Energy |
| Convergence to ε-optimal | **≈ 7 s** (analytical) / 6.4 ± 0.7 s (empirical) |
| ICU VT alarm latency | **480 ms → 220 ms**, within IEC 60601-2-27 envelope |

All numbers are reproducible from clean using the master seed `20260425`; the full 30-seed table is in `docs/HOWTO.md`.

---

## How to cite

If you reference the work, please cite the research:

> Mustafa Azzawi, "PhysaRoute: Slime-Mold-Inspired Adaptive Routing for Energy-Efficient and Reliable Wireless Body Area Networks in Healthcare IoT," 2026.

GitHub will render the citation widget from [`CITATION.cff`](CITATION.cff).

---

## Repository structure

```
practical/
├── README.md                      ← you are here
├── LICENSE                        ← All Rights Reserved
├── CITATION.cff                   ← GitHub citation widget
├── Makefile                       ← one-command build
├── requirements.txt               ← Python deps
├── .gitignore
│
├── docs/
│   └── HOWTO.md                   ← step-by-step usage
│
├── src/
│   └── physaroute_sim.py          ← the simulator
│
├── figures/                       ← simulator output (gitignored)
└── data/                          ← simulator output (gitignored)
```

---

## Requirements

| Tool | Version | Purpose |
| --- | --- | --- |
| Python | ≥ 3.10 | Simulator + analysis pipeline |
| `make` (optional) | GNU Make 4.x | One-command build wrapper |

Tested on Ubuntu 22.04, macOS 14, and Windows 11 + WSL2.

---

## Reporting issues

Issues should be filed on the GitHub tracker (once the repo is public) or by email to mazzawi1991@gmail.com. Please include:

- Operating system + Python version.
- The exact command that failed.
- The stack trace or last 30 lines of stdout.

---

**All rights reserved.** No portion of this repository may be copied, modified, redistributed, or incorporated into another work without the author's prior written permission.
