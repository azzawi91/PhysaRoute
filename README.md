# PhysaRoute — Reference Implementation

**Slime-Mold–Inspired Adaptive Routing for Energy-Efficient and Reliable Wireless Body Area Networks in Healthcare IoT**

Reference implementation, simulator, and manuscript-build pipeline accompanying the IEEE Internet of Things Journal (IoTJ) submission.

> **© 2026 Mustafa Mazzawi. All rights reserved.**
> Contact: mazzawi1991@gmail.com
> See [LICENSE](LICENSE) for the full terms — this is **not** an open-source release; reuse requires the author's written permission.

---

## What is in this repository

| Folder | What it contains |
| --- | --- |
| `src/` | The Python event-driven WBAN simulator (`physaroute_sim.py`) that produces every figure and CSV reported in the paper. |
| `manuscript/` | Node + Python pipeline that assembles the manuscript `.docx` from typed sections and figures, plus the scripts that apply the reviewer revisions. |
| `latex/` | The IEEE IoTJ LaTeX template (`PhysaRoute_IEEE_IoTJ_Template.tex`) and its bibliography (`PhysaRoute.bib`). |
| `docs/` | Step-by-step usage guide ([`HOWTO.md`](docs/HOWTO.md)). |
| `figures/` | Output target for figures (PNG, 300 dpi). Git-ignored. |
| `data/` | Output target for CSV data and statistical tables. Git-ignored. |
| `CITATION.cff` | GitHub-rendered citation metadata. |
| `Makefile` | One-command build (`make` → install + simulate + paper). |

---

## Quick start

```bash
git clone https://github.com/mazzawi/physaroute.git
cd physaroute/practical

make                 # install deps + simulate + build the docx paper
# or, individually:
make install         # pip + npm dependencies
make simulate        # run the simulator → figures/ and data/
make paper           # assemble the .docx manuscript
make latex           # (optional) build the IEEE PDF via pdflatex
```

For a guided walkthrough see [docs/HOWTO.md](docs/HOWTO.md).

---

## Headline results (reproducible by `make simulate`)

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

If you reference the work, please cite the manuscript:

> Mustafa Mazzawi, "PhysaRoute: Slime-Mold-Inspired Adaptive Routing for Energy-Efficient and Reliable Wireless Body Area Networks in Healthcare IoT," *IEEE Internet of Things Journal*, 2026 (under review).

A BibTeX entry is in [`latex/PhysaRoute.bib`](latex/PhysaRoute.bib); GitHub will render the citation widget from [`CITATION.cff`](CITATION.cff).

---

## Repository structure

```
practical/
├── README.md                      ← you are here
├── LICENSE                        ← All Rights Reserved
├── CITATION.cff                   ← GitHub citation widget
├── Makefile                       ← one-command build
├── requirements.txt               ← Python deps
├── package.json                   ← Node deps (docx generator)
├── .gitignore
│
├── docs/
│   └── HOWTO.md                   ← step-by-step usage
│
├── src/
│   └── physaroute_sim.py          ← the simulator
│
├── manuscript/
│   ├── build_paper.js             ← top-level docx assembler
│   ├── build_paper_part1.js       ← docx helpers
│   ├── build_paper_main.js        ← front matter + Sections I–VI
│   ├── build_paper_part2.js       ← Sections VII–XI + references
│   ├── revise_manuscript.py       ← appends Appendices A–J to original docx
│   ├── integrate_revisions.py     ← in-lines reviewer fixes into body
│   ├── cleanup_revisions.py       ← removes redundant Addendum block
│   ├── appendix_f_fix.py          ← stale-sentence cleanup
│   ├── build_response.py          ← Response-to-Reviewers cover letter
│   ├── input/                     ← place source .docx files here
│   └── output/                    ← assembled .docx written here
│
├── latex/
│   ├── PhysaRoute_IEEE_IoTJ_Template.tex
│   └── PhysaRoute.bib
│
├── figures/                       ← simulator output (gitignored)
└── data/                          ← simulator output (gitignored)
```

---

## Requirements

| Tool | Version | Purpose |
| --- | --- | --- |
| Python | ≥ 3.10 | Simulator + Python-side build scripts |
| Node.js | ≥ 18 | `docx` package for assembling the `.docx` manuscript |
| TeX Live | 2022+ | Optional — only needed for `make latex` |
| `IEEEtran` | latest | Optional — `tlmgr install ieeetran` |

Tested on Ubuntu 22.04, macOS 14, and Windows 11 + WSL2.

---

## Reporting issues

Issues should be filed on the GitHub tracker (once the repo is public) or by email to mazzawi1991@gmail.com. Please include:

- Operating system + Python / Node versions.
- The exact command that failed.
- The stack trace or last 30 lines of stdout.

---

**All rights reserved.** No portion of this repository may be copied, modified, redistributed, or incorporated into another work without the author's prior written permission. The only exception is the limited reading-and-execution grant extended to IEEE IoTJ peer reviewers for the purpose of verifying the published results.
