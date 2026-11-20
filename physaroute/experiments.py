"""
Experiment driver: every figure and table of the manuscript is produced from
the CSV files written here (data/*.csv).  Usage:

    python -m physaroute.experiments --exp all --seeds 30 --procs 2
    python -m physaroute.experiments --exp velocity load lifetime ...

Seeds: run s of every cell uses seed = MASTER_SEED + s, so the environment
(body placement, channel realisation, traffic, fades) is identical across
protocols for the same s (common random numbers -> paired statistics).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from . import run_one
from .protocols import PROTOCOLS, ABLATIONS

MASTER_SEED = 20260425
ROOT = Path(os.environ.get("PHYSAROUTE_OUT", str(Path(__file__).resolve().parent.parent)))
DATA = ROOT / "data"

OP = dict(velocity=1.0, load=80.0, duration=200.0, warmup=20.0)   # operating point

VELOCITIES = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
LOADS = [5, 10, 20, 40, 80, 120, 160, 200]
BLE = [0.0, 0.10, 0.25, 0.50]
BLACKHOLE_SETS = [(), (8,), (8, 10), (8, 10, 11)]
OFFCALIB = [3.5, 4.0]

SENS_GRID = {
    "mu": [0.10, 0.20, 0.35],
    "k": [3.0, 5.0, 8.0],          # alpha / mu
    "kappa": [1.0, 2.0, 4.0],
    "gamma": [1.5, 2.0, 3.0],
    "D_min": [0.02, 0.05, 0.15],
    "tau_explore": [3.0, 10.0, 30.0],
    "lambda_E": [0.0, 2.0, 4.0],
    "hold_s": [0.025, 0.05, 0.10],
}
SENS_BASE = dict(mu=0.20, k=5.0, kappa=2.0, gamma=2.0, D_min=0.05, tau_explore=10.0, lambda_E=2.0, hold_s=0.05)


def _job(args):
    exp, cell, cfg = args
    t0 = time.time()
    out = run_one(**cfg)
    out["_runtime_s"] = time.time() - t0
    return exp, cell, out


def _cells(exp, seeds):
    """Yield (cell_dict, run_config_dict) for an experiment."""
    S = range(seeds)
    if exp == "velocity":
        for p in PROTOCOLS:
            for v in VELOCITIES:
                for s in S:
                    yield dict(protocol=p, velocity=v, rep=s), dict(OP, protocol=p, velocity=v, seed=MASTER_SEED + s)
    elif exp == "load":
        for p in PROTOCOLS:
            for L in LOADS:
                for s in S:
                    yield dict(protocol=p, load=L, rep=s), dict(OP, protocol=p, load=float(L), seed=MASTER_SEED + s)
    elif exp == "lifetime":
        for p in PROTOCOLS:
            for s in S:
                yield dict(protocol=p, rep=s), dict(OP, protocol=p, duration=1500.0, energy_sample_s=25.0,
                                                     seed=MASTER_SEED + s)
    elif exp == "ablation":
        for p in ABLATIONS:
            for v in (1.0, 3.0):
                for s in S:
                    yield dict(protocol=p, velocity=v, rep=s), dict(OP, protocol=p, velocity=v, seed=MASTER_SEED + s)
    elif exp == "coexistence":
        for p in PROTOCOLS:
            for a in BLE:
                for s in S:
                    yield dict(protocol=p, ble_airtime=a, rep=s), dict(OP, protocol=p, ble_airtime=a, seed=MASTER_SEED + s)
    elif exp == "blackhole":
        for p in PROTOCOLS + ["PR-noE2E"]:
            for m in BLACKHOLE_SETS:
                for s in S:
                    yield dict(protocol=p, n_malicious=len(m), rep=s), dict(OP, protocol=p, malicious=m, seed=MASTER_SEED + s)
    elif exp == "jamming":
        for p in PROTOCOLS:
            for j in (-1, 8):
                for s in S:
                    yield dict(protocol=p, jam_node=j, rep=s), dict(OP, protocol=p, jam_node=j, seed=MASTER_SEED + s)
    elif exp == "offcalib":
        for p in PROTOCOLS:
            for v in OFFCALIB:
                for s in S:
                    yield dict(protocol=p, velocity=v, rep=s), dict(OP, protocol=p, velocity=v, seed=MASTER_SEED + s)
    elif exp == "icu":
        for p in PROTOCOLS:
            for s in S:
                yield dict(protocol=p, rep=s), dict(OP, protocol=p, duration=600.0, alarm_rate=0.2, seed=MASTER_SEED + s)
    elif exp == "sensitivity":
        n = min(seeds, 10)
        def kw_of(name, val):
            d = dict(SENS_BASE)
            if name != "base":
                d[name] = val
            kw = dict(mu=d["mu"], alpha=d["k"] * d["mu"], kappa=d["kappa"], gamma=d["gamma"], D_min=d["D_min"],
                      tau_explore=d["tau_explore"], lambda_E=d["lambda_E"], hold_s=d["hold_s"])
            return kw
        for v in (1.0, 3.0):
            for s in range(n):
                yield dict(param="base", value=np.nan, velocity=v, rep=s), dict(OP, protocol="PhysaRoute", velocity=v,
                                                                              proto_kw=kw_of("base", None), seed=MASTER_SEED + s)
            for name, vals in SENS_GRID.items():
                for val in vals:
                    if val == SENS_BASE[name]:
                        continue
                    for s in range(n):
                        yield dict(param=name, value=val, velocity=v, rep=s), dict(OP, protocol="PhysaRoute", velocity=v,
                                                                                proto_kw=kw_of(name, val), seed=MASTER_SEED + s)
    elif exp == "convergence":
        for node in (9, 0):
            yield dict(protocol="PhysaRoute", trace_node=node, rep=0), dict(OP, protocol="PhysaRoute", duration=120.0,
                                                                            trace_node=node, seed=MASTER_SEED)
    else:
        raise KeyError(exp)


SCALAR_KEYS = None


def run_experiment(exp, seeds=30, procs=2):
    DATA.mkdir(parents=True, exist_ok=True)
    cells = list(_cells(exp, seeds))
    print(f"[{exp}] {len(cells)} runs", flush=True)
    path = DATA / f"{exp}.csv"
    extra = {}
    t0 = time.time()
    rows = []
    with Pool(procs) as pool:
        for k, (e, cell, out) in enumerate(pool.imap_unordered(_job, [(exp, c, cfg) for c, cfg in cells], chunksize=1)):
            row = dict(cell)
            for kk, vv in out.items():
                if kk.startswith("_"):
                    extra.setdefault(kk, []).append((cell, vv))
                else:
                    row[kk] = vv
            rows.append(row)
            if (k + 1) % 50 == 0 or k + 1 == len(cells):
                el = time.time() - t0
                print(f"[{exp}] {k + 1}/{len(cells)}  {el / 60:.1f} min elapsed, "
                      f"~{el / (k + 1) * (len(cells) - k - 1) / 60:.1f} min left", flush=True)
    keys = []
    for r in rows:
        for kk in r:
            if kk not in keys:
                keys.append(kk)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    # side files
    if "_energy_trace" in extra:
        with open(DATA / "energy_trace.csv", "w", newline="") as f:
            w = csv.writer(f); w.writerow(["protocol", "seed", "time_s", "residual_frac", "alive"])
            for cell, tr in extra["_energy_trace"]:
                for t, e, n in tr:
                    w.writerow([cell["protocol"], cell["rep"], round(t, 3), e, n])
    if "_dead_times" in extra and exp == "lifetime":
        with open(DATA / "dead_times.csv", "w", newline="") as f:
            w = csv.writer(f); w.writerow(["protocol", "seed", "order", "time_s"])
            for cell, dt in extra["_dead_times"]:
                for i, t in enumerate(dt):
                    w.writerow([cell["protocol"], cell["rep"], i + 1, t])
    if "_trace" in extra:
        with open(DATA / "convergence_trace.csv", "w", newline="") as f:
            w = csv.writer(f); w.writerow(["node", "time_s", "link", "conductance"])
            for cell, tr in extra["_trace"]:
                for t, D in tr:
                    for j, d in D.items():
                        w.writerow([cell["trace_node"], round(t, 3), j, d])
    print(f"[{exp}] done in {(time.time() - t0) / 60:.1f} min -> {path}", flush=True)


ALL = ["velocity", "load", "lifetime", "ablation", "coexistence", "blackhole", "jamming", "offcalib", "icu",
       "sensitivity", "convergence"]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", nargs="+", default=["all"])
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args(argv)
    exps = ALL if a.exp == ["all"] else a.exp
    for e in exps:
        run_experiment(e, a.seeds, a.procs)


if __name__ == "__main__":
    main()
