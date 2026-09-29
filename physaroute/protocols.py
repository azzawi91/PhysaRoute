"""
Routing protocols for the PhysaRoute WBAN simulator.

Every protocol implements the same small interface (class Protocol) and runs
on the same engine, channel, MAC, energy model and control substrate; only
the routing logic differs.  Baselines are implemented from the cited
descriptions (see docs/BASELINES.md):

  AODV        Perkins & Royer 1999 / RFC 3561 (reactive discovery, 3 s route
              timeout, RREQ retries, RERR on link failure)
  M-ATTEMPT   Javaid et al. 2013 (min-hop tree, energy-cost tie-break,
              direct transmission for critical data, 5 s re-computation)
  SIMPLE      Nadeem et al. 2013 (sink elects one forwarder per round by
              cost d(i)/E_res(i); critical nodes transmit directly)
  ACO-WBAN    AntHocNet-style stigmergy (Di Caro et al. 2005): periodic
              forward/backward ants, pheromone = path-goodness estimate,
              stochastic data forwarding with exponent beta
  PSO-Relay   periodic centralised relay assignment optimised by particle
  GWO-Relay   swarm / grey-wolf optimisation (PSOBAN 2019; Bilandi 2020)
  QL-WBAN     Q-routing (Boyan & Littman 1994) with an energy-aware cost,
              epsilon-greedy exploration (Guo 2022, Arafat 2024 style)
  QoS-2C      two-class QoS-aware forwarding after DMQoS / QPRD / ZEQoS
              (reliability-constrained min-delay for critical traffic,
              energy-geographic cost for ordinary traffic)
  PhysaRoute  this paper (Eqs. 7-9 of the manuscript)
"""
from __future__ import annotations

import math
import numpy as np

from . import channel as ch
from .engine import BROADCAST, HOLD, HOLD_BACK, SKIP, EV_TIMER

GW = ch.GATEWAY


def _softmax_sample(rng, keys, vals, theta):
    m = max(vals)
    ws = [math.exp((v - m) / theta) for v in vals]
    s = sum(ws)
    r = rng.random() * s
    acc = 0.0
    for k, w in zip(keys, ws):
        acc += w
        if r <= acc:
            return k
    return keys[-1]


class Protocol:
    name = "base"

    def __init__(self, eng, **kw):
        self.eng = eng
        self.kw = kw
        self.rng = eng.rng_mac
        # per-node EWMA link-success estimate, shared helper
        self.lq = [dict() for _ in eng.nodes]

    # --- helpers -----------------------------------------------------------
    def timer(self, delay, tag, node=None):
        self.eng.push(self.eng.t + delay, EV_TIMER, node.id if node is not None else -1, tag)

    def cands(self, node, pkt=None):
        """Loop-free candidate set: neighbours not farther from the gateway and
        not already on the packet's path; after one lateral hop only strictly
        closer neighbours (or the gateway) remain."""
        eng = self.eng
        h = node.hops
        strict = pkt is not None and pkt.hops >= 1
        out = []
        for j, nb in node.nbr.items():
            if not eng.nodes[j].alive:
                continue
            if j == GW or nb[1] < h or (not strict and nb[1] == h):
                if j != pkt_src(pkt):
                    out.append(j)
        if not out:
            out = [GW]
        return out

    def _lq_update(self, node, j, ok, a=0.15):
        d = self.lq[node.id]
        d[j] = (1 - a) * d.get(j, 0.9) + a * (1.0 if ok else 0.0)

    def lq_get(self, node, j):
        return self.lq[node.id].get(j, 0.9)

    # --- interface ---------------------------------------------------------
    def start(self): pass
    def select_next_hop(self, node, pkt): return GW
    def on_tx_result(self, node, pkt, nh, ok, rssi, t_service, rx): self._lq_update(node, nh, ok)
    def on_hop_fail(self, node, pkt): return None
    def on_ctrl_rx(self, node, pkt, sender, rssi): pass
    def on_ctrl_result(self, node, pkt, nh, ok, rssi): pass
    def on_ctrl_fail(self, node, pkt): pass
    def on_beacon(self, node, sender, payload, rssi): pass
    def on_receipts(self, node, bitmap): pass
    def on_window(self, w): pass
    def on_timer(self, tag, node): pass
    def on_delivered(self, pkt): pass
    def on_node_dead(self, node): pass
    def advertised_cost(self, node): return float(node.hops)
    def trace_state(self, node): return {}


def pkt_src(pkt):
    return pkt.src if pkt is not None else -2


