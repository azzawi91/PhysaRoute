"""
Generate manuscript/shared/numbers.tex: every number quoted in the manuscript
text is a LaTeX macro computed here from data/*.csv, so text and data cannot
drift apart.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(os.environ.get("PHYSAROUTE_OUT", str(Path(__file__).resolve().parent.parent)))
DATA = ROOT / "data"
OUT = ROOT / "manuscript" / "shared" / "numbers.tex"

ORDER = ["PhysaRoute", "QL-WBAN", "QoS-2C", "ACO-WBAN", "PSO-Relay", "GWO-Relay", "SIMPLE", "M-ATTEMPT", "AODV"]

# LaTeX macro names may not contain digits or hyphens
KEY = {"QoS-2C": "QoSC", "PR-noE2E": "PRnoEE"}


def key(p):
    return KEY.get(p, p.replace("-", ""))


def macro(name, value, fmt="{:.1f}"):
    if isinstance(value, str):
        s = value
    else:
        s = fmt.format(value)
    return f"\\newcommand{{\\{name}}}{{{s}}}\n"


def ci(x):
    x = np.asarray(x, dtype=float); x = x[np.isfinite(x)]
    return 1.96 * x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else np.nan


def main():
    L = []
    vel = pd.read_csv(DATA / "velocity.csv")
    op = vel[np.isclose(vel.velocity, 1.0)]; hi = vel[np.isclose(vel.velocity, 3.0)]
    st = vel[np.isclose(vel.velocity, 0.0)]

    def mean_of(df, p, col):
        return df[df.protocol == p][col].mean()

    for tag, df in (("Op", op), ("Hi", hi), ("St", st)):
        pr = mean_of(df, "PhysaRoute", "pdr")
        base = {p: mean_of(df, p, "pdr") for p in ORDER if p != "PhysaRoute"}
        best = max(base, key=base.get); worst = min(base, key=base.get)
        L.append(macro(f"prPdr{tag}Pct", 100 * pr, "{:.2f}"))
        L.append(macro(f"prPdrGainBest{tag}", 100 * (pr - base[best]), "{:.1f}"))
        L.append(macro(f"prPdrBestBase{tag}", best))
        L.append(macro(f"prPdrBestBase{tag}Pct", 100 * base[best], "{:.2f}"))
        L.append(macro(f"prPdrGainWorst{tag}", 100 * (pr - base[worst]), "{:.1f}"))
        L.append(macro(f"prPdrWorstBase{tag}", worst))
        L.append(macro(f"prPdrWorstBase{tag}Pct", 100 * base[worst], "{:.2f}"))
        for p in ORDER:
            L.append(macro(f"pdr{tag}{key(p)}", 100 * mean_of(df, p, "pdr"), "{:.2f}"))
            L.append(macro(f"latMed{tag}{key(p)}", mean_of(df, p, "lat_median_ms"), "{:.1f}"))
            L.append(macro(f"latMean{tag}{key(p)}", mean_of(df, p, "lat_mean_ms"), "{:.1f}"))
            L.append(macro(f"latPnf{tag}{key(p)}", mean_of(df, p, "lat_p95_ms"), "{:.1f}"))
            L.append(macro(f"energy{tag}{key(p)}", mean_of(df, p, "energy_mean_mJ"), "{:.1f}"))
            L.append(macro(f"energyMax{tag}{key(p)}", mean_of(df, p, "energy_max_mJ"), "{:.1f}"))
            L.append(macro(f"ctrl{tag}{key(p)}", mean_of(df, p, "ctrl_frames_per_s"), "{:.1f}"))
            L.append(macro(f"ctrlB{tag}{key(p)}", mean_of(df, p, "ctrl_bytes_per_delivered"), "{:.1f}"))
            L.append(macro(f"hops{tag}{key(p)}", mean_of(df, p, "mean_hops"), "{:.2f}"))
            L.append(macro(f"retx{tag}{key(p)}", 100 * mean_of(df, p, "retx_ratio"), "{:.1f}"))
        e = {p: mean_of(df, p, "energy_mean_mJ") for p in ORDER}
        eb = min((p for p in ORDER if p != "PhysaRoute"), key=e.get)
        L.append(macro(f"prEnergy{tag}", e["PhysaRoute"], "{:.1f}"))
        L.append(macro(f"prEnergyBestBase{tag}", eb))
        L.append(macro(f"prEnergyGainBestPct{tag}", 100 * (e[eb] - e["PhysaRoute"]) / e[eb], "{:.0f}"))
        L.append(macro(f"prEnergyRank{tag}", str(sorted(ORDER, key=e.get).index("PhysaRoute") + 1)))
        # energy per delivered packet (uJ): 12 sensors x mean energy / delivered packets
        epp = {p: (df[df.protocol == p]["energy_mean_mJ"] * 12.0 / df[df.protocol == p]["delivered"]).mean() * 1e3 for p in ORDER}
        for p in ORDER:
            L.append(macro(f"epp{tag}{key(p)}", epp[p], "{:.1f}"))
        direct = ["M-ATTEMPT", "PSO-Relay", "GWO-Relay"]
        relayers = [p for p in ORDER if p not in direct and p != "PhysaRoute"]
        L.append(macro(f"prEpp{tag}", epp["PhysaRoute"], "{:.1f}"))
        L.append(macro(f"directEpp{tag}", min(epp[p] for p in direct), "{:.1f}"))
        L.append(macro(f"relayerBestEpp{tag}", min(epp[p] for p in relayers), "{:.1f}"))
        L.append(macro(f"relayerBestEppName{tag}", min(relayers, key=lambda p: epp[p])))
        L.append(macro(f"prEppRank{tag}", str(sorted(ORDER, key=lambda p: epp[p]).index("PhysaRoute") + 1)))
        L.append(macro(f"prEppVsDirectPct{tag}", 100 * (epp["PhysaRoute"] - min(epp[p] for p in direct)) / min(epp[p] for p in direct), "{:.0f}"))
        L.append(macro(f"prEnergyVsDirectPct{tag}", 100 * (e["PhysaRoute"] - min(e[p] for p in direct)) / min(e[p] for p in direct), "{:.0f}"))
        for p in ORDER[1:]:
            L.append(macro(f"prPdrGain{tag}{key(p)}", 100 * (pr - base[p]), "{:.1f}"))
            L.append(macro(f"energyVsPrPct{tag}{key(p)}", 100 * (e[p] - e["PhysaRoute"]) / e["PhysaRoute"], "{:+.0f}"))
        lm = {p: mean_of(df, p, "lat_median_ms") for p in ORDER}
        L.append(macro(f"prLatMedVsDirect{tag}", lm["PhysaRoute"] - min(lm[p] for p in direct), "{:.2f}"))
        L.append(macro(f"prLatMed{tag}", lm["PhysaRoute"], "{:.1f}"))
        L.append(macro(f"prLatMean{tag}", mean_of(df, "PhysaRoute", "lat_mean_ms"), "{:.1f}"))
        L.append(macro(f"prLatPnf{tag}", mean_of(df, "PhysaRoute", "lat_p95_ms"), "{:.0f}"))
    # PDR range across all speeds
    g = vel.groupby(["protocol", "velocity"])["pdr"].mean()
    L.append(macro("prPdrMinAll", 100 * g["PhysaRoute"].min(), "{:.1f}"))
    L.append(macro("aodvPdrMinAll", 100 * g["AODV"].min(), "{:.1f}"))
    L.append(macro("mattemptPdrMinAll", 100 * g["M-ATTEMPT"].min(), "{:.1f}"))
    # lifetime
    if (DATA / "lifetime.csv").exists():
        lt = pd.read_csv(DATA / "lifetime.csv")
        f = lt.groupby("protocol")["fnd_s"].mean()
        for p in ORDER:
            L.append(macro(f"fnd{key(p)}", f.get(p, np.nan), "{:.0f}"))
        direct = max(f[["M-ATTEMPT", "SIMPLE"]].to_dict().items(), key=lambda kv: kv[1])
        L.append(macro("fndBestDirect", direct[0]))
        L.append(macro("fndBestDirectVal", direct[1], "{:.0f}"))
        L.append(macro("prFndGapPct", 100 * (direct[1] - f["PhysaRoute"]) / direct[1], "{:.0f}"))
        best_other = max((p for p in ORDER if p != "PhysaRoute"), key=lambda p: f.get(p, -1))
        L.append(macro("fndBestOther", best_other))
        L.append(macro("fndRankPR", str(sorted(ORDER, key=lambda p: -f.get(p, -1)).index("PhysaRoute") + 1)))
        pd_lt = lt.groupby("protocol")["pdr"].mean()
        for p in ORDER:
            L.append(macro(f"pdrLt{key(p)}", 100 * pd_lt.get(p, np.nan), "{:.1f}"))
    # load sweep
    if (DATA / "load.csv").exists():
        ld = pd.read_csv(DATA / "load.csv")
        mx = ld.load.max()
        t = ld[ld.load == mx].groupby("protocol")["throughput_kbps"].mean()
        for p in ORDER:
            L.append(macro(f"thrMax{key(p)}", t.get(p, np.nan), "{:.1f}"))
        L.append(macro("loadMax", mx, "{:.0f}"))
        best_other = max((p for p in ORDER if p != "PhysaRoute"), key=lambda p: t.get(p, -1))
        L.append(macro("thrBestOther", best_other))
        L.append(macro("thrGainPct", 100 * (t["PhysaRoute"] - t[best_other]) / t[best_other], "{:.1f}"))
        ll = ld[ld.load == mx].groupby("protocol")["lat_median_ms"].mean()
        L.append(macro("prLatMedMaxLoad", ll["PhysaRoute"], "{:.1f}"))
        pl = ld[ld.load == mx].groupby("protocol")["pdr"].mean()
        L.append(macro("prPdrMaxLoad", 100 * pl["PhysaRoute"], "{:.1f}"))
        L.append(macro("aodvPdrMaxLoad", 100 * pl["AODV"], "{:.1f}"))
    # ablation
    if (DATA / "ablation.csv").exists():
        ab = pd.read_csv(DATA / "ablation.csv")
        for v, tag in ((1.0, "Op"), (3.0, "Hi")):
            d = ab[np.isclose(ab.velocity, v)].groupby("protocol")
            full = d["pdr"].mean()["PhysaRoute"]
            for var in ("PR-noEnergy", "PR-noShadow", "PR-noCrit", "PR-noExplore"):
                L.append(macro(f"abl{tag}{var.replace('PR-', '')}Pdr", 100 * (d['pdr'].mean()[var] - full), "{:+.2f}"))
                fullE = d["energy_max_mJ"].mean()["PhysaRoute"]
                L.append(macro(f"abl{tag}{var.replace('PR-', '')}Emax", 100 * (d['energy_max_mJ'].mean()[var] - fullE) / fullE, "{:+.0f}"))
                fullL = d["lat_median_ms"].mean()["PhysaRoute"]
                L.append(macro(f"abl{tag}{var.replace('PR-', '')}Lat", 100 * (d['lat_median_ms'].mean()[var] - fullL) / fullL, "{:+.0f}"))
    # coexistence
    if (DATA / "coexistence.csv").exists():
        co = pd.read_csv(DATA / "coexistence.csv")
        g = co.groupby(["protocol", "ble_airtime"])["pdr"].mean()
        for p in ORDER:
            L.append(macro(f"coex{key(p)}Zero", 100 * g[p][0.0], "{:.1f}"))
            L.append(macro(f"coex{key(p)}Half", 100 * g[p][0.5], "{:.1f}"))
            L.append(macro(f"coex{key(p)}Quarter", 100 * g[p][0.25], "{:.1f}"))
            L.append(macro(f"coex{key(p)}Drop", 100 * (g[p][0.0] - g[p][0.5]), "{:.1f}"))
    # blackhole
    if (DATA / "blackhole.csv").exists():
        bh = pd.read_csv(DATA / "blackhole.csv")
        g = bh.groupby(["protocol", "n_malicious"])["pdr"].mean()
        for p in ORDER + ["PR-noE2E"]:
            for n in (0, 1, 2, 3):
                L.append(macro(f"bh{key(p)}{'ZOWT'[n]}", 100 * g[p][n], "{:.1f}"))
    if (DATA / "jamming.csv").exists():
        jm = pd.read_csv(DATA / "jamming.csv")
        g = jm.groupby(["protocol", "jam_node"])["pdr"].mean()
        for p in ORDER:
            L.append(macro(f"jam{key(p)}", 100 * g[p][8], "{:.1f}"))
            L.append(macro(f"jamDrop{key(p)}", 100 * (g[p][-1] - g[p][8]), "{:.1f}"))
    if (DATA / "offcalib.csv").exists():
        oc = pd.read_csv(DATA / "offcalib.csv")
        g = oc.groupby(["protocol", "velocity"])["pdr"].mean()
        for p in ORDER:
            L.append(macro(f"off{key(p)}Four", 100 * g[p][4.0], "{:.1f}"))
    if (DATA / "icu.csv").exists():
        icu = pd.read_csv(DATA / "icu.csv")
        g = icu.groupby("protocol")
        for p in ORDER:
            d = g.get_group(p)
            L.append(macro(f"icuMed{key(p)}", d["alarm_lat_median_ms"].median(), "{:.1f}"))
            L.append(macro(f"icuPnf{key(p)}", d["alarm_lat_p95_ms"].median(), "{:.1f}"))
            L.append(macro(f"icuMiss{key(p)}", 1000.0 * d["alarms_missed"].sum() / d["alarms"].sum(), "{:.2f}"))
            L.append(macro(f"icuAlarms{key(p)}", d["alarms"].sum(), "{:.0f}"))
            L.append(macro(f"icuPdrAlarm{key(p)}", 100 * d["pdr_alarm"].mean(), "{:.2f}"))
            L.append(macro(f"icuMean{key(p)}", d["lat_alarm_ms"].mean(), "{:.1f}"))
            L.append(macro(f"icuMissedCount{key(p)}", d["alarms_missed"].sum(), "{:.0f}"))
    if (DATA / "stats_all.csv").exists():
        stt = pd.read_csv(DATA / "stats_all.csv")
        pdrrows = stt[stt.metric == "pdr"]
        L.append(macro("statsNTests", str(len(stt))))
        L.append(macro("statsNSig", str(int(stt["significant_holm_0.05"].sum()))))
        L.append(macro("statsMinDzPdr", pdrrows["cohens_dz"].min(), "{:.2f}"))
        L.append(macro("statsMaxDzPdr", pdrrows["cohens_dz"].max(), "{:.2f}"))
        L.append(macro("statsMaxPholmPdr", pdrrows["p_holm"].max(), "{:.1e}"))
    if (DATA / "sensitivity.csv").exists():
        se = pd.read_csv(DATA / "sensitivity.csv")
        for v, tag in ((1.0, "Op"), (3.0, "Hi")):
            d = se[np.isclose(se.velocity, v)]
            cells = d.groupby(["param", "value"], dropna=False)["pdr"].mean()
            L.append(macro(f"sensRange{tag}", 100 * (cells.max() - cells.min()), "{:.2f}"))
            base = d[d.param == "base"]["pdr"].mean()
            L.append(macro(f"sensMuHighGain{tag}", 100 * (d[(d.param == "mu") & np.isclose(d.value, 0.35)]["pdr"].mean() - base), "{:.2f}"))
            L.append(macro(f"sensMuLowGain{tag}", 100 * (d[(d.param == "mu") & np.isclose(d.value, 0.10)]["pdr"].mean() - base), "{:.2f}"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(L))
    print("wrote", OUT, len(L), "macros")
    write_tables()


def _fmt_p(p):
    if not np.isfinite(p):
        return "--"
    if p < 1e-4:
        return "$<10^{-4}$"
    return f"{p:.3f}" if p >= 0.001 else f"{p:.1e}"


def write_tables():
    """LaTeX table bodies: paired statistics at the operating point and
    protocol overhead, so that tables and data cannot drift apart."""
    shared = OUT.parent
    vel = pd.read_csv(DATA / "velocity.csv")
    # --- overhead table (v = 1 and 3 m/s) -------------------------------------
    rows = []
    for p in ORDER:
        cells = [p]
        for v in (1.0, 3.0):
            d = vel[np.isclose(vel.velocity, v) & (vel.protocol == p)]
            cells += [f"{d.ctrl_frames_per_s.mean():.1f}", f"{d.ctrl_bytes_per_delivered.mean():.1f}",
                      f"{100 * d.retx_ratio.mean():.1f}", f"{d.mean_hops.mean():.2f}"]
        rows.append(" & ".join(cells) + r" \\")
    (shared / "tab_overhead.tex").write_text("\n".join(rows) + "\n")
    # --- ablation table ----------------------------------------------------------
    f = DATA / "ablation.csv"
    if f.exists():
        ab = pd.read_csv(f)
        variants = [("PhysaRoute", "full protocol"), ("PR-noEnergy", "no energy term ($\\lambda_E=0$)"),
                    ("PR-noShadow", "no shadowing predictor ($\\beta_3=0$)"),
                    ("PR-noCrit", "no criticality terms"), ("PR-noExplore", "no exploration probes")]
        rows = []
        for var, lab in variants:
            cells = [lab]
            for col, fmt, scale in (("pdr", "{:.2f}", 100.0), ("lat_median_ms", "{:.1f}", 1.0), ("energy_max_mJ", "{:.0f}", 1.0)):
                for v in (1.0, 3.0):
                    d = ab[np.isclose(ab.velocity, v) & (ab.protocol == var)][col]
                    cells.append(fmt.format(scale * d.mean()))
            rows.append(" & ".join(cells) + r" \\")
        (shared / "tab_ablation.tex").write_text("\n".join(rows) + "\n")
    # --- paired statistics table -----------------------------------------------
    f = DATA / "stats_all.csv"
    if not f.exists():
        f = DATA / "stats_operating_point.csv"
    if f.exists():
        stt = pd.read_csv(f)
        want = [("pdr", 100.0, "{:+.2f}"), ("lat_p95", 1.0, "{:+.1f}"), ("energy", 1.0, "{:+.1f}"), ("fnd", 1.0, "{:+.0f}")]
        rows = []
        for p in ORDER[1:]:
            cells = [p]
            for m, scale, fmt in want:
                r = stt[(stt.metric == m) & (stt.baseline == p)]
                if len(r) == 0:
                    cells += ["--", "--"]
                    continue
                r = r.iloc[0]
                sig = "" if r["significant_holm_0.05"] else "$^{\\dagger}$"
                cells += [fmt.format(scale * r.mean_diff) + f" [{fmt.format(scale * r.ci_lo)}, {fmt.format(scale * r.ci_hi)}]" + sig,
                          f"{r.cohens_dz:.2f}"]
            rows.append(" & ".join(cells) + r" \\")
        (shared / "tab_stats.tex").write_text("\n".join(rows) + "\n")
    # --- supplementary: high-mobility paired table and full-metric table ---------
    fh = DATA / "stats_high_mobility.csv"
    if fh.exists():
        stt = pd.read_csv(fh)
        want = [("pdr", 100.0, "{:+.2f}"), ("lat_p95", 1.0, "{:+.1f}"), ("energy", 1.0, "{:+.1f}"), ("ctrl", 1.0, "{:+.1f}")]
        rows = []
        for p in ORDER[1:]:
            cells = [p]
            for m, scale, fmt in want:
                r = stt[(stt.metric == m) & (stt.baseline == p)]
                if len(r) == 0:
                    cells += ["--", "--"]
                    continue
                r = r.iloc[0]
                sig = "" if r["significant_holm_0.05"] else "$^{\\dagger}$"
                cells += [fmt.format(scale * r.mean_diff) + f" [{fmt.format(scale * r.ci_lo)}, {fmt.format(scale * r.ci_hi)}]" + sig,
                          f"{r.cohens_dz:.2f}"]
            rows.append(" & ".join(cells) + r" \\")
        (shared / "tab_stats_hi.tex").write_text("\n".join(rows) + "\n")
    fo = DATA / "stats_all.csv"
    if fo.exists():
        stt = pd.read_csv(fo)
        names = {"pdr": ("PDR (pp)", 100.0, "{:+.2f}"), "lat_median": ("Median latency (ms)", 1.0, "{:+.2f}"),
                 "lat_p95": ("95th-pct latency (ms)", 1.0, "{:+.1f}"), "energy": ("Energy / node (mJ)", 1.0, "{:+.1f}"),
                 "energy_max": ("Max energy / node (mJ)", 1.0, "{:+.1f}"), "ctrl": ("Control B / delivered pkt", 1.0, "{:+.1f}"),
                 "fnd": ("FND (s)", 1.0, "{:+.0f}"), "thr": ("Throughput at 200 pkt/s (kb/s)", 1.0, "{:+.1f}")}
        rows = []
        for m, (lab, scale, fmt) in names.items():
            first = True
            for p in ORDER[1:]:
                r = stt[(stt.metric == m) & (stt.baseline == p)]
                if len(r) == 0:
                    continue
                r = r.iloc[0]
                rows.append(" & ".join([lab if first else "", p, fmt.format(scale * r.ref_mean) if m != "pdr" else f"{scale * r.ref_mean:.2f}",
                                        fmt.format(scale * r.base_mean) if m != "pdr" else f"{scale * r.base_mean:.2f}",
                                        fmt.format(scale * r.mean_diff), f"[{fmt.format(scale * r.ci_lo)}, {fmt.format(scale * r.ci_hi)}]",
                                        f"{r.t:.1f}", f"{r.cohens_dz:.2f}", _fmt_p(r.wilcoxon_p), _fmt_p(r.p_holm)]) + r" \\")
                first = False
            rows.append(r"\addlinespace[2pt]")
        (shared / "tab_stats_full.tex").write_text("\n".join(rows) + "\n")
    print("wrote tables")


if __name__ == "__main__":
    main()
