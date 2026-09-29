"""
Publication figures from data/*.csv -> figures/*.pdf and *.png (300 dpi).

Design rules followed (see docs/FIGURES.md): a fixed categorical order that is
colour-blind safe, PhysaRoute always in slot 1, at most five series per panel
(the nine protocols are split into 'continuous/local' and 'periodic/global'
panels with PhysaRoute repeated as the reference), markers as a secondary
identity channel, one y-axis per panel, 95 % confidence bands from 30 paired
seeds, recessive grids.
"""
from __future__ import annotations

import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(os.environ.get("PHYSAROUTE_OUT", str(Path(__file__).resolve().parent.parent)))
DATA = ROOT / "data"
FIG = ROOT / "figures"
FIG.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "Nimbus Roman", "DejaVu Serif"],
    "font.size": 8.5, "axes.labelsize": 8.5, "axes.titlesize": 9, "legend.fontsize": 7.2,
    "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "figure.dpi": 150, "savefig.dpi": 300,
    "axes.grid": True, "grid.color": "#e3e3e0", "grid.linewidth": 0.6, "grid.linestyle": "-",
    "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#8a8a86",
    "axes.linewidth": 0.7, "legend.frameon": False, "lines.linewidth": 1.6,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
})

STYLE = {  # protocol: (colour, marker, linestyle)
    "PhysaRoute": ("#2a78d6", "o", "-"),
    "QL-WBAN":    ("#eb6834", "s", "-"),
    "QoS-2C":     ("#1baf7a", "^", "-"),
    "ACO-WBAN":   ("#eda100", "D", "-"),
    "PSO-Relay":  ("#e87ba4", "v", "-"),
    "GWO-Relay":  ("#008300", "P", "-"),
    "SIMPLE":     ("#4a3aa7", "X", "-"),
    "M-ATTEMPT":  ("#e34948", "*", "-"),
    "AODV":       ("#6b6b6b", "d", "--"),
    "PR-noEnergy": ("#eb6834", "s", "-"), "PR-noShadow": ("#1baf7a", "^", "-"),
    "PR-noCrit": ("#eda100", "D", "-"), "PR-noExplore": ("#e87ba4", "v", "-"), "PR-noE2E": ("#4a3aa7", "X", "-"),
}
PANEL_A = ["PhysaRoute", "QL-WBAN", "QoS-2C", "ACO-WBAN"]
PANEL_B = ["PhysaRoute", "PSO-Relay", "GWO-Relay", "SIMPLE", "M-ATTEMPT", "AODV"]
ORDER = ["PhysaRoute", "QL-WBAN", "QoS-2C", "ACO-WBAN", "PSO-Relay", "GWO-Relay", "SIMPLE", "M-ATTEMPT", "AODV"]
COL_W, COL_2W = 3.45, 7.1      # IEEE column widths (in)


def _save(fig, name):
    try:
        fig.tight_layout(w_pad=1.2, h_pad=1.0)
    except Exception:
        pass
    fig.savefig(FIG / f"{name}.pdf")
    fig.savefig(FIG / f"{name}.png")
    plt.close(fig)


def _line(ax, df, x, y, protos, ci=True, lw_ref=2.2):
    for p in protos:
        d = df[df.protocol == p].groupby(x)[y]
        m = d.mean(); s = d.std(ddof=1); n = d.count()
        if len(m) == 0:
            continue
        c, mk, ls = STYLE[p]
        lw = lw_ref if p == "PhysaRoute" else 1.4
        ax.plot(m.index, m.values, color=c, marker=mk, ls=ls, lw=lw, ms=4.5 if p != "PhysaRoute" else 5.5,
                mec="white", mew=0.6, label=p, zorder=3 if p == "PhysaRoute" else 2)
        if ci:
            e = 1.96 * s / np.sqrt(n)
            ax.fill_between(m.index, (m - e).values, (m + e).values, color=c, alpha=0.12, lw=0)


