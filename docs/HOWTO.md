# PhysaRoute — Step-by-Step Usage Guide

This guide takes you from a fresh clone to a fully reproduced manuscript with figures, tables, and the IEEE-typeset PDF. Allow ~10 minutes for the full pipeline on a modern laptop.

> **© 2026 Mustafa Mazzawi. All rights reserved.** See [`../LICENSE`](../LICENSE).

---

## Table of contents

1. [Prerequisites](#1-prerequisites)
2. [Clone and install](#2-clone-and-install)
3. [Run the simulator (figures + CSV)](#3-run-the-simulator)
4. [Assemble the manuscript (Word .docx)](#4-assemble-the-manuscript-word-docx)
5. [Apply the reviewer revisions](#5-apply-the-reviewer-revisions)
6. [Build the IEEE LaTeX PDF](#6-build-the-ieee-latex-pdf)
7. [Reproduce specific figures or tables](#7-reproduce-specific-figures-or-tables)
8. [Seed list](#8-seed-list)
9. [Troubleshooting](#9-troubleshooting)
10. [What each file does](#10-what-each-file-does)

---

## 1. Prerequisites

| Tool | Minimum | Tested with | Install on Ubuntu |
| --- | --- | --- | --- |
| Python | 3.10 | 3.12 | `sudo apt install python3 python3-pip` |
| Node.js | 18 | 22 | `curl -fsSL https://deb.nodesource.com/setup_22.x \| sudo -E bash -` then `sudo apt install nodejs` |
| `make` | — | GNU Make 4.3 | `sudo apt install make` |
| (optional) TeX Live | 2022 | 2024 | `sudo apt install texlive-latex-extra texlive-fonts-recommended texlive-publishers` |

On Windows, the simplest path is **WSL2 with Ubuntu 22.04 LTS** — every command below works unchanged. Native Windows works too if you have Python and Node installed; just substitute `\` for `/` in paths.

---

## 2. Clone and install

```bash
git clone https://github.com/mazzawi/physaroute.git
cd physaroute/practical

# One-shot install of Python + Node dependencies:
make install

# Equivalent manual commands:
python3 -m pip install -r requirements.txt
npm install
```

`make install` is idempotent — safe to re-run after `git pull`.

### Sanity check

```bash
python3 -c "import numpy, scipy, matplotlib, docx; print('python OK')"
node -e "require('docx'); console.log('node OK')"
```

Both should print the corresponding `OK` message.

---

## 3. Run the simulator

```bash
make simulate
```

This calls `python3 src/physaroute_sim.py`, which:

1. Seeds the RNG with master seed `20260425`.
2. Builds the 12-node simulated WBAN topology (Section VII-A of the paper).
3. Runs all eight protocols (PhysaRoute, AODV, M-ATTEMPT, ACO-WBAN, GWO-WBAN, PSO-Energy, DARE-IoT, PZ-2021, RL-WBAN) for 30 seeded runs each, at the operating point grid of the paper.
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

If any file is missing, see [Troubleshooting](#9-troubleshooting).

---

## 4. Assemble the manuscript (Word .docx)

```bash
make paper
```

This calls `node manuscript/build_paper.js`, which:

1. Loads the eight figures from `figures/` (they must exist — run `make simulate` first).
2. Concatenates the four section files (`build_paper_part1.js`, `build_paper_main.js`, `build_paper_part2.js`) under the orchestrator (`build_paper.js`).
3. Writes the assembled docx to `manuscript/output/PhysaRoute_IEEE_IoTJ_Manuscript.docx`.

### Manual invocation

```bash
cd manuscript
node build_paper.js
# → output/PhysaRoute_IEEE_IoTJ_Manuscript.docx
```

The output is a two-column journal layout, Times New Roman 10 pt, US Letter, 1-inch top/bottom and 0.75-inch left/right margins, with the IEEE running footer.

---

## 5. Apply the reviewer revisions

The revision pipeline is in `manuscript/` and runs in three stages:

```bash
cd manuscript

# Stage 1 — append Appendices A through J to the original draft.
# Source : input/PhysaRoute_IEEE_IoTJ_Manuscript - Last versrion.docx
# Output : output/PhysaRoute_IEEE_IoTJ_Manuscript_R1.docx
python3 revise_manuscript.py

# Stage 2 — integrate reviewer fixes into the body text and remove the
#           Addendum block.
# Source : output/PhysaRoute_IEEE_IoTJ_Manuscript_R1.docx
# Output : output/PhysaRoute_IEEE_IoTJ_Manuscript_Submission.docx
python3 integrate_revisions.py

# Stage 3 — second-pass cleanup of the Appendices (drop the stale
#           Appendix F sentence, remove the response-to-reviewer matrix
#           from Appendix J).
# Edits   : output/PhysaRoute_IEEE_IoTJ_Manuscript_Submission.docx in-place
python3 cleanup_revisions.py
python3 appendix_f_fix.py
```

### Generate the response-to-reviewers cover letter

```bash
python3 build_response.py
# → output/PhysaRoute_Response_to_Reviewers.docx
```

### Putting the source `.docx` files in place

Before running stage 1 you must place the original "Last version" `.docx` in `manuscript/input/`. The script will fail with a clear `FileNotFoundError` if it cannot find it. The reviewer report `.docx` is **not** needed by these scripts — it is consumed by the cover-letter pipeline indirectly.

---

## 6. Build the IEEE LaTeX PDF

```bash
make latex
```

This calls the four-step `pdflatex → bibtex → pdflatex → pdflatex` cycle on `latex/PhysaRoute_IEEE_IoTJ_Template.tex` and writes `latex/PhysaRoute_IEEE_IoTJ_Template.pdf`.

The template is pre-populated with the abstract, IEEE keywords, equations, Algorithm 1, the appendix scaffold, and the bibliography call to `PhysaRoute.bib`. Each section body carries a `% TEMPLATE NOTE:` comment pointing back to the corresponding section of the assembled `.docx` — paste the prose between the section header and the next `% TEMPLATE NOTE:` to finalize the manuscript.

### Manual invocation

```bash
cd latex
pdflatex PhysaRoute_IEEE_IoTJ_Template
bibtex   PhysaRoute_IEEE_IoTJ_Template
pdflatex PhysaRoute_IEEE_IoTJ_Template
pdflatex PhysaRoute_IEEE_IoTJ_Template
```

The double `pdflatex` after `bibtex` is required to resolve forward references.

---

## 7. Reproduce specific figures or tables

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

## 8. Seed list

Every result in the paper uses the master seed `20260425`. Each experiment consumes 30 derived seeds:

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
| Appendix B — Extended baselines | 210 – 239 |
| Appendix D — Effect sizes | 0 – 29, 180 – 209 |

To reproduce a single seed for debugging:

```bash
python3 src/physaroute_sim.py --seed 20260425 --offset 12
```

---

## 9. Troubleshooting

### `ModuleNotFoundError: No module named 'docx'`

Run `python3 -m pip install -r requirements.txt`. On PEP-668-marked systems (Debian 12+, Ubuntu 24.04+) add `--break-system-packages` or use a virtual environment.

### `Error: Cannot find module 'docx'` (Node)

Run `npm install` inside `practical/`.

### `pdflatex: command not found`

Only required for `make latex`. The docx-only pipeline (`make simulate && make paper`) does not need TeX.

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

### Figures match the paper but numbers differ slightly

Floating-point reproducibility across BLAS implementations: NumPy linked against MKL versus OpenBLAS will diverge in the 5th significant figure. The headline conclusions (every digit reported in the paper) are robust to this.

---

## 10. What each file does

### `src/physaroute_sim.py`
The event-driven WBAN simulator. Implements:
- IEEE 802.15.6 CM3 on-body channel model (path loss, log-normal shadowing).
- CR2032 daily-budget energy accounting (`E_tx = L_pkt (E_elec + ε_amp d^k)`).
- PhysaRoute conductance update with softmax forwarding.
- The seven baseline protocols.
- The figure-generation and CSV-writing logic.

### `manuscript/build_paper_part1.js`
The docx-helper library: `p()`, `h1()`, `eq()`, `image()`, `tableCell()`, font registration, etc. Used by the other build scripts.

### `manuscript/build_paper_main.js`
Section text for the front matter (title, author, abstract, index terms) and Sections I–VI as `Paragraph[]` arrays. The hardest part of the codebase to modify; do small edits and run `node -c` to syntax-check.

### `manuscript/build_paper_part2.js`
Sections VII–XI plus the 45-entry IEEE-format reference list.

### `manuscript/build_paper.js`
The top-level orchestrator: imports the three parts, creates the document object with two-column journal page setup and IEEE footer, writes the `.docx`.

### `manuscript/revise_manuscript.py`
Stage 1 of the revision pipeline. Opens the original `.docx`, completes the truncated sentences in Sections VII-A, VII-C, VIII-G, appends Appendices A–J, and saves as `..._R1.docx`.

### `manuscript/integrate_revisions.py`
Stage 2. Walks every `w:t` element in the docx, applies in-place text substitutions for the abstract, Section VI-A, Section VII-C, Section VIII-F, Section IX heading, the SIMPLE reference, etc., and removes the Addendum block.

### `manuscript/cleanup_revisions.py` + `manuscript/appendix_f_fix.py`
Stage 3. Polishes the appendices: removes the response-to-reviewer matrix (which lives in the cover letter) and drops a stale sentence in Appendix F.

### `manuscript/build_response.py`
Builds the standalone Response-to-Reviewers cover letter as a separate `.docx`.

### `latex/PhysaRoute_IEEE_IoTJ_Template.tex`
The IEEEtran journal-mode skeleton. Replace the `% TEMPLATE NOTE:` placeholders with the section bodies from the assembled `.docx` to produce the final IEEE PDF.

### `latex/PhysaRoute.bib`
47 BibTeX entries formatted for `IEEEtran.bst`.

---

If you find a step that does not work as described, please open an issue or email mazzawi1991@gmail.com with the OS, Python version, and the exact failing command.

**All rights reserved.**