# ===========================================================================
# PhysaRoute
# ===========================================================================
class PhysaRoute(Protocol):
    """
    Physarum tube dynamics on WBAN links (manuscript Eqs. 7-9).

    Potential field: every node advertises its expected cost-to-gateway
    p_i (ETX-like, in expected transmissions) in beacon re-broadcasts and in
    the 1-byte field of every I-Ack; the gateway has p = 0.
    Link length:     L_ij = 1 / p_hat_ij   (expected transmissions per success)
    Flow gain:       g_ij = max(0, (p_i - p_j) / L_ij)      (progress per transmission)
    Realised flow:   Phi_ij = D_ij * g_ij * s_ij, s_ij = window success ratio
    Conductance:     D_ij <- (1 - mu) D_ij + alpha F_ij psi(Phi_ij), psi(x) = x^g/(1+x^g)
    Forwarding:      pi(j|i) = (D_ij g_ij)^kappa / sum_k (D_ik g_ik)^kappa
    Fitness:         F_ij = b1 R_j + b2 p_hat_ij + b3 (1 - S_hat_ij) + b4 (1 - c_j)
    Pruning / probes: D_ij < D_min -> pruned; an exploration probe every
    tau_explore seeds a pruned link above its unstable fixed point D^- so that
    a viable link re-grows (Theorem 1 of the manuscript).
    """
    name = "PhysaRoute"

    def __init__(self, eng, mu=0.20, alpha=1.00, gamma=2.0, kappa=2.0, kappa_crit=4.0, D_min=0.05,
                 beta=(0.35, 0.30, 0.20, 0.15), tau_explore=10.0, lambda_E=2.0, lambda_c=1.0,
                 use_e2e=True, use_probe=True, use_shadow=True, D_init=2.0,
                 sens_margin_dB=3.0, hold_s=0.05, **kw):
        super().__init__(eng, **kw)
        self.hold_s = hold_s
        self.mu, self.alpha, self.gamma = mu, alpha, gamma
        self.kappa, self.kappa_crit, self.D_min = kappa, kappa_crit, D_min
        self.beta = beta; self.tau_explore = tau_explore
        self.lambda_E = lambda_E; self.lambda_c = lambda_c; self.use_e2e = use_e2e
        self.use_probe = use_probe; self.use_shadow = use_shadow; self.D_init = D_init
        self.wants_receipts = use_e2e
        self.thr = eng.sens_dBm + sens_margin_dB
        n = len(eng.nodes)
        self.D = [dict() for _ in range(n)]        # conductance per candidate link
        self.acked = [dict() for _ in range(n)]    # ACKed frames per next hop in window
        self.attd = [dict() for _ in range(n)]     # attempted frames per next hop in window
        self.pruned = [set() for _ in range(n)]
        self.rs = [dict() for _ in range(n)]       # per-link RSSI predictor state
        self.pot_nb = [dict() for _ in range(n)]   # freshest advertised potential of neighbours
        self.sent_via = [dict() for _ in range(n)] # seq -> first hop, last beacon period
        self.p_e2e = [dict() for _ in range(n)]    # e2e delivery estimate per first hop
        for nd in eng.nodes:
            nd.state["pot"] = 0.0 if nd.is_gw else 1.0

    # -- reinforcement function ---------------------------------------------
    def psi(self, x):
        xg = x ** self.gamma
        return xg / (1.0 + xg)

    def fixed_points(self, F, h):
        """(D_minus, D_plus) of D = k psi(h D) for gamma = 2, or None if the link is not viable."""
        k = self.alpha * F / self.mu
        if h <= 0.0 or k * h < 2.0:
            return None
        r = math.sqrt(k * k - 4.0 / (h * h))
        return (0.5 * (k - r), 0.5 * (k + r))

    def start(self):
        if self.use_probe:
            for n in self.eng.nodes[:-1]:
                self.timer(self.rng.uniform(0.5, 1.0) * self.tau_explore, "probe", n)

    # -- potentials ---------------------------------------------------------
    def pot_of(self, node, j):
        if j == GW:
            return 0.0
        v = self.pot_nb[node.id].get(j)
        if v is None:
            nb = node.nbr.get(j)
            v = nb[3] if nb is not None else 1.0
        return max(v, 1.0)     # plausibility bound: a relay needs >= 1 transmission

    def length(self, node, j):
        """Energy-aware tube length: expected transmissions per success,
        stretched by the residual-energy deficit of the next hop."""
        L = 1.0 / max(self.lq_get(node, j), 0.02)
        if j != GW:
            nb = node.nbr.get(j)
            R = nb[2] if nb is not None else 0.5
            L *= (1.0 + self.lambda_E * (1.0 - R)) * (1.0 + self.lambda_c * self.eng.nodes[j].crit)
        return L

    def gain(self, node, j):
        return max(0.0, (node.state["pot"] - self.pot_of(node, j)) / self.length(node, j))

    def _own_potential(self, node):
        """Potential achievable through the *active* overlay, and the best
        pruned link (if any) that would improve on it: (p_active, j_best_pruned, p_pruned)."""
        best = 1e9; bestp = 1e9; jp = None
        pr = self.pruned[node.id]
        for j in self.cands(node):
            v = self.length(node, j) + self.pot_of(node, j)
            if j in pr:
                if v < bestp:
                    bestp = v; jp = j
            elif v < best:
                best = v
        if best >= 1e9:
            best = bestp if bestp < 1e9 else 1.0
        return best, jp, bestp

    def advertised_cost(self, node):
        return node.state["pot"]

    # -- forwarding -----------------------------------------------------------
    def _active(self, node, pkt):
        cs = self.cands(node, pkt)
        D = self.D[node.id]
        for j in cs:
            if j not in D:
                D[j] = self.D_init
        return [j for j in cs if j not in self.pruned[node.id]]

    def _flows(self, node, act):
        D = self.D[node.id]
        return [D[j] * self.gain(node, j) for j in act]

    def select_next_hop(self, node, pkt):
        if node.state.get("hold_until", -1.0) > self.eng.t:
            return SKIP
        act = self._active(node, pkt)
        if not act:
            # every tube has been pruned: emergency choice by link-quality estimate;
            # a success re-seeds the tube (on_tx_result)
            cs = self.cands(node, pkt)
            return max(cs, key=lambda j: (self.lq_get(node, j), j == GW))
        if len(act) == 1:
            return act[0]
        Q = self._flows(node, act)
        kap = self.kappa_crit if pkt.cls in ("crit", "alarm") else self.kappa
        ws = [q ** kap for q in Q]
        s = sum(ws)
        if s <= 0.0:
            D = self.D[node.id]
            return max(act, key=lambda j: D[j])
        r = self.rng.random() * s; acc = 0.0
        for j, w in zip(act, ws):
            acc += w
            if r <= acc:
                return j
        return act[-1]

    def on_hop_fail(self, node, pkt):
        act = [j for j in self._active(node, pkt) if j != pkt.nh]
        if act:
            Q = self._flows(node, act)
            return act[int(np.argmax(Q))]
        # active overlay exhausted: fall back to the best-quality pruned link
        # (an on-demand probe), otherwise hold the packet for one window
        alt = [j for j in self.cands(node, pkt) if j != pkt.nh]
        if alt:
            return max(alt, key=lambda j: self.lq_get(node, j))
        # node-level adaptive hold: 50 ms, doubling up to 400 ms, reset on success
        st = node.state
        h = st.get("hold_len", self.hold_s)
        st["hold_until"] = self.eng.t + h
        st["hold_len"] = min(2.0 * h, 4.0 * self.hold_s)
        self.timer(h + 1e-4, "unhold", node)
        return HOLD_BACK

    # -- measurements ---------------------------------------------------------
    def on_tx_result(self, node, pkt, nh, ok, rssi, t_service, rx):
        self._lq_update(node, nh, ok)
        nid = node.id
        a = self.attd[nid]; a[nh] = a.get(nh, 0) + 1
        if ok:
            self.acked[nid][nh] = self.acked[nid].get(nh, 0) + 1
            node.state["hold_len"] = self.hold_s
            if nh in self.pruned[nid]:
                self._reseed(node, nh)
            if not rx.is_gw:
                self.pot_nb[nid][nh] = 0.0 if rx.malicious else rx.state.get("pot", 1.0)
            st = self.rs[nid].get(nh)
            if st is None:
                self.rs[nid][nh] = [rssi, rssi, 4.0]      # last, mean, residual variance
            else:
                pred = st[1] + 0.8 * (st[0] - st[1])
                res = rssi - pred
                st[2] = 0.9 * st[2] + 0.1 * res * res
                st[1] = 0.95 * st[1] + 0.05 * rssi
                st[0] = rssi
        if pkt.holder == pkt.src and self.use_e2e:
            self.sent_via[nid][pkt.payload % 64] = pkt.via if pkt.via is not None else nh

    def on_beacon(self, node, sender, payload, rssi):
        if node.is_gw:
            return
        # a beacon is a free link-quality sample: expected success at this RSSI
        p = math.exp(self.eng.ncw_data * float(self.eng.per.log_success_per_codeword(rssi)))
        d = self.lq[node.id]
        d[sender.id] = 0.8 * d.get(sender.id, 0.9) + 0.2 * p
        if not sender.is_gw:
            self.pot_nb[node.id][sender.id] = 0.0 if sender.malicious else payload["cost"]

    def shadow_prob(self, node, j):
        if not self.use_shadow:
            return 0.0
        st = self.rs[node.id].get(j)
        if st is None:
            return 0.2
        pred = st[1] + 0.8 * (st[0] - st[1])
        sd = math.sqrt(max(st[2], 1.0))
        z = (self.thr - pred) / sd
        return 0.5 * math.erfc(-z / math.sqrt(2.0))       # Phi(z)

    def fitness(self, node, j):
        b1, b2, b3, b4 = self.beta
        if j == GW:
            R = 1.0; c = 0.0
        else:
            nb = node.nbr.get(j)
            R = nb[2] if nb is not None else 0.5
            c = self.eng.nodes[j].crit
        p = self.lq_get(node, j)
        S = self.shadow_prob(node, j)
        return b1 * R + b2 * p + b3 * (1.0 - S) + b4 * (1.0 - c)

    # -- conductance update (once per window) ---------------------------------
    def on_window(self, w):
        eng = self.eng
        for node in eng.nodes[:-1]:
            if not node.alive:
                continue
            nid = node.id
            D = self.D[nid]; acked = self.acked[nid]; attd = self.attd[nid]
            pot, jp, potp = self._own_potential(node)
            node.state["pot"] = pot
            # a pruned link that would clearly improve the potential is probed
            # at once (the mold extends a pseudopod toward a richer source)
            if jp is not None and potp < 0.8 * pot and self.use_probe and \
                    eng.t - node.state.get("last_probe", -9.0) > 1.0:
                node.state["last_probe"] = eng.t
                eng.send_ctrl(node, "probe", None, 8, dest=jp)
            act = [j for j in self.cands(node) if j in D]
            for j in act:
                if j in self.pruned[nid]:
                    continue
                n_att = attd.get(j, 0)
                s = acked.get(j, 0) / n_att if n_att > 0 else self.lq_get(node, j)
                if self.use_e2e and j in self.p_e2e[nid]:
                    s *= self.p_e2e[nid][j]      # flow that does not reach the sink is not flow
                phi = D[j] * self.gain(node, j) * s
                D[j] = (1.0 - self.mu) * D[j] + self.alpha * self.fitness(node, j) * self.psi(phi)
                if D[j] < self.D_min:
                    self.pruned[nid].add(j); D[j] = 0.0
            attd.clear(); acked.clear()

    def on_receipts(self, node, bitmap):
        if not self.use_e2e:
            return
        nid = node.id
        sv = self.sent_via[nid]
        if not sv:
            return
        cnt = {}; okc = {}
        for seq, j in sv.items():
            cnt[j] = cnt.get(j, 0) + 1
            if (bitmap >> seq) & 1:
                okc[j] = okc.get(j, 0) + 1
        for j, n in cnt.items():
            r = okc.get(j, 0) / n
            self.p_e2e[nid][j] = 0.6 * self.p_e2e[nid].get(j, 1.0) + 0.4 * r
        sv.clear()

    # -- exploration probes -----------------------------------------------------
    def on_timer(self, tag, node):
        if tag == "unhold" and node is not None:
            self.eng.kick(node)
            return
        if tag == "probe" and node is not None and node.alive:
            pr = [j for j in self.pruned[node.id] if self.eng.nodes[j].alive]
            if pr:
                j = pr[int(self.rng.integers(len(pr)))]
                self.eng.send_ctrl(node, "probe", None, 8, dest=j)
            self.timer(self.tau_explore, "probe", node)

    def _reseed(self, node, nh):
        """Re-open a pruned tube if it is viable: seed it at 1/h, the geometric
        mean of the unstable and stable fixed points (D^- D^+ = 1/h^2), where
        growth toward D^+ is fastest."""
        if self.pruned[node.id]:
            # potentials were computed over the active overlay; a re-opened link
            # must be judged against the best available path
            pot, jp, potp = self._own_potential(node)
            node.state["pot"] = min(pot, potp)
        h = self.gain(node, nh) * self.lq_get(node, nh)
        if h <= 0.0:
            h = self.lq_get(node, nh)
        fp = self.fixed_points(self.fitness(node, nh), h)
        if fp is not None:
            self.pruned[node.id].discard(nh)
            self.D[node.id][nh] = max(1.0 / h, 2.0 * self.D_min)

    def on_ctrl_result(self, node, pkt, nh, ok, rssi):
        if pkt.ctype != "probe":
            return
        self._lq_update(node, nh, ok, a=0.3)
        if ok:
            self._reseed(node, nh)

    def trace_state(self, node):
        return dict(self.D[node.id])