def fig_velocity():
    df = pd.read_csv(DATA / "velocity.csv")
    fig, axes = plt.subplots(1, 2, figsize=(COL_2W, 2.3), sharey=True)
    for ax, protos, title in zip(axes, (PANEL_A, PANEL_B), ("(a) continuous / local adaptation", "(b) periodic or reactive")):
        _line(ax, df, "velocity", "pdr", protos)
        ax.set_xlabel("Patient speed $v$ (m/s)"); ax.set_title(title, loc="left")
        ax.legend(ncol=2, loc="lower left")
    axes[0].set_ylabel("Packet delivery ratio")
    axes[0].set_ylim(max(0.80, df.pdr.min() - 0.02), 1.002)
    _save(fig, "fig_pdr_vs_mobility")


def fig_load():
    df = pd.read_csv(DATA / "load.csv")
    fig, axes = plt.subplots(2, 2, figsize=(COL_2W, 4.6), sharey="row")
    for row, (y, lab) in enumerate((("lat_median_ms", "Median latency (ms)"), ("lat_p95_ms", "95th-pct latency (ms)"))):
        for ax, protos, title in zip(axes[row], (PANEL_A, PANEL_B), (("(a)", "(b)"), ("(c)", "(d)"))[row]):
            _line(ax, df, "load", y, protos)
            ax.set_xscale("log"); ax.set_xticks([5, 10, 20, 40, 80, 160]); ax.set_xticklabels([5, 10, 20, 40, 80, 160])
            ax.set_yscale("log")
            if row == 1:
                ax.set_xlabel("Aggregate offered load (packets/s)")
            ax.set_title(f"{title} {'continuous / local' if protos is PANEL_A else 'periodic or reactive'}", loc="left")
        axes[row][0].set_ylabel(lab)
    axes[0][0].legend(ncol=2, loc="upper left"); axes[0][1].legend(ncol=2, loc="upper left")
    _save(fig, "fig_latency_vs_load")
    fig, axes = plt.subplots(1, 2, figsize=(COL_2W, 2.5), sharey=True)
    loads = np.array(sorted(df.load.unique()), dtype=float)
    for ax, protos, title in zip(axes, (PANEL_A, PANEL_B), ("(a) continuous / local adaptation", "(b) periodic or reactive")):
        ax.plot(loads, loads * 87 * 8 / 1e3, color="#9a9a96", ls=":", lw=1.0, label="lossless", zorder=1)
        _line(ax, df, "load", "throughput_kbps", protos)
        ax.set_xlabel("Aggregate offered load (packets/s)"); ax.set_title(title, loc="left")
        ax.legend(ncol=2, loc="upper left")
    axes[0].set_ylabel("Delivered throughput (kb/s)")
    _save(fig, "fig_throughput")
    fig, axes = plt.subplots(1, 2, figsize=(COL_2W, 2.5), sharey=True)
    for ax, protos, title in zip(axes, (PANEL_A, PANEL_B), ("(a) continuous / local adaptation", "(b) periodic or reactive")):
        _line(ax, df, "load", "pdr", protos)
        ax.set_xlabel("Aggregate offered load (packets/s)"); ax.set_title(title, loc="left")
        ax.legend(ncol=2, loc="lower left")
    axes[0].set_ylabel("Packet delivery ratio")
    _save(fig, "fig_pdr_vs_load")


def fig_energy():
    df = pd.read_csv(DATA / "velocity.csv")
    fig, axes = plt.subplots(1, 2, figsize=(COL_2W, 2.5), sharey=True)
    for ax, protos, title in zip(axes, (PANEL_A, PANEL_B), ("(a) continuous / local adaptation", "(b) periodic or reactive")):
        _line(ax, df, "velocity", "energy_mean_mJ", protos)
        ax.set_xlabel("Patient speed $v$ (m/s)"); ax.set_title(title, loc="left")
        ax.legend(ncol=2, loc="upper left")
    axes[0].set_ylabel("Radio energy per node in 180 s (mJ)")
    _save(fig, "fig_energy_vs_mobility")


