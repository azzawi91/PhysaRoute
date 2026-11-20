"""
Statistical post-processing of the experiment CSVs.

Paired design: run r of every protocol shares the same environment seed, so
PhysaRoute-vs-baseline differences are paired by r.  For each metric we report
the mean paired difference, a bootstrap 95 % CI, the paired t statistic,
Cohen's d_z (paired form), the Wilcoxon signed-rank p-value, and Holm-Bonferroni
adjusted p-values over the whole family of comparisons.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as st

ROOT = Path(os.environ.get("PHYSAROUTE_OUT", str(Path(__file__).resolve().parent.parent)))
DATA = ROOT / "data"

METRICS = {  # metric: (column, higher_is_better, label, unit)
    "pdr": ("pdr", True, "Packet delivery ratio", ""),
    "lat_median": ("lat_median_ms", False, "Median latency", "ms"),
    "lat_p95": ("lat_p95_ms", False, "95th-pct latency", "ms"),
    "energy": ("energy_mean_mJ", False, "Mean energy / node", "mJ"),
    "energy_max": ("energy_max_mJ", False, "Max energy / node", "mJ"),
    "ctrl": ("ctrl_bytes_per_delivered", False, "Control bytes / delivered pkt", "B"),
}


def bootstrap_ci(x, n=5000, seed=0):
    rng = np.random.default_rng(seed)
    x = np.asarray(x, dtype=float)
    m = rng.choice(x, (n, len(x)), replace=True).mean(1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def holm(pvals):
    p = np.asarray(pvals, dtype=float)
    m = len(p)
    order = np.argsort(p)
    adj = np.empty(m)
    running = 0.0
    for rank, idx in enumerate(order):
        val = (m - rank) * p[idx]
        running = max(running, val)
        adj[idx] = min(1.0, running)
    return adj


def paired_table(df, ref="PhysaRoute", metrics=METRICS, key="rep"):
    """df: rows = (protocol, rep, metrics...) at one operating point."""
    rows = []
    prot = [p for p in df["protocol"].unique() if p != ref]
    for mname, (col, hib, label, unit) in metrics.items():
        a = df[df.protocol == ref].set_index(key)[col]
        for p in prot:
            b = df[df.protocol == p].set_index(key)[col]
            idx = a.index.intersection(b.index)
            x = a.loc[idx].values.astype(float); y = b.loc[idx].values.astype(float)
            d = x - y if hib else y - x            # positive = PhysaRoute better
            ok = np.isfinite(d)
            d = d[ok]
            if len(d) < 3:
                continue
            t, pt = st.ttest_1samp(d, 0.0)
            try:
                w, pw = st.wilcoxon(d, zero_method="wilcox")
            except ValueError:
                pw = np.nan
            lo, hi = bootstrap_ci(d)
            dz = d.mean() / d.std(ddof=1) if d.std(ddof=1) > 0 else np.inf
            rows.append(dict(metric=mname, label=label, unit=unit, baseline=p, n=len(d),
                             ref_mean=float(np.nanmean(x[ok])), base_mean=float(np.nanmean(y[ok])),
                             mean_diff=float(d.mean()), ci_lo=lo, ci_hi=hi, t=float(t), p_raw=float(pt),
                             wilcoxon_p=float(pw), cohens_dz=float(dz)))
    out = pd.DataFrame(rows)
    if len(out):
        out["p_holm"] = holm(out["p_raw"].values)
        out["significant_holm_0.05"] = out["p_holm"] < 0.05
    return out


def summary_by(df, by, cols):
    g = df.groupby(by)[cols]
    m = g.mean(); s = g.std(ddof=1); n = g.count()
    ci = 1.96 * s / np.sqrt(n)
    out = m.copy()
    for c in cols:
        out[c + "_ci95"] = ci[c]
        out[c + "_n"] = n[c]
    return out.reset_index()


def main():
    vel = pd.read_csv(DATA / "velocity.csv")
    op = vel[np.isclose(vel.velocity, 1.0)]
    tab = paired_table(op)
    tab.to_csv(DATA / "stats_operating_point.csv", index=False)
    # add lifetime and throughput comparisons when available
    extra = []
    if (DATA / "lifetime.csv").exists():
        lt = pd.read_csv(DATA / "lifetime.csv")
        extra.append(paired_table(lt, metrics={"fnd": ("fnd_s", True, "Time to first node death", "s")}))
    if (DATA / "load.csv").exists():
        ld = pd.read_csv(DATA / "load.csv")
        hi = ld[ld.load == ld.load.max()]
        extra.append(paired_table(hi, metrics={"thr": ("throughput_kbps", True, "Saturation throughput", "kb/s")}))
    if extra:
        full = pd.concat([tab] + extra, ignore_index=True)
        full["p_holm"] = holm(full["p_raw"].values)
        full["significant_holm_0.05"] = full["p_holm"] < 0.05
        full.to_csv(DATA / "stats_all.csv", index=False)
    # high-mobility operating point
    hm = vel[np.isclose(vel.velocity, 3.0)]
    paired_table(hm).to_csv(DATA / "stats_high_mobility.csv", index=False)
    # per-cell summaries
    cols = ["pdr", "lat_mean_ms", "lat_median_ms", "lat_p95_ms", "throughput_kbps", "energy_mean_mJ",
            "energy_max_mJ", "ctrl_frames_per_s", "ctrl_bytes_per_delivered", "retx_ratio", "mean_hops"]
    summary_by(vel, ["protocol", "velocity"], cols).to_csv(DATA / "summary_velocity.csv", index=False)
    for name, by in (("load", ["protocol", "load"]), ("coexistence", ["protocol", "ble_airtime"]),
                     ("blackhole", ["protocol", "n_malicious"]), ("jamming", ["protocol", "jam_node"]),
                     ("offcalib", ["protocol", "velocity"]), ("ablation", ["protocol", "velocity"]),
                     ("sensitivity", ["param", "value", "velocity"])):
        f = DATA / f"{name}.csv"
        if f.exists():
            d = pd.read_csv(f)
            c = [x for x in cols if x in d.columns]
            summary_by(d, by, c).to_csv(DATA / f"summary_{name}.csv", index=False)
    if (DATA / "lifetime.csv").exists():
        lt = pd.read_csv(DATA / "lifetime.csv")
        summary_by(lt, ["protocol"], ["fnd_s", "dead_count", "pdr", "energy_mean_mJ", "energy_max_mJ"]).to_csv(
            DATA / "summary_lifetime.csv", index=False)
    if (DATA / "icu.csv").exists():
        icu = pd.read_csv(DATA / "icu.csv")
        g = icu.groupby("protocol")
        out = pd.DataFrame({
            "alarms": g["alarms"].sum(), "missed": g["alarms_missed"].sum(),
            "missed_per_1000": 1000.0 * g["alarms_missed"].sum() / g["alarms"].sum(),
            "alarm_lat_median_ms": g["alarm_lat_median_ms"].median(),
            "alarm_lat_p95_ms": g["alarm_lat_p95_ms"].median(),
            "pdr_alarm": g["pdr_alarm"].mean(), "pdr_crit": g["pdr_crit"].mean(), "pdr_data": g["pdr_data"].mean(),
            "energy_mean_mJ": g["energy_mean_mJ"].mean(),
        }).reset_index()
        out.to_csv(DATA / "summary_icu.csv", index=False)
    print("stats written to", DATA)


if __name__ == "__main__":
    main()
