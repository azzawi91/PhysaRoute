# PhysaRoute — Physarum conductance dynamics for routing in healthcare WBANs

> **© 2026 Mustafa Azzawi. All rights reserved.** Contact: mazzawi1991@gmail.com.
> Licence: see [LICENSE](LICENSE) — reading and reproduction grant; no redistribution without permission.

PhysaRoute is a routing sub-layer for IEEE 802.15.6 wireless body area networks (WBANs) in which every
candidate link keeps a scalar *conductance* that is reinforced by the flow it carries and decays otherwise —
the tube dynamic of the slime mould *Physarum polycephalum* (Tero *et al.*, Science 2010) made executable on a
body-worn microcontroller. This repository contains the complete discrete-event simulator, the protocol,
eight baseline protocols implemented from their original descriptions, the experiment driver, the statistics
and the figure pipeline. **Every figure and number in the accompanying article is reproduced by `make`.**

## What is in the box

| Component | File |
| --- | --- |
| Body channel (IEEE 802.15.6 CM3 + dynamic fading + posture fades), PHY timing, BER/PER, radio energy | [`physaroute/channel.py`](physaroute/channel.py) |
| Discrete-event engine: traffic, CSMA/CA with user priorities, collisions, ACKs, retransmissions, energy, beacon substrate, end-to-end receipts | [`physaroute/engine.py`](physaroute/engine.py) |
| PhysaRoute and the baselines (AODV, M-ATTEMPT, SIMPLE, ACO-WBAN, PSO-Relay, GWO-Relay, QL-WBAN, QoS-2C) and ablations | [`physaroute/protocols.py`](physaroute/protocols.py) |
| Experiment driver (all sweeps, 30 paired seeds per cell) | [`physaroute/experiments.py`](physaroute/experiments.py) |
| Paired statistics: bootstrap CIs, Cohen's *d_z*, Wilcoxon, Holm–Bonferroni | [`physaroute/stats.py`](physaroute/stats.py) |
| Figures | [`physaroute/plots.py`](physaroute/plots.py) |
| Manuscript numbers as LaTeX macros (text cannot drift from data) | [`physaroute/report_numbers.py`](physaroute/report_numbers.py) |
| Parameter files (mirrors of the defaults in code) | [`params/`](params/) |
| Design notes: simulator, baselines, figures | [`docs/`](docs/) |
| Unit tests | [`tests/`](tests/) |

## One-command reproduction

```bash
git clone https://github.com/azzawi91/PhysaRoute.git
cd PhysaRoute
make            # install → test → simulate (≈2 h on 2 cores) → stats → figures → numbers.tex
```

Individual steps:

```bash
make install    # pip install -r requirements.txt
make test       # pytest tests/
make simulate   # python -m physaroute.experiments --exp all --seeds 30 --procs 2
make stats      # python -m physaroute.stats
make figures    # python -m physaroute.plots
make numbers    # python -m physaroute.report_numbers
make quick      # a 3-seed smoke run of every experiment (≈10 min)
```

Outputs: `data/*.csv` (one row per run), `data/summary_*.csv` and `data/stats_*.csv` (aggregates and paired
tests), `figures/*.pdf|png`, `manuscript/shared/numbers.tex`.

## Simulator in one paragraph

Twelve body-worn sensors and a belt-worn gateway (positions, criticality and traffic weights in
`channel.SENSORS`). The channel is the IEEE 802.15.6 CM3 model at 2.4 GHz (a = 6.6, b = 36.1, σ = 3.8 dB,
TG6 channel-model document) plus a 12 dB around-the-body penalty for links crossing the torso or head, an
AR(1) dynamic component whose standard deviation (1–6 dB) and coherence time (2 s → 50 ms) depend on walking
speed, and posture-driven deep fades of 10–35 dB. The PHY is the 971.4 kb/s π/4-DQPSK + BCH(63,51) narrowband
mode with the differential-detection BER; the MAC is CSMA/CA with the standard's per-priority contention
windows, carrier sensing, collisions, immediate ACKs and retransmissions; energy is airtime × nRF52840 radio
current. All protocols share a beacon substrate (gateway beacon every 2 s, re-broadcast once per node) that
gives hop counts, neighbour RSSI and residual energy. Runs are paired: run *r* of every protocol uses the same
environment seed (`20260425 + r`) for placement, channel, fades, packet arrivals and alarm events. See
[`docs/SIMULATOR.md`](docs/SIMULATOR.md), [`docs/BASELINES.md`](docs/BASELINES.md) and [`docs/FIGURES.md`](docs/FIGURES.md).

## Running a single simulation

```python
from physaroute import run_one
r = run_one(protocol="PhysaRoute", velocity=1.0, load=80.0, duration=200.0, seed=20260425)
print(r["pdr"], r["lat_median_ms"], r["energy_mean_mJ"])
```

`RunConfig` (in `engine.py`) lists every knob: speed, load, duration, energy budget, BLE interferer airtime,
jammed node, black-hole relays, alarm rate, a trace node whose conductances are logged every window, and an
optional externally measured path-loss trace (`channel_trace`, windows × nodes × nodes, dB) that replaces
the parametric dynamics.

## Requirements

Python ≥ 3.10 with NumPy, SciPy, pandas, Matplotlib, PyYAML and pytest (`requirements.txt`). Tested on
Ubuntu 22.04 / Python 3.11. NumPy linked against different BLAS libraries may differ in the last digits of some
aggregates; no reported conclusion depends on those digits.

## Citing

See [`CITATION.cff`](CITATION.cff).