def fig_lifetime():
    lt = pd.read_csv(DATA / "lifetime.csv")
    tr = pd.read_csv(DATA / "energy_trace.csv")
    fig, axes = plt.subplots(1, 3, figsize=(COL_2W, 2.5), gridspec_kw=dict(width_ratios=[1.15, 1.15, 1.0]))
    for ax, protos, title in zip(axes[:2], (PANEL_A, PANEL_B), ("(a) continuous / local", "(b) periodic or reactive")):
        for p in protos:
            d = tr[tr.protocol == p].groupby("time_s")["residual_frac"].mean() * 100
            c, mk, ls = STYLE[p]
            ax.plot(d.index, d.values, color=c, ls=ls, lw=2.2 if p == "PhysaRoute" else 1.4, label=p,
                    marker=mk, markevery=8, ms=4, mec="white", mew=0.6)
        ax.set_xlabel("Time (s)"); ax.set_title(title, loc="left"); ax.legend(ncol=1, loc="lower left")
    axes[0].set_ylabel("Mean residual energy (%)")
    ax = axes[2]
    g = lt.groupby("protocol")["fnd_s"]
    m = g.mean().reindex(ORDER); s = g.std(ddof=1).reindex(ORDER); n = g.count().reindex(ORDER)
    y = np.arange(len(ORDER))[::-1]
    colors = [STYLE[p][0] for p in ORDER]
    ax.barh(y, m.values, xerr=1.96 * s.values / np.sqrt(n.values), color=colors, height=0.62,
            error_kw=dict(ecolor="#333", lw=0.8, capsize=2))
    ax.set_yticks(y); ax.set_yticklabels(ORDER); ax.set_xlabel("Time to first node death (s)")
    ax.set_title("(c) network lifetime", loc="left"); ax.grid(axis="y", visible=False)
    err = 1.96 * s.values / np.sqrt(n.values)
    ax.set_xlim(0, (m.values + err).max() * 1.22)
    for yi, v, e in zip(y, m.values, err):
        ax.text(v + e + 0.02 * ax.get_xlim()[1], yi, f"{v:.0f}", va="center", fontsize=6.8, color="#333")
    _save(fig, "fig_network_lifetime")


def fig_fnd():
    """Single-column version of the lifetime result: time to first node death only."""
    lt = pd.read_csv(DATA / "lifetime.csv")
    fig, ax = plt.subplots(figsize=(COL_W, 2.0))
    g = lt.groupby("protocol")["fnd_s"]
    m = g.mean().reindex(ORDER); s = g.std(ddof=1).reindex(ORDER); n = g.count().reindex(ORDER)
    y = np.arange(len(ORDER))[::-1]
    err = 1.96 * s.values / np.sqrt(n.values)
    ax.barh(y, m.values, xerr=err, color=[STYLE[p][0] for p in ORDER], height=0.62,
            error_kw=dict(ecolor="#333", lw=0.8, capsize=2))
    ax.set_yticks(y); ax.set_yticklabels(ORDER); ax.set_xlabel("Time to first node death (s)")
    ax.grid(axis="y", visible=False); ax.set_xlim(0, (m.values + err).max() * 1.22)
    for yi, v, e in zip(y, m.values, err):
        ax.text(v + e + 0.02 * ax.get_xlim()[1], yi, f"{v:.0f}", va="center", fontsize=6.8, color="#333")
    _save(fig, "fig_fnd")


def fig_convergence():
    tr = pd.read_csv(DATA / "convergence_trace.csv")
    from .channel import SENSORS, GATEWAY
    names = {i: s[0] for i, s in enumerate(SENSORS)}; names[GATEWAY] = "Gateway"
    fig, axes = plt.subplots(1, 2, figsize=(COL_2W, 2.55))
    for ax, node in zip(axes, sorted(tr.node.unique())):
        d = tr[(tr.node == node) & (tr.time_s <= 60)]
        piv = d.pivot_table(index="time_s", columns="link", values="conductance")
        keep = [c for c in piv.columns if piv[c].max() > 0.05]
        keep = sorted(keep, key=lambda c: -piv[c].max())[:6]
        palette = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#4a3aa7"]
        for k, c in enumerate(keep):
            ax.plot(piv.index, piv[c].values, color=palette[k], lw=1.5, label=f"link to {names.get(c, c)}")
        ax.set_xlabel("Time (s)"); ax.set_title(f"({'ab'[list(sorted(tr.node.unique())).index(node)]}) source: {names[node]}", loc="left")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.30), ncol=3, columnspacing=1.0, handlelength=1.6)
    axes[0].set_ylabel("Conductance $D_{ij}$")
    _save(fig, "fig_convergence")