# ===========================================================================
# AODV (RFC 3561, single destination = gateway)
# ===========================================================================
class AODV(Protocol):
    name = "AODV"
    ACTIVE_ROUTE_TIMEOUT = 3.0
    RREQ_TIMEOUT = 0.15
    RREQ_RETRIES = 2
    TTL = 4

    def __init__(self, eng, **kw):
        super().__init__(eng, **kw)
        n = len(eng.nodes)
        self.route = [None] * n            # [nh, hops, expiry]
        self.pending = [False] * n
        self.rreq_id = [0] * n
        self.rreq_tries = [0] * n
        self.seen = [set() for _ in range(n)]
        self.reverse = [dict() for _ in range(n)]   # orig -> (prev hop, expiry)

    def _valid(self, node):
        r = self.route[node.id]
        return r is not None and r[2] > self.eng.t and self.eng.nodes[r[0]].alive

    def _discover(self, node):
        nid = node.id
        if self.pending[nid]:
            return
        self.pending[nid] = True
        self.rreq_tries[nid] = 0
        self._send_rreq(node)

    def _send_rreq(self, node):
        nid = node.id
        self.rreq_id[nid] += 1
        self.eng.send_ctrl(node, "rreq", {"orig": nid, "id": self.rreq_id[nid], "hops": 0, "ttl": self.TTL},
                           24, dest=BROADCAST, front=True)
        self.timer(self.RREQ_TIMEOUT, ("rreq_to", self.rreq_id[nid]), node)

    def select_next_hop(self, node, pkt):
        if self._valid(node):
            return self.route[node.id][0]
        self._discover(node)
        return HOLD

    def on_tx_result(self, node, pkt, nh, ok, rssi, t_service, rx):
        self._lq_update(node, nh, ok)
        r = self.route[node.id]
        if ok and r is not None and r[0] == nh:
            r[2] = self.eng.t + self.ACTIVE_ROUTE_TIMEOUT

    def on_hop_fail(self, node, pkt):
        # link break: invalidate, notify precursors, rediscover
        self.route[node.id] = None
        self.eng.send_ctrl(node, "rerr", {"via": node.id}, 12, dest=BROADCAST, front=True)
        self._discover(node)
        return HOLD

    def on_ctrl_rx(self, node, pkt, sender, rssi):
        p = pkt.payload; eng = self.eng
        if pkt.ctype == "rreq":
            key = (p["orig"], p["id"])
            if key in self.seen[node.id] or p["orig"] == node.id:
                return
            self.seen[node.id].add(key)
            self.reverse[node.id][p["orig"]] = (sender.id, eng.t + self.ACTIVE_ROUTE_TIMEOUT)
            if node.is_gw or node.malicious:
                eng.send_ctrl(node, "rrep", {"orig": p["orig"], "hops": 0}, 20, dest=sender.id, front=True)
            elif self._valid(node):
                eng.send_ctrl(node, "rrep", {"orig": p["orig"], "hops": self.route[node.id][1]}, 20,
                              dest=sender.id, front=True)
            elif p["ttl"] > 0:
                eng.send_ctrl(node, "rreq", {"orig": p["orig"], "id": p["id"], "hops": p["hops"] + 1,
                                             "ttl": p["ttl"] - 1}, 24, dest=BROADCAST, front=True)
        elif pkt.ctype == "rrep":
            if node.is_gw:
                return
            hops = p["hops"] + 1
            r = self.route[node.id]
            if r is None or r[2] <= eng.t or hops <= r[1]:
                self.route[node.id] = [sender.id, hops, eng.t + self.ACTIVE_ROUTE_TIMEOUT]
            if p["orig"] == node.id:
                self.pending[node.id] = False
                eng.kick(node)
            else:
                rv = self.reverse[node.id].get(p["orig"])
                if rv is not None:
                    eng.send_ctrl(node, "rrep", {"orig": p["orig"], "hops": hops}, 20, dest=rv[0], front=True)
        elif pkt.ctype == "rerr":
            r = self.route[node.id]
            if r is not None and r[0] == p["via"]:
                self.route[node.id] = None
                eng.send_ctrl(node, "rerr", {"via": node.id}, 12, dest=BROADCAST, front=True)

    def on_timer(self, tag, node):
        if isinstance(tag, tuple) and tag[0] == "rreq_to" and node is not None:
            nid = node.id
            if not self.pending[nid] or tag[1] != self.rreq_id[nid]:
                return
            if self._valid(node):
                self.pending[nid] = False; self.eng.kick(node); return
            self.rreq_tries[nid] += 1
            if self.rreq_tries[nid] <= self.RREQ_RETRIES:
                self._send_rreq(node)
            else:
                self.pending[nid] = False
                q = node.queue
                keep = []
                while q:
                    pk = q.popleft()
                    if pk.kind == "data":
                        self.eng.drop(pk, "no_route")
                    else:
                        keep.append(pk)
                q.extend(keep)
                self.eng.kick(node)

    def on_ctrl_fail(self, node, pkt):
        if pkt.ctype == "rrep":
            pass


