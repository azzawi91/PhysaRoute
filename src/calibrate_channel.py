#!/usr/bin/env python3
# =============================================================================
# Copyright (c) 2026 Mustafa Azzawi.  All rights reserved.
#
# calibrate_channel.py — IEEE 802.15.6 CM3 on-body 2.4 GHz channel calibration.
#
# Anchors the simulator's shadowing standard deviation σ_S(v) to the publicly
# cited values of Yazdandoost & Sayrafian-Pour, "Channel Model for Body Area
# Network (BAN)," IEEE 802.15-08-0780-12, 2010:
#
#     σ_S = 1.8 dB during static posture
#     σ_S = 5.6 dB during 3 m/s motion
#
# This script reads params/simulation.yaml, computes σ_S(v) for v ∈ [0, 3] m/s,
# generates the received-SNR cumulative-distribution-function curves used in
# the manuscript's Appendix D figure, and writes the curves to
# data/calibration.csv.  It can also be imported as a library.
#
# Used by the experiment-reproduction Makefile (`make calibrate`).
#
# All rights reserved.  See LICENSE.
# =============================================================================
import os
import sys
import csv
from pathlib import Path
import numpy as np

try:
    import yaml
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False


HERE      = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
PARAMS    = REPO_ROOT / "params" / "simulation.yaml"
DATA_OUT  = REPO_ROOT / "data" / "calibration.csv"
DATA_OUT.parent.mkdir(parents=True, exist_ok=True)

VELOCITY_GRID = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
SNR_GRID_dB   = np.linspace(-10.0, 30.0, 200)
SNR_SAMPLES   = 5000


def load_params(path=PARAMS):
    """Read simulation.yaml. Returns a dict with the keys this script needs."""
    if HAVE_YAML and path.exists():
        with open(path) as f:
            cfg = yaml.safe_load(f)
        return cfg
    # Fallback: hard-code the values published in the manuscript.
    return {
        "shadowing_sigma_static_dB": 1.8,
        "shadowing_sigma_motion_dB": 5.6,
        "velocity_max_mps":          3.0,
        "master_seed":               20260425,
    }


def shadowing_sigma_dB(velocity_m_s, *, sigma_static=1.8, sigma_motion=5.6,
                       v_max=3.0):
    """
    Linearly interpolate σ_S(v) between the two anchor points reported by
    Yazdandoost & Sayrafian-Pour 2010 (Table 8).  Outside the [0, v_max]
    envelope the value is clipped — Appendix C of the manuscript explicitly
    flags this as the failure-case regime.
    """
    v = max(0.0, min(v_max, float(velocity_m_s)))
    return sigma_static + (sigma_motion - sigma_static) * (v / v_max)


def received_snr_cdf(velocity_m_s, snr_grid_dB, *, n_samples=SNR_SAMPLES,
                     mean_snr_dB=12.0, rng=None, **sigma_kwargs):
    """
    Returns the empirical CDF of the received SNR (in dB) at a given walking
    speed, under a reference mean of 12 dB and the calibrated σ_S(v).
    """
    if rng is None:
        rng = np.random.default_rng(20260425 + int(velocity_m_s * 10))
    sigma = shadowing_sigma_dB(velocity_m_s, **sigma_kwargs)
    samples = mean_snr_dB - rng.normal(0.0, sigma, n_samples)
    return np.array([float(np.mean(samples <= x)) for x in snr_grid_dB])


def main():
    cfg = load_params()
    sigma_static = float(cfg.get("shadowing_sigma_static_dB", 1.8))
    sigma_motion = float(cfg.get("shadowing_sigma_motion_dB", 5.6))
    v_max        = float(cfg.get("velocity_max_mps", 3.0))
    master_seed  = int(cfg.get("master_seed", 20260425))

    print(f"calibrating CM3 shadowing:")
    print(f"  σ_S(static) = {sigma_static} dB")
    print(f"  σ_S(motion) = {sigma_motion} dB")
    print(f"  v_max       = {v_max} m/s")
    print(f"  master seed = {master_seed}")

    sigmas, cdfs = {}, {}
    for v in VELOCITY_GRID:
        sigmas[v] = shadowing_sigma_dB(v, sigma_static=sigma_static,
                                       sigma_motion=sigma_motion, v_max=v_max)
        rng = np.random.default_rng(master_seed + int(v * 100))
        cdfs[v] = received_snr_cdf(v, SNR_GRID_dB,
                                    rng=rng,
                                    sigma_static=sigma_static,
                                    sigma_motion=sigma_motion,
                                    v_max=v_max)
        print(f"  v = {v:.1f} m/s → σ_S = {sigmas[v]:.2f} dB")

    # Write data/calibration.csv
    with open(DATA_OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["velocity_mps", "sigma_S_dB", "snr_dB", "cdf"])
        for v in VELOCITY_GRID:
            for snr, c in zip(SNR_GRID_dB, cdfs[v]):
                w.writerow([f"{v:.2f}", f"{sigmas[v]:.4f}",
                            f"{snr:.4f}",  f"{c:.6f}"])
    print(f"wrote {DATA_OUT}")


if __name__ == "__main__":
    sys.exit(main())