def fig_ablation():
    df = pd.read_csv(DATA / "ablation.csv")
    variants = ["PhysaRoute", "PR-noEnergy", "PR-noShadow", "PR-noCrit", "PR-noExplore"]
    labels = ["full", "no energy\nterm", "no shadow\npredictor", "no criticality", "no probes"]
    metrics = [("pdr", "PDR"), ("lat_median_ms", "Median latency (ms)"), ("energy_mean_mJ", "Energy / node (mJ)"),
               ("energy_max_mJ", "Max energy / node (mJ)")]
    fig, axes = plt.subplots(1, 4, figsize=(COL_2W, 2.3))
    for ax, (col, lab) in zip(axes, metrics):
        for vi, v in enumerate((1.0, 3.0)):
            d = df[np.isclose(df.velocity, v)].groupby("protocol")[col]
            m = d.mean().reindex(variants); s = d.std(ddof=1).reindex(variants); n = d.count().reindex(variants)
            x = np.arange(len(variants)) + (vi - 0.5) * 0.36
            ax.bar(x, m.values, width=0.33, color="#2a78d6" if vi == 0 else "#eb6834",
                   yerr=1.96 * s.values / np.sqrt(n.values), error_kw=dict(ecolor="#333", lw=0.7, capsize=1.5),
                   label=f"$v$ = {v:.0f} m/s")
        ax.set_xticks(np.arange(len(variants))); ax.set_xticklabels(labels, rotation=60, ha="right", fontsize=6.5)
        ax.set_title(lab, loc="left", fontsize=8); ax.grid(axis="x", visible=False)
        if col == "pdr":
            lo = df[col].min(); ax.set_ylim(max(0.8, lo - 0.02), 1.0)
    axes[0].legend(loc="lower left")
    _save(fig, "fig_ablation")


def fig_coexistence():
    df = pd.read_csv(DATA / "coexistence.csv")
    fig, axes = plt.subplots(1, 2, figsize=(COL_2W, 2.5), sharey=True)
    for ax, protos, title in zip(axes, (PANEL_A, PANEL_B), ("(a) continuous / local adaptation", "(b) periodic or reactive")):
        _line(ax, df, "ble_airtime", "pdr", protos)
        ax.set_xlabel("BLE interferer airtime fraction"); ax.set_title(title, loc="left"); ax.legend(ncol=2, loc="lower left")
    axes[0].set_ylabel("Packet delivery ratio")
    _save(fig, "fig_coexistence")


def fig_security():
    bh = pd.read_csv(DATA / "blackhole.csv")
    jm = pd.read_csv(DATA / "jamming.csv")
    fig, axes = plt.subplots(1, 3, figsize=(COL_2W, 2.35), gridspec_kw=dict(width_ratios=[1.1, 1.1, 1.0]))
    protos_a = ["PhysaRoute", "PR-noE2E", "QL-WBAN", "QoS-2C", "ACO-WBAN"]
    for ax, protos, title in zip(axes[:2], (protos_a, PANEL_B), ("(a) black-hole relays: local", "(b) black-hole relays: periodic")):
        _line(ax, bh, "n_malicious", "pdr", protos)
        ax.set_xlabel("Compromised relays (of 12 sensors)"); ax.set_xticks([0, 1, 2, 3])
        ax.set_title(title, loc="left"); ax.legend(ncol=1, loc="lower left")
    axes[0].set_ylabel("Packet delivery ratio")
    ax = axes[2]
    g0 = jm[jm.jam_node < 0].groupby("protocol")["pdr"].mean().reindex(ORDER)
    g1 = jm[jm.jam_node >= 0].groupby("protocol")["pdr"]
    m = g1.mean().reindex(ORDER); s = g1.std(ddof=1).reindex(ORDER); n = g1.count().reindex(ORDER)
    y = np.arange(len(ORDER))[::-1]
    ax.barh(y, m.values, xerr=1.96 * s.values / np.sqrt(n.values), color=[STYLE[p][0] for p in ORDER], height=0.62,
            error_kw=dict(ecolor="#333", lw=0.8, capsize=2))
    ax.scatter(g0.values, y, marker="|", color="#222", s=40, zorder=4, label="no jammer")
    ax.set_yticks(y); ax.set_yticklabels(ORDER); ax.set_xlabel("PDR, jammer at the hip relay")
    ax.set_xlim(max(0.5, m.min() - 0.1), 1.0); ax.set_title("(c) jamming", loc="left"); ax.grid(axis="y", visible=False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.3), ncol=1, handlelength=1.0)
    _save(fig, "fig_security")