# ===========================================================================
# M-ATTEMPT
# ===========================================================================
class MATTEMPT(Protocol):
    name = "M-ATTEMPT"

    def __init__(self, eng, round_s=5.0, **kw):
        super().__init__(eng, **kw)
        self.round_s = round_s
        self.parent = [GW] * len(eng.nodes)
        self.bad = [set() for _ in eng.nodes]

    def start(self):
        self.timer(0.5, "round")

    def _link_cost(self, node, j):
        # relative energy cost of the hop ~ linear path loss (Javaid 2013: least energy route)
        return 10 ** ((self.eng.cfg.tx_power_dBm - node.nbr[j][0]) / 10.0) / 1e5

    def _select(self, node):
        cs = [j for j in self.cands(node) if j not in self.bad[node.id]] or self.cands(node)
        best = None; bkey = None
        for j in cs:
            if j == GW:
                hops = 1; cost = self._link_cost(node, j) if j in node.nbr else 1.0
            else:
                nb = node.nbr[j]; hops = nb[1] + 1; cost = self._link_cost(node, j) + nb[3]
            key = (hops, cost)
            if bkey is None or key < bkey:
                best, bkey = j, key
        return best if best is not None else GW

    def advertised_cost(self, node):
        p = self.parent[node.id]
        if p == GW:
            return self._link_cost(node, GW) if GW in node.nbr else 1.0
        nb = node.nbr.get(p)
        return (self._link_cost(node, p) + nb[3]) if nb else 1.0

    def on_timer(self, tag, node):
        if tag == "round":
            for n in self.eng.nodes[:-1]:
                if n.alive:
                    self.bad[n.id].clear()
                    self.parent[n.id] = self._select(n)
            self.timer(self.round_s, "round")

    def select_next_hop(self, node, pkt):
        if pkt.cls in ("crit", "alarm"):
            return GW
        p = self.parent[node.id]
        if p != GW and (not self.eng.nodes[p].alive or p in self.bad[node.id] or p == pkt.src):
            return GW
        return p

    def on_hop_fail(self, node, pkt):
        if pkt.nh != GW:
            self.bad[node.id].add(pkt.nh)
            return GW
        return None


