# Baseline protocols

All baselines run on the same engine, channel, MAC, energy model and beacon substrate as PhysaRoute
(`docs/SIMULATOR.md`). Each is implemented from its original description; parameters are in
`params/baselines.yaml`. "Candidates" below means neighbours not farther from the gateway in hops (excluding the
packet's source), with only strictly-closer neighbours or the gateway allowed after one lateral hop.

| Name | Source | Decision rule | Control traffic | On link failure |
| --- | --- | --- | --- | --- |
| **AODV** | Perkins & Royer 1999; RFC 3561 | reactive route to the gateway; RREQ flood (24 B, TTL 4), RREP from gateway or a node with a fresh route (20 B); 3 s active-route timeout refreshed by data | RREQ/RREP/RERR; discovery timer 150 ms, 2 retries | invalidate, RERR (12 B), re-discover; data buffered FIFO |
| **M-ATTEMPT** | Javaid et al. 2013 | every 5 s: parent = candidate with min hop count, tie-break by energy-cost route (linear path loss + parent's advertised cost); critical data direct to gateway | beacon fields only | direct transmission until next round |
| **SIMPLE** | Nadeem et al. 2013 | every 5 s the gateway elects the non-critical node with min d(i,gw)/E_res(i) as forwarder (24 B broadcast); non-critical nodes closer to the forwarder than to the gateway use it; critical nodes direct | round broadcast | direct transmission |
| **ACO-WBAN** | AntHocNet, Di Caro et al. 2005 | pheromone T_ij; forward ant every 1 s per sensor follows T^1 (16 B); backward ant (24 B) updates T ← 0.7 T + 0.3 τ with τ = 1/(measured path delay + hops·2 ms); data follow ∝ T^5 | ants (≈50 frames/s) | evaporate T_ij by 50 %, re-route to the sampled alternative |
| **PSO-Relay** | PSOBAN, Bilandi et al. 2019 | every 5 s the gateway optimises the parent of each non-critical sensor (gateway or a non-critical node not farther in hops) with 20 particles × 40 iterations (inertia 0.9→0.2, c1 = c2 = 1.5) minimising 0.4·worst drain rate + 0.3·transmit energy + 0.3·expected loss (mean CM3 path loss); critical sensors direct, never relay | 40 B assignment broadcast | direct transmission until next round |
| **GWO-Relay** | Mirjalili et al. 2014; Bilandi et al. 2020 | as PSO-Relay with 20 wolves × 40 iterations of GWO (a: 2 → 0) | same | same |
| **QL-WBAN** | Q-routing, Boyan & Littman 1994; Guo et al. 2022; Arafat et al. 2024 | Q_i(j) = estimated delivery time via j; on ACK: Q ← Q + 0.5 (queue + service + t_j − Q), t_j = neighbour's best Q piggybacked in the ACK, plus 5 ms·(1 − R_j); on failure: Q ← Q + 0.5 (50 ms − Q); ε-greedy (ε = 0.05) | 1 B in ACK | re-route to the next-best Q |
| **QoS-2C** | DMQoS (Razzaque 2011), QPRD (Khan 2012), ZEQoS (Khan 2014) | critical: min advertised path delay among neighbours with link reliability ≥ 0.9 (else the most reliable); ordinary: closer-to-gateway neighbour with min d²/E_res(j); reliability EWMA (β = 0.4) of ACKs; path delay advertised in beacons | beacon field | re-route by the same rule |

PhysaRoute ablations: `PR-noEnergy` (β1 = 0, λ_E = 0), `PR-noShadow` (β3 = 0, no predictor), `PR-noCrit`
(β4 = 0, κ_crit = κ, λ_c = 0), `PR-noExplore` (no probes), `PR-noE2E` (hop ACKs only; used in the black-hole
experiment).