def fig_offcalib():
    v1 = pd.read_csv(DATA / "velocity.csv"); v2 = pd.read_csv(DATA / "offcalib.csv")
    df = pd.concat([v1[["protocol", "velocity", "pdr", "rep"]], v2[["protocol", "velocity", "pdr", "rep"]]])
    fig, axes = plt.subplots(1, 2, figsize=(COL_2W, 2.5), sharey=True)
    for ax, protos, title in zip(axes, (PANEL_A, PANEL_B), ("(a) continuous / local adaptation", "(b) periodic or reactive")):
        _line(ax, df, "velocity", "pdr", protos)
        ax.axvspan(3.05, 4.1, color="#e34948", alpha=0.08, lw=0)
        ax.text(3.55, ax.get_ylim()[0] + 0.01, "outside\ncalibration", ha="center", fontsize=6.5, color="#8a2b2b")
        ax.set_xlabel("Patient speed $v$ (m/s)"); ax.set_title(title, loc="left"); ax.legend(ncol=2, loc="lower left")
    axes[0].set_ylabel("Packet delivery ratio")
    _save(fig, "fig_failure_case")


def fig_icu():
    df = pd.read_csv(DATA / "icu.csv")
    fig, axes = plt.subplots(1, 3, figsize=(COL_2W, 2.5), gridspec_kw=dict(width_ratios=[1.25, 1.0, 1.0], wspace=0.25))
    ax = axes[0]
    data = [df[df.protocol == p]["alarm_lat_p95_ms"].dropna().values for p in ORDER]
    bp = ax.boxplot(data, vert=False, widths=0.55, patch_artist=True, showfliers=False,
                    medianprops=dict(color="#222", lw=1.0), whiskerprops=dict(lw=0.7), capprops=dict(lw=0.7))
    for patch, p in zip(bp["boxes"], ORDER):
        patch.set_facecolor(STYLE[p][0]); patch.set_alpha(0.75); patch.set_edgecolor("white")
    ax.set_yticks(np.arange(1, len(ORDER) + 1)); ax.set_yticklabels(ORDER); ax.invert_yaxis()
    ax.set_xscale("log"); ax.set_xlabel("95th-pct latency per run (ms)")
    ax.set_xticks([3, 5, 10, 20]); ax.set_xticklabels(["3", "5", "10", "20"]); ax.minorticks_off()
    ax.set_title("(a) alarm latency tail", loc="left")
    ax.grid(axis="y", visible=False)
    ax = axes[1]
    g = df.groupby("protocol")
    mean_lat = g["lat_alarm_ms"].mean().reindex(ORDER)
    sd = g["lat_alarm_ms"].std(ddof=1).reindex(ORDER); n = g["lat_alarm_ms"].count().reindex(ORDER)
    y = np.arange(len(ORDER))[::-1]
    ax.barh(y, mean_lat.values, xerr=1.96 * sd.values / np.sqrt(n.values), color=[STYLE[p][0] for p in ORDER], height=0.62,
            error_kw=dict(ecolor="#333", lw=0.8, capsize=2))
    ax.set_yticks(y); ax.set_yticklabels([]); ax.set_xlabel("Mean alarm-frame latency (ms)")
    ax.set_title("(b) mean alarm latency", loc="left"); ax.grid(axis="y", visible=False)
    ax = axes[2]
    miss = 1000.0 * g["alarms_missed"].sum().reindex(ORDER) / g["alarms"].sum().reindex(ORDER)
    ax.barh(y, miss.values, color=[STYLE[p][0] for p in ORDER], height=0.62)
    ax.set_yticks(y); ax.set_yticklabels([]); ax.set_xlabel("Missed alarms per 1000")
    ax.set_title("(c) missed events", loc="left"); ax.grid(axis="y", visible=False)
    for yi, v in zip(y, miss.values):
        ax.text(v + miss.max() * 0.02, yi, f"{v:.1f}", va="center", fontsize=6.8, color="#333")
    _save(fig, "fig_icu_alarms")