# ===========================================================================
# SIMPLE
# ===========================================================================
class SIMPLE(Protocol):
    name = "SIMPLE"

    def __init__(self, eng, round_s=5.0, **kw):
        super().__init__(eng, **kw)
        self.round_s = round_s
        self.fwd = [-1] * len(eng.nodes)
        self.gw_energy = {}

    def start(self):
        self.timer(0.3, "round")

    def on_beacon(self, node, sender, payload, rssi):
        if node.is_gw:
            self.gw_energy[sender.id] = payload["energy"]

    def on_timer(self, tag, node):
        if tag == "round":
            eng = self.eng
            best, bc = -1, 1e18
            for n in eng.nodes[:-1]:
                if not n.alive or n.crit >= 0.85:
                    continue
                e = self.gw_energy.get(n.id, 1.0)
                if e <= 0.02:
                    continue
                cost = eng.d_mm[n.id, GW] / e
                if cost < bc:
                    best, bc = n.id, cost
            eng.send_ctrl(eng.gw, "round", {"fwd": best}, 24, dest=BROADCAST, front=True)
            self.timer(self.round_s, "round")

    def on_ctrl_rx(self, node, pkt, sender, rssi):
        if pkt.ctype == "round":
            self.fwd[node.id] = pkt.payload["fwd"]

    def select_next_hop(self, node, pkt):
        f = self.fwd[node.id]
        if pkt.cls in ("crit", "alarm") or f < 0 or f == node.id or f == pkt.src or not self.eng.nodes[f].alive:
            return GW
        d = self.eng.d_mm
        return f if d[node.id, f] < d[node.id, GW] else GW

    def on_hop_fail(self, node, pkt):
        return GW if pkt.nh != GW else None


# ===========================================================================
# ACO-WBAN (AntHocNet-style)
# ===========================================================================
class _AntPkt:
    __slots__ = ("hops", "src", "cls")

    def __init__(self, hops, src):
        self.hops = hops; self.src = src; self.cls = "ctrl"


