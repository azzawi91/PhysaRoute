# Figure conventions

All figures are produced by `python -m physaroute.plots` from `data/*.csv`; nothing is drawn by hand.

* **One categorical palette, fixed order.** PhysaRoute is always slot 1 (`#2a78d6`), then QL-WBAN, QoS-2C,
  ACO-WBAN, PSO-Relay, GWO-Relay, SIMPLE, M-ATTEMPT, AODV (`plots.STYLE`). A protocol keeps its colour and marker
  in every figure, whichever subset is shown, so identity is never carried by colour alone (marker + line style are the
  secondary channels; AODV is dashed).
* **At most five or six series per panel.** The nine protocols are split into two panels — (a) protocols that adapt
  continuously from local observations (QL-WBAN, QoS-2C, ACO-WBAN) and (b) protocols that recompute routes per round or
  reactively (PSO-Relay, GWO-Relay, SIMPLE, M-ATTEMPT, AODV) — with PhysaRoute repeated in both as the reference.
* **Uncertainty is always shown.** Lines carry 95 % confidence bands from the 30 paired seeds; bars carry 95 % CIs.
* **One y-axis per panel**, recessive grid, no top/right spines, serif font matching the manuscript, IEEE column widths
  (3.45 in single, 7.1 in double), 300 dpi PNG and vector PDF of every figure.
* **Latency is shown as a completion-time distribution** over all generated packets (curves saturate at the delivery
  ratio), so that loss and delay are read together and a protocol cannot look fast by dropping packets.
* Ablation and sensitivity figures use two colours only (1 m/s, 3 m/s) with the variant on the x axis.