def fig_sensitivity():
    df = pd.read_csv(DATA / "sensitivity.csv")
    params = ["mu", "k", "kappa", "gamma", "D_min", "tau_explore", "lambda_E", "hold_s"]
    labels = {"mu": r"$\mu$", "k": r"$\alpha/\mu$", "kappa": r"$\kappa$", "gamma": r"$\gamma$", "D_min": r"$D_{\min}$",
              "tau_explore": r"$\tau_{\rm explore}$ (s)", "lambda_E": r"$\lambda_E$", "hold_s": "hold (s)"}
    from .experiments import SENS_BASE
    fig, axes = plt.subplots(2, 4, figsize=(COL_2W, 3.6))
    for ax, prm in zip(axes.ravel(), params):
        for vi, v in enumerate((1.0, 3.0)):
            base = df[(df.param == "base") & np.isclose(df.velocity, v)]
            d = df[(df.param == prm) & np.isclose(df.velocity, v)]
            xs = sorted(set(d.value.dropna().unique()) | {SENS_BASE[prm]})
            ys = []; es = []
            for x in xs:
                sel = base if np.isclose(x, SENS_BASE[prm]) else d[np.isclose(d.value, x)]
                ys.append(sel.pdr.mean()); es.append(1.96 * sel.pdr.std(ddof=1) / np.sqrt(max(len(sel), 1)))
            c = "#2a78d6" if vi == 0 else "#eb6834"
            ax.errorbar(range(len(xs)), ys, yerr=es, color=c, marker="o", ms=4, lw=1.4, capsize=2, label=f"$v$ = {v:.0f} m/s")
            ax.set_xticks(range(len(xs))); ax.set_xticklabels([f"{x:g}" for x in xs])
        ax.set_title(labels[prm], loc="left"); ax.set_ylim(df.pdr.min() - 0.01, 1.0)
    for ax in axes[:, 0]:
        ax.set_ylabel("PDR")
    axes[0, 0].legend(loc="lower left")
    _save(fig, "fig_sensitivity")


def fig_latency_cdf():
    """Completion-time distribution at the operating point: the fraction of all
    generated packets delivered within x ms (one run per protocol, same seed).
    Curves plateau at the run's delivery ratio, so loss and delay are visible
    together."""
    from . import run_one
    from .experiments import OP, MASTER_SEED
    import physaroute.engine as E
    fig, ax = plt.subplots(figsize=(COL_W, 2.5))
    for p in ORDER:
        lat = []
        orig = E.Engine._delivered
        def deliv(self, pkt, _lat=lat):
            if pkt.t_gen >= self.cfg.warmup:
                _lat.append((self.t - pkt.t_gen) * 1e3)
            return orig(self, pkt)
        E.Engine._delivered = deliv
        try:
            res = run_one(**dict(OP, protocol=p, seed=MASTER_SEED))
        finally:
            E.Engine._delivered = orig
        x = np.sort(lat); y = np.arange(1, len(x) + 1) / max(1, res["generated"])
        x = np.append(x, 5000.0); y = np.append(y, y[-1])
        c, mk, ls = STYLE[p]
        ax.plot(x, y, color=c, ls=ls, lw=2.0 if p == "PhysaRoute" else 1.2, label=p)
    ax.set_xscale("log"); ax.set_xlabel("End-to-end latency $x$ (ms)"); ax.set_ylabel("Fraction of generated packets\ndelivered within $x$")
    ax.set_ylim(0.5, 1.0); ax.set_xlim(1.5, 3000); ax.legend(ncol=2, loc="lower right")
    _save(fig, "fig_latency_cdf")