class ACO(Protocol):
    name = "ACO-WBAN"

    def __init__(self, eng, ant_period=1.0, beta_data=5.0, beta_ant=1.0, gamma=0.7, T_hop=0.002,
                 fail_evap=0.5, **kw):
        super().__init__(eng, **kw)
        self.ant_period = ant_period; self.bd = beta_data; self.ba = beta_ant
        self.gamma = gamma; self.T_hop = T_hop; self.fail_evap = fail_evap
        self.T = [dict() for _ in eng.nodes]

    def start(self):
        for n in self.eng.nodes[:-1]:
            self.timer(self.rng.uniform(0.0, self.ant_period), "ant", n)

    def _table(self, node, pkt=None):
        T = self.T[node.id]
        cs = self.cands(node, pkt)
        for j in cs:
            if j not in T:
                T[j] = 1.0 / (self.T_hop * (1 + (node.nbr[j][1] if j in node.nbr else 0)))
        return cs, T

    def _choose(self, node, cs, T, beta, exclude=None):
        keys = [j for j in cs if j != exclude] or cs
        ws = [T[j] ** beta for j in keys]
        s = sum(ws)
        if s <= 0:
            return keys[0]
        r = self.rng.random() * s; acc = 0.0
        for k, w in zip(keys, ws):
            acc += w
            if r <= acc:
                return k
        return keys[-1]

    def select_next_hop(self, node, pkt):
        cs, T = self._table(node, pkt)
        return self._choose(node, cs, T, self.bd)

    def on_hop_fail(self, node, pkt):
        T = self.T[node.id]
        if pkt.nh in T:
            T[pkt.nh] *= self.fail_evap
        cs, T = self._table(node, pkt)
        if len(cs) <= 1 and cs[0] == pkt.nh:
            return None
        return self._choose(node, cs, T, self.bd, exclude=pkt.nh)

    def on_timer(self, tag, node):
        if tag == "ant" and node is not None and node.alive:
            cs, T = self._table(node, _AntPkt(0, node.id))
            nh = self._choose(node, cs, T, self.ba)
            self.eng.send_ctrl(node, "fant", {"path": [(node.id, self.eng.t)], "orig": node.id}, 16, dest=nh)
            self.timer(self.ant_period, "ant", node)

    def on_ctrl_rx(self, node, pkt, sender, rssi):
        eng = self.eng; p = pkt.payload
        if pkt.ctype == "fant":
            path = p["path"] + [(node.id, eng.t)]
            if node.is_gw:
                # backward ant retraces the path
                eng.send_ctrl(node, "bant", {"path": path, "idx": len(path) - 2}, 24, dest=path[-2][0])
            elif node.malicious:
                return
            else:
                cs, T = self._table(node, _AntPkt(len(path) - 1, p["orig"]))
                nh = self._choose(node, cs, T, self.ba)
                eng.send_ctrl(node, "fant", {"path": path, "orig": p["orig"]}, 16, dest=nh)
        elif pkt.ctype == "bant":
            path = p["path"]; idx = p["idx"]
            if path[idx][0] != node.id:
                return
            t_leave = path[idx][1]; t_arrive_gw = path[-1][1]
            h = len(path) - 1 - idx
            tau = 1.0 / (max(t_arrive_gw - t_leave, 1e-4) + h * self.T_hop)
            nxt = path[idx + 1][0]
            T = self.T[node.id]
            T[nxt] = self.gamma * T.get(nxt, tau) + (1 - self.gamma) * tau
            if idx > 0:
                eng.send_ctrl(node, "bant", {"path": path, "idx": idx - 1}, 24, dest=path[idx - 1][0])

    def on_ctrl_result(self, node, pkt, nh, ok, rssi):
        if not ok and pkt.ctype in ("fant", "bant"):
            T = self.T[node.id]
            if nh in T:
                T[nh] *= self.fail_evap