def fig_channel():
    """Channel-model characterisation: PER curve, link-outage fraction vs speed,
    and an example dynamic path-loss trace."""
    from . import channel as ch
    per = ch.PERModel()
    fig, axes = plt.subplots(1, 3, figsize=(COL_2W, 2.3))
    ax = axes[0]
    prx = np.linspace(-105, -80, 200)
    for body, lab in ((87, "96-B data frame"), (255, "255-B PSDU (std. test)"), (0, "I-Ack")):
        ncw = ch.psdu_codewords(body)
        ax.plot(prx, 1 - np.exp(ncw * per.log_success_per_codeword(prx)), lw=1.4, label=lab)
    ax.axhline(0.1, color="#888", lw=0.7, ls=":"); ax.set_yscale("log"); ax.set_ylim(1e-4, 1)
    ax.set_xlabel("Received power (dBm)"); ax.set_ylabel("Packet error rate"); ax.set_title("(a) PHY", loc="left")
    ax.legend(loc="lower left")
    ax = axes[1]
    vs = np.linspace(0, 3, 7); rng = np.random.default_rng(1)
    outage = {"direct": [], "all": []}
    for v in vs:
        o_d = []; o_a = []
        for r in range(4):
            logS, PL, d = ch.generate_channel(np.random.default_rng([r, 5]), v, 200.0, 0.1, per)
            p = np.exp(ch.psdu_codewords(87) * logS)
            o_d.append((p[:, :12, 12] < 0.5).mean()); o_a.append((p[:, :12, :12] < 0.5).mean())
        outage["direct"].append(np.mean(o_d)); outage["all"].append(np.mean(o_a))
    ax.plot(vs, outage["direct"], marker="o", ms=4, lw=1.4, color="#2a78d6", label="sensor-gateway links")
    ax.plot(vs, outage["all"], marker="s", ms=4, lw=1.4, color="#eb6834", label="sensor-sensor links")
    ax.set_xlabel("Patient speed (m/s)"); ax.set_ylabel("Fraction of 100-ms windows\nwith link PER > 50 %")
    ax.set_title("(b) dynamics", loc="left"); ax.legend(loc="upper left")
    ax = axes[2]
    logS, PL, d = ch.generate_channel(np.random.default_rng([3, 5]), 1.0, 60.0, 0.1, per)
    t = np.arange(PL.shape[0]) * 0.1
    ax.plot(t, -10 - PL[:, 1, 12], lw=0.9, color="#2a78d6", label="wrist-gateway")
    ax.plot(t, -10 - PL[:, 0, 12], lw=0.9, color="#eb6834", label="chest-gateway")
    ax.axhline(per.sensitivity_dBm(87, 0.1), color="#888", lw=0.7, ls=":")
    ax.set_xlabel("Time (s)"); ax.set_ylabel("Received power (dBm)"); ax.set_title("(c) example, $v$ = 1 m/s", loc="left")
    ax.set_ylim(-103, -42); ax.legend(loc="upper left", ncol=2)
    _save(fig, "fig_channel")


def main():
    for fn in (fig_channel, fig_velocity, fig_load, fig_energy, fig_lifetime, fig_fnd, fig_convergence, fig_ablation,
               fig_coexistence, fig_security, fig_offcalib, fig_icu, fig_sensitivity, fig_latency_cdf):
        try:
            fn()
            print("ok", fn.__name__)
        except FileNotFoundError as e:
            print("skip", fn.__name__, e)


if __name__ == "__main__":
    main()