# ===========================================================================
# Centralised metaheuristic relay assignment (PSO / GWO)
# ===========================================================================
class MetaRelay(Protocol):
    name = "PSO-Relay"

    def __init__(self, eng, optimizer="pso", period=5.0, pop=20, iters=40, weights=(0.4, 0.3, 0.3), **kw):
        super().__init__(eng, **kw)
        self.optimizer = optimizer; self.period = period; self.pop = pop; self.iters = iters
        self.w = weights
        self.parent = [GW] * len(eng.nodes)
        self.info = {}      # gateway's knowledge: node -> (hops, energy)
        self.orng = np.random.default_rng([eng.cfg.seed, 99])
        # mean link success from the CM3 mean path loss at known positions
        PL = ch.ChannelParams.a * np.log10(eng.d_mm) + ch.ChannelParams.b
        ncw = eng.ncw_data
        self.pmean = np.exp(ncw * eng.per.log_success_per_codeword(eng.cfg.tx_power_dBm - PL))
        self.e_tx = np.full(eng.d_mm.shape, eng.p_tx * eng.T_data)
        self.e_rx = eng.p_rx * eng.T_data

    def start(self):
        self.timer(0.4, "opt")

    def on_beacon(self, node, sender, payload, rssi):
        if node.is_gw:
            self.info[sender.id] = (payload["hops"], payload["energy"])

    def _options(self):
        eng = self.eng
        alive = [n for n in eng.nodes[:-1] if n.alive]
        opts = {}
        for n in alive:
            if n.crit >= 0.85:
                opts[n.id] = [GW]        # critical sources transmit directly and never relay
                continue
            h = self.info.get(n.id, (1, 1.0))[0]
            o = [GW] + [m.id for m in alive if m.id != n.id and m.crit < 0.85
                        and self.info.get(m.id, (99, 1.0))[0] <= h]
            opts[n.id] = o
        return alive, opts

    def _fitness(self, x, ids, opts, rates, eres):
        w1, w2, w3 = self.w
        load = {i: 0.0 for i in ids}
        e_cost = 0.0; loss = 0.0; rsum = sum(rates.values())
        par = {}
        for k, i in enumerate(ids):
            p = opts[i][int(x[k])]
            par[i] = p
            load[i] += rates[i] * self.e_tx[i, p]
            e_cost += rates[i] * self.e_tx[i, p]
            loss += rates[i] * (1.0 - self.pmean[i, p])
        for i, p in par.items():
            if p != GW:
                load[p] += rates[i] * (self.e_rx + self.e_tx[p, par.get(p, GW)])
                loss += rates[i] * (1.0 - self.pmean[p, par.get(p, GW)])
        drain = max(load[i] / max(eres[i], 1e-3) for i in ids)
        return w1 * drain / 1e-3 + w2 * e_cost / (rsum * self.e_tx.max()) + w3 * loss / rsum

    def on_timer(self, tag, node):
        if tag != "opt":
            return
        eng = self.eng
        alive, opts = self._options()
        ids = [n.id for n in alive]
        rates = {n.id: n.rate for n in alive}
        eres = {n.id: max(self.info.get(n.id, (1, 1.0))[1], 0.01) * eng.cfg.e0 for n in alive}
        K = np.array([len(opts[i]) for i in ids], dtype=float)
        dim = len(ids)
        rng = self.orng
        if dim > 0:
            f = lambda x: self._fitness(np.minimum(np.floor(np.clip(x, 0, K - 1e-9)), K - 1), ids, opts, rates, eres)
            X = rng.uniform(0, K, (self.pop, dim))
            X[0] = 0.0                       # all-direct assignment as a seed
            F = np.array([f(x) for x in X])
            if self.optimizer == "pso":
                V = np.zeros_like(X); P = X.copy(); PF = F.copy()
                g = int(PF.argmin()); G = P[g].copy(); GF = PF[g]
                for it in range(self.iters):
                    w_in = 0.9 - 0.7 * it / max(1, self.iters - 1)
                    r1 = rng.random((self.pop, dim)); r2 = rng.random((self.pop, dim))
                    V = w_in * V + 1.5 * r1 * (P - X) + 1.5 * r2 * (G - X)
                    X = np.clip(X + V, 0, K - 1e-9)
                    F = np.array([f(x) for x in X])
                    imp = F < PF
                    P[imp] = X[imp]; PF[imp] = F[imp]
                    g = int(PF.argmin())
                    if PF[g] < GF:
                        G = P[g].copy(); GF = PF[g]
                best = G
            else:  # GWO (Mirjalili et al. 2014)
                for it in range(self.iters):
                    a = 2.0 - 2.0 * it / max(1, self.iters - 1)
                    order = np.argsort(F)
                    leaders = (X[order[0]], X[order[1]], X[order[2]])
                    Xn = np.zeros_like(X)
                    for lead in leaders:
                        r1 = rng.random((self.pop, dim)); r2 = rng.random((self.pop, dim))
                        A = 2 * a * r1 - a; C = 2 * r2
                        Xn += lead - A * np.abs(C * lead - X)
                    X = np.clip(Xn / 3.0, 0, K - 1e-9)
                    F = np.array([f(x) for x in X])
                best = X[int(F.argmin())]
            assign = {i: opts[i][int(min(math.floor(best[k]), len(opts[i]) - 1))] for k, i in enumerate(ids)}
            eng.send_ctrl(eng.gw, "assign", {"assign": assign}, 40, dest=BROADCAST, front=True)
        self.timer(self.period, "opt")

    def on_ctrl_rx(self, node, pkt, sender, rssi):
        if pkt.ctype == "assign" and node.id in pkt.payload["assign"]:
            self.parent[node.id] = pkt.payload["assign"][node.id]

    def select_next_hop(self, node, pkt):
        if pkt.cls in ("crit", "alarm"):
            return GW
        p = self.parent[node.id]
        if p != GW and (not self.eng.nodes[p].alive or p == pkt.src):
            return GW
        return p

    def on_hop_fail(self, node, pkt):
        return GW if pkt.nh != GW else None


class PSORelay(MetaRelay):
    name = "PSO-Relay"

    def __init__(self, eng, **kw):
        super().__init__(eng, optimizer="pso", **kw)


class GWORelay(MetaRelay):
    name = "GWO-Relay"

    def __init__(self, eng, **kw):
        super().__init__(eng, optimizer="gwo", **kw)


# ===========================================================================
# Q-routing (QL-WBAN)
# ===========================================================================
class QLWBAN(Protocol):
    name = "QL-WBAN"

    def __init__(self, eng, eta=0.5, eps=0.05, penalty=0.05, zeta=0.005, T_hop=0.003, **kw):
        super().__init__(eng, **kw)
        self.eta, self.eps, self.penalty, self.zeta, self.T_hop = eta, eps, penalty, zeta, T_hop
        self.Q = [dict() for _ in eng.nodes]
        for n in eng.nodes:
            n.state["bestQ"] = 0.0 if n.is_gw else 0.01

    def _table(self, node, pkt=None):
        Q = self.Q[node.id]
        cs = self.cands(node, pkt)
        for j in cs:
            if j not in Q:
                Q[j] = self.T_hop * (1 + (node.nbr[j][1] if j in node.nbr else 0))
        return cs, Q

    def _best(self, node, cs, Q, exclude=None):
        keys = [j for j in cs if j != exclude] or cs
        return min(keys, key=lambda j: Q[j])

    def select_next_hop(self, node, pkt):
        cs, Q = self._table(node, pkt)
        if len(cs) > 1 and self.rng.random() < self.eps:
            return cs[int(self.rng.integers(len(cs)))]
        return self._best(node, cs, Q)

    def on_hop_fail(self, node, pkt):
        cs, Q = self._table(node, pkt)
        Q[pkt.nh] += self.eta * (self.penalty - Q[pkt.nh])
        node.state["bestQ"] = min(Q[j] for j in cs)
        if len(cs) <= 1 and cs[0] == pkt.nh:
            return None
        return self._best(node, cs, Q, exclude=pkt.nh)

    def on_tx_result(self, node, pkt, nh, ok, rssi, t_service, rx):
        self._lq_update(node, nh, ok)
        cs, Q = self._table(node, pkt)
        if ok:
            t_next = 0.0 if rx.is_gw else (0.0 if rx.malicious else rx.state.get("bestQ", 0.01))
            R = node.nbr[nh][2] if nh in node.nbr else 1.0
            target = t_service + t_next + self.zeta * (1.0 - R)
            Q[nh] += self.eta * (target - Q[nh])
        node.state["bestQ"] = min(Q[j] for j in cs)


# ===========================================================================
# QoS-2C (DMQoS / QPRD / ZEQoS-style two-class routing)
# ===========================================================================
class QoS2C(Protocol):
    name = "QoS-2C"

    def __init__(self, eng, R_req=0.9, **kw):
        super().__init__(eng, **kw)
        self.R_req = R_req
        self.delay_est = [0.003] * len(eng.nodes)   # own hop service-time estimate
        self.path_delay = [0.0] * len(eng.nodes)

    def advertised_cost(self, node):
        return self.path_delay[node.id]

    def _path_delay(self, node, j):
        adv = 0.0 if j == GW else node.nbr[j][3]
        return self.delay_est[node.id] + adv

    def _pick(self, node, pkt, exclude=None):
        cs = [j for j in self.cands(node, pkt) if j != exclude] or self.cands(node, pkt)
        if pkt.cls in ("crit", "alarm"):
            ok = [j for j in cs if self.lq_get(node, j) >= self.R_req]
            if ok:
                return min(ok, key=lambda j: self._path_delay(node, j))
            return max(cs, key=lambda j: self.lq_get(node, j))
        d = self.eng.d_mm
        closer = [j for j in cs if j == GW or d[j, GW] < d[node.id, GW]] or cs
        def cost(j):
            E = 1.0 if j == GW else max(node.nbr[j][2], 0.01)
            return (d[node.id, j] ** 2) / E
        return min(closer, key=cost)

    def select_next_hop(self, node, pkt):
        nh = self._pick(node, pkt)
        return nh

    def on_hop_fail(self, node, pkt):
        cs = self.cands(node, pkt)
        if len(cs) <= 1 and cs[0] == pkt.nh:
            return None
        return self._pick(node, pkt, exclude=pkt.nh)

    def on_tx_result(self, node, pkt, nh, ok, rssi, t_service, rx):
        self._lq_update(node, nh, ok, a=0.4)
        if ok:
            self.delay_est[node.id] = 0.8 * self.delay_est[node.id] + 0.2 * t_service
            adv = 0.0 if nh == GW else node.nbr[nh][3]
            self.path_delay[node.id] = self.delay_est[node.id] + adv


# ===========================================================================
# registry
# ===========================================================================
def make_protocol(name, eng, **kw):
    table = {
        "PhysaRoute": PhysaRoute, "AODV": AODV, "M-ATTEMPT": MATTEMPT, "SIMPLE": SIMPLE,
        "ACO-WBAN": ACO, "PSO-Relay": PSORelay, "GWO-Relay": GWORelay, "QL-WBAN": QLWBAN,
        "QoS-2C": QoS2C,
    }
    if name in table:
        return table[name](eng, **kw)
    # PhysaRoute ablations
    if name == "PR-noEnergy":
        return PhysaRoute(eng, beta=(0.0, 0.30 / 0.65, 0.20 / 0.65, 0.15 / 0.65), lambda_E=0.0, **kw)
    if name == "PR-noShadow":
        return PhysaRoute(eng, beta=(0.35 / 0.8, 0.30 / 0.8, 0.0, 0.15 / 0.8), use_shadow=False, **kw)
    if name == "PR-noCrit":
        return PhysaRoute(eng, beta=(0.35 / 0.85, 0.30 / 0.85, 0.20 / 0.85, 0.0), kappa_crit=2.0, lambda_c=0.0, **kw)
    if name == "PR-noExplore":
        return PhysaRoute(eng, use_probe=False, **kw)
    if name == "PR-noE2E":
        return PhysaRoute(eng, use_e2e=False, **kw)
    raise KeyError(name)


PROTOCOLS = ["PhysaRoute", "QL-WBAN", "QoS-2C", "ACO-WBAN", "PSO-Relay", "GWO-Relay",
             "SIMPLE", "M-ATTEMPT", "AODV"]
ABLATIONS = ["PhysaRoute", "PR-noEnergy", "PR-noShadow", "PR-noCrit", "PR-noExplore"]
