"""
Discrete-event core of the PhysaRoute WBAN simulator.

The engine models, per run:
  * 12 body-worn sensors + 1 belt-worn gateway (see channel.SENSORS);
  * per-sensor Poisson traffic with clinical criticality classes;
  * a window-sampled dynamic body channel (channel.generate_channel);
  * IEEE 802.15.6 CSMA/CA with user-priority contention windows, carrier
    sensing, collisions, immediate ACKs and retransmissions (single collision
    domain: all on-body nodes are within carrier-sense range);
  * a first-order radio energy model (TX/RX airtime x nRF52840 currents);
  * a common control substrate shared by every routing protocol: a gateway
    beacon flooded once per beacon period that gives every node its hop
    distance to the gateway, its neighbour table (RSSI, hops, residual
    energy) and, optionally, end-to-end delivery receipts;
  * pluggable routing protocols (physaroute.protocols) that decide the next
    hop of every frame and react to per-hop outcomes.
"""
from __future__ import annotations

import heapq
import math
from collections import deque

import zlib

import numpy as np

from . import channel as ch

# event codes
EV_GEN, EV_ATTEMPT, EV_TXEND, EV_WINDOW, EV_BEACON, EV_TIMER, EV_ALARM, EV_REBCAST = range(8)
BROADCAST = -1
HOLD = "hold"          # keep at queue head, wait for protocol kick()
HOLD_BACK = "hold_back"  # re-queue at the tail, protocol kicks later
SKIP = "skip"          # this packet is not eligible yet; serve the next one

# CSMA/CA contention windows per class (IEEE 802.15.6 Table 20)
CW_TABLE = {  # class: (CWmin, CWmax)
    "data": (8, 32),      # UP2/UP3
    "crit": (4, 8),       # UP5 medical data
    "alarm": (1, 4),      # UP7 emergency / medical event report
    "ctrl": (4, 8),       # UP5 network control
}
T_CCA = 105e-6            # pCCATime: transmissions starting closer than this collide

DATA_BODY_BYTES = 87      # 87 B body + 7 B MAC header + 2 B FCS = 96 B PSDU
ACK_BODY_BYTES = 0


class Packet:
    __slots__ = ("pid", "src", "t_gen", "cls", "kind", "ctype", "payload", "body", "hops",
                 "attempts", "holder", "nh", "reroutes", "t_enq", "t_first_tx", "bcast", "via",
                 "wait_until")

    def __init__(self, pid, src, t_gen, cls="data", kind="data", ctype=None, payload=None,
                 body=DATA_BODY_BYTES, bcast=False):
        self.pid = pid; self.src = src; self.t_gen = t_gen; self.cls = cls
        self.kind = kind; self.ctype = ctype; self.payload = payload; self.body = body
        self.hops = 0; self.attempts = 0; self.holder = src; self.nh = None
        self.reroutes = 0; self.t_enq = t_gen; self.t_first_tx = None; self.bcast = bcast
        self.via = None   # first hop chosen by the source (for e2e receipts)
        self.wait_until = -1.0

    def clone(self):
        """Copy taken by a receiver: the sender keeps its own object for retries,
        so a lost ACK followed by a re-route creates two genuine duplicates."""
        c = Packet(self.pid, self.src, self.t_gen, self.cls, self.kind, self.ctype, self.payload,
                   self.body, self.bcast)
        c.hops = self.hops; c.attempts = self.attempts; c.via = self.via; c.reroutes = 0
        return c


class Node:
    __slots__ = ("id", "name", "crit", "w", "energy", "e0", "alive", "queue", "mac_state", "cw",
                 "retries", "att_token", "hops", "nbr", "seen", "malicious", "is_gw",
                 "n_tx", "n_rx", "dead_at", "state", "cost_to_sink", "last_beacon_seq",
                 "queue_cap", "tx_group", "gen_next", "rate", "sent_seq", "e2e_bitmap", "cur", "rng_traffic")

    def __init__(self, nid, name, crit, w, e0, is_gw=False):
        self.id = nid; self.name = name; self.crit = crit; self.w = w
        self.energy = e0; self.e0 = e0; self.alive = True; self.queue = deque()
        self.mac_state = 0; self.cw = 8; self.retries = 0; self.att_token = 0
        self.hops = 99; self.nbr = {}; self.seen = set(); self.malicious = False; self.is_gw = is_gw
        self.n_tx = 0; self.n_rx = 0; self.dead_at = None; self.state = {}
        self.cost_to_sink = 1e9; self.last_beacon_seq = -1; self.queue_cap = 32
        self.tx_group = None; self.gen_next = 0.0; self.rate = 0.0; self.sent_seq = 0
        self.e2e_bitmap = 0
        self.cur = None
        self.rng_traffic = None


class RunConfig:
    """All knobs of one simulation run (defaults = manuscript operating point)."""
    def __init__(self, **kw):
        self.velocity = 1.0            # m/s
        self.load = 80.0               # aggregate packets/s
        self.duration = 200.0          # s
        self.warmup = 20.0             # s excluded from statistics
        self.window = 0.100            # s
        self.e0 = 0.5                  # J routing-radio budget per sensor
        self.beacon_period = 2.0       # s
        self.max_retries = 3           # per hop (4 attempts)
        self.max_reroutes = 3          # per hop
        self.max_attempts = 24         # per packet
        self.ttl = 2.0                 # s, packet lifetime (stale samples are discarded)
        self.ble_airtime = 0.0         # fraction of frames hit by a co-channel BLE burst
        self.ble_loss = 0.9            # P(loss | hit)
        self.jam_node = -1             # node index near a persistent jammer
        self.jam_loss = 0.9
        self.malicious = ()            # blackhole (Sybil-style) relay node ids
        self.alarm_rate = 0.0          # alarm bursts / s (ICU scenario)
        self.alarm_burst = 3
        self.trace_node = -1           # node whose routing state is logged every window
        self.energy_sample_s = 0.0     # >0: record mean residual energy every this many seconds
        self.seed = 0
        self.protocol = "PhysaRoute"
        self.proto_kw = {}
        self.channel_trace = None
        self.tx_power_dBm = -10.0
        for k, v in kw.items():
            if not hasattr(self, k):
                raise KeyError(k)
            setattr(self, k, v)


class Engine:
    def __init__(self, cfg: RunConfig, protocol_factory):
        self.cfg = cfg
        self.t = 0.0
        self.heap = []
        self.seq = 0
        # Common random numbers.  Everything a protocol cannot influence -- placement,
        # channel realisation and fades (rng_env), packet arrivals (one stream per
        # source, rng_traffic) and alarm events (rng_alarm) -- is drawn from streams
        # seeded by the environment seed only, so every protocol sees the identical
        # environment for the same seed and comparisons are paired.  Randomness whose
        # consumption depends on the protocol (backoff, PER draws, interference,
        # re-broadcast jitter, protocol sampling) uses rng_mac, seeded with a
        # deterministic hash of the protocol name (bit-reproducible across runs).
        self.rng_env = np.random.default_rng([cfg.seed, 11])
        self.rng_alarm = np.random.default_rng([cfg.seed, 13])
        self.rng_mac = np.random.default_rng([cfg.seed, 23, zlib.crc32(cfg.protocol.encode()) % 10007])
        self.per = ch.PERModel()
        cp = ch.ChannelParams(); cp.tx_power_dBm = cfg.tx_power_dBm
        logS, PL, d_mm = ch.generate_channel(self.rng_env, cfg.velocity, cfg.duration, cfg.window,
                                             self.per, cp, cfg.channel_trace)
        self.logS = logS.tolist()
        self.PL = PL
        self.d_mm = d_mm
        self.n_windows = len(self.logS)
        self.w = 0
        self.ncw_data = ch.psdu_codewords(DATA_BODY_BYTES)
        self.ncw_ack = ch.psdu_codewords(ACK_BODY_BYTES)
        self.T_data = ch.frame_airtime(DATA_BODY_BYTES)
        self.T_ack = ch.T_ACK
        self.p_tx = ch.p_tx_W(cfg.tx_power_dBm)
        self.p_rx = ch.P_RX_W
        self.sens_dBm = self.per.sensitivity_dBm(DATA_BODY_BYTES, 0.10)
        # nodes
        self.nodes = []
        wsum = sum(s[2] for s in ch.SENSORS)
        for i, (name, crit, w, _e, _p) in enumerate(ch.SENSORS):
            n = Node(i, name, crit, w, cfg.e0)
            n.rate = cfg.load * w / wsum
            n.rng_traffic = np.random.default_rng([cfg.seed, 12, i])
            self.nodes.append(n)
        gw = Node(ch.GATEWAY, "Gateway", 0.0, 0.0, 1e9, is_gw=True)
        gw.hops = 0; gw.cost_to_sink = 0.0
        self.nodes.append(gw)
        self.gw = gw
        for m in cfg.malicious:
            self.nodes[m].malicious = True
        # medium state
        self.medium_free_at = 0.0
        self.tx_group_start = -1.0
        self.tx_group = []
        # statistics
        self.pid_counter = 0
        self.stats = {
            "generated": 0, "delivered": 0, "dropped": {}, "lat": [], "lat_cls": {},
            "gen_cls": {}, "del_cls": {}, "ctrl_frames": 0, "ctrl_bytes": 0, "data_tx": 0,
            "data_retx": 0, "collisions": 0, "alarm_lat": [], "alarms": 0, "alarms_missed": 0,
            "delivered_payload_bits": 0, "hops_sum": 0, "e2e_attempts": 0,
        }
        self.trace = []
        self.beacon_seq = 0
        self.e2e_receipts = {}        # src -> bitmap of delivered seq numbers in last beacon period
        self.proto = protocol_factory(self)
        self.proto.name = cfg.protocol

    # ------------------------------------------------------------------ utils
    def now(self):
        return self.t

    def push(self, t, code, nid=-1, payload=None):
        self.seq += 1
        heapq.heappush(self.heap, (t, self.seq, code, nid, payload))

    def rssi(self, i, j):
        """Mean received power (dBm) on link i-j in the current window."""
        w = self.w if self.w < self.n_windows else self.n_windows - 1
        return self.cfg.tx_power_dBm - float(self.PL[w, i, j])

    def link_p(self, i, j, ncw):
        w = self.w if self.w < self.n_windows else self.n_windows - 1
        return math.exp(ncw * self.logS[w][i][j])

    def alive_sensors(self):
        return [n for n in self.nodes[:-1] if n.alive]

    def new_pid(self):
        self.pid_counter += 1
        return self.pid_counter

    # -------------------------------------------------------------- traffic
    def _schedule_gen(self, node):
        node.gen_next = self.t + node.rng_traffic.exponential(1.0 / node.rate)
        self.push(node.gen_next, EV_GEN, node.id)

    def generate(self, node, cls=None, t=None):
        if not node.alive:
            return
        cls = cls or ("crit" if node.crit >= 0.85 else "data")
        pkt = Packet(self.new_pid(), node.id, self.t if t is None else t, cls=cls)
        node.sent_seq += 1
        pkt.payload = node.sent_seq
        if self.t >= self.cfg.warmup:
            self.stats["generated"] += 1
            self.stats["gen_cls"][cls] = self.stats["gen_cls"].get(cls, 0) + 1
        self.enqueue(node, pkt)

    def enqueue(self, node, pkt, front=False):
        if not node.alive:
            self.drop(pkt, "dead_holder"); return
        if len(node.queue) >= node.queue_cap and pkt.kind == "data":
            self.drop(pkt, "overflow"); return
        pkt.holder = node.id; pkt.t_enq = self.t; pkt.nh = None
        if front:
            node.queue.appendleft(pkt)
        else:
            node.queue.append(pkt)
        self.try_start(node)

    def send_ctrl(self, node, ctype, payload, body_bytes, dest=BROADCAST, cls="ctrl", front=False):
        pkt = Packet(self.new_pid(), node.id, self.t, cls=cls, kind="ctrl", ctype=ctype,
                     payload=payload, body=body_bytes, bcast=(dest == BROADCAST))
        pkt.nh = dest
        if not node.alive:
            return
        pkt.holder = node.id; pkt.t_enq = self.t
        if front:
            node.queue.appendleft(pkt)
        else:
            node.queue.append(pkt)
        self.try_start(node)

    def drop(self, pkt, reason):
        if pkt.kind == "data" and pkt.t_gen >= self.cfg.warmup:
            self.stats["dropped"][reason] = self.stats["dropped"].get(reason, 0) + 1
        if pkt.kind == "data" and pkt.cls == "alarm":
            self._alarm_outcome(pkt, delivered=False)

    # ------------------------------------------------------------------ MAC
    def _remove(self, node, pkt):
        try:
            node.queue.remove(pkt)
        except ValueError:
            pass

    def try_start(self, node):
        """Serve the first eligible frame: control frames may bypass data
        packets that are held waiting for a route; data stays FIFO."""
        if node.mac_state != 0 or not node.alive:
            return
        held = False
        for pkt in list(node.queue):
            if pkt.kind == "data":
                if pkt.attempts >= self.cfg.max_attempts:
                    self._remove(node, pkt); self.drop(pkt, "attempts"); continue
                if self.t - pkt.t_gen > self.cfg.ttl:
                    self._remove(node, pkt); self.drop(pkt, "expired"); continue
                if held:
                    continue
                if pkt.nh is None:
                    nh = self.proto.select_next_hop(node, pkt)
                    if nh == HOLD:
                        held = True
                        continue                     # protocol will kick() later
                    if nh == SKIP:
                        continue                     # not eligible yet; others may go
                    if nh is None:
                        self._remove(node, pkt); self.drop(pkt, "no_route"); continue
                    pkt.nh = nh
                    if pkt.holder == pkt.src and pkt.via is None:
                        pkt.via = nh
            # start contention for this frame
            node.cur = pkt
            node.mac_state = 1
            node.cw = CW_TABLE[pkt.cls][0]
            node.retries = 0
            self._schedule_attempt(node)
            return

    def kick(self, node):
        """Protocol signals that a held packet can now be routed."""
        if node.mac_state == 0 and node.queue and node.alive:
            self.try_start(node)

    def _schedule_attempt(self, node):
        k = int(self.rng_mac.integers(1, node.cw + 1))
        base = self.t if self.t > self.medium_free_at else self.medium_free_at
        t_att = base + ch.P_SIFS + k * ch.SLOT
        node.att_token += 1
        self.push(t_att, EV_ATTEMPT, node.id, node.att_token)

    def _attempt(self, node, token):
        if token != node.att_token or node.mac_state != 1 or not node.alive or node.cur is None:
            return
        pkt = node.cur
        # carrier sense
        if self.t < self.medium_free_at - 1e-12:
            if self.tx_group_start >= 0.0 and (self.t - self.tx_group_start) < T_CCA:
                self._start_tx(node, pkt, collide=True)
            else:
                self._schedule_attempt(node)
            return
        self._start_tx(node, pkt, collide=False)

    def _start_tx(self, node, pkt, collide):
        node.mac_state = 2
        T_f = self.T_data if pkt.kind == "data" else ch.frame_airtime(pkt.body)
        unicast = not pkt.bcast
        T_txn = T_f + (ch.P_SIFS + self.T_ack if unicast else 0.0)
        if collide:
            self.stats["collisions"] += 1
            for other in self.tx_group:
                other[2] = True
            self.tx_group.append([node.id, pkt, True])
            end = max(self.medium_free_at, self.t + T_txn)
        else:
            self.tx_group_start = self.t
            self.tx_group = [[node.id, pkt, False]]
            end = self.t + T_txn
        self.medium_free_at = end
        node.energy -= self.p_tx * T_f
        node.n_tx += 1
        pkt.attempts += 1
        if pkt.kind == "data":
            self.stats["data_tx"] += 1
            if pkt.t_first_tx is None:
                pkt.t_first_tx = self.t
            elif node.retries > 0:
                self.stats["data_retx"] += 1
        else:
            self.stats["ctrl_frames"] += 1
            self.stats["ctrl_bytes"] += pkt.body + ch.MAC_HDR_BYTES + ch.FCS_BYTES
        self.push(self.t + T_txn, EV_TXEND, node.id, (pkt, T_f, len(self.tx_group) - 1))

    def _frame_ok(self, i, j, body_bytes, ncw=None):
        cfg = self.cfg
        if ncw is None:
            ncw = ch.psdu_codewords(body_bytes)
        p = self.link_p(i, j, ncw)
        if cfg.ble_airtime > 0.0 and self.rng_mac.random() < cfg.ble_airtime:
            p *= (1.0 - cfg.ble_loss)
        if cfg.jam_node >= 0 and (i == cfg.jam_node or j == cfg.jam_node):
            p *= (1.0 - cfg.jam_loss)
        return self.rng_mac.random() < p

    def _txend(self, node, payload):
        pkt, T_f, idx = payload
        entry = self.tx_group[idx] if idx < len(self.tx_group) and self.tx_group[idx][0] == node.id else None
        collided = entry[2] if entry is not None else False
        # node stays 'busy' (state 2) during protocol callbacks so that control
        # frames they enqueue are served by the final try_start() below
        if pkt.bcast:
            for rx in self.nodes:
                if rx.id == node.id or not rx.alive:
                    continue
                rx.energy -= self.p_rx * T_f
                if not collided and self._frame_ok(node.id, rx.id, pkt.body):
                    self._deliver_ctrl(rx, pkt, node)
            self._remove(node, pkt); node.cur = None
            self._check_dead(node)
            node.mac_state = 0
            self.try_start(node)
            return
        j = pkt.nh
        rx = self.nodes[j]
        ok = False
        if rx.alive:
            rx.energy -= self.p_rx * T_f
            if not collided and self._frame_ok(node.id, j, pkt.body):
                # receiver got the frame; it replies with an I-Ack
                rx.energy -= self.p_tx * self.T_ack
                node.energy -= self.p_rx * self.T_ack
                ack_ok = self._frame_ok(j, node.id, ACK_BODY_BYTES, self.ncw_ack)
                key = (pkt.src, pkt.pid)
                dup = key in rx.seen
                if not dup:
                    rx.seen.add(key)
                    if len(rx.seen) > 4096:
                        rx.seen = set(list(rx.seen)[-2048:])
                    self._receive(rx, pkt, node)
                ok = ack_ok
        rssi = self.rssi(node.id, j)
        t_service = self.t - pkt.t_enq
        if pkt.kind == "data":
            self.proto.on_tx_result(node, pkt, j, ok, rssi, t_service, rx)
        else:
            self.proto.on_ctrl_result(node, pkt, j, ok, rssi)
        if ok:
            self._remove(node, pkt); node.cur = None
            self._check_dead(node); self._check_dead(rx)
            node.mac_state = 0
            self.try_start(node)
            return
        # failure: retry, re-route or drop
        node.retries += 1
        if node.retries <= self.cfg.max_retries and pkt.attempts < self.cfg.max_attempts:
            node.cw = min(node.cw * 2, CW_TABLE[pkt.cls][1])
            node.mac_state = 1
            self._schedule_attempt(node)
            self._check_dead(node)
            return
        if pkt.kind == "data":
            nh = self.proto.on_hop_fail(node, pkt) if pkt.reroutes < self.cfg.max_reroutes else None
            if nh is not None and nh not in (HOLD, HOLD_BACK) and pkt.attempts < self.cfg.max_attempts:
                pkt.nh = nh; pkt.reroutes += 1
                node.retries = 0; node.cw = CW_TABLE[pkt.cls][0]; node.mac_state = 1
                self._schedule_attempt(node)
                self._check_dead(node)
                return
            self._remove(node, pkt); node.cur = None
            if nh in (HOLD, HOLD_BACK):
                pkt.nh = None
                self.enqueue(node, pkt, front=(nh == HOLD))
                self._check_dead(node)
                node.mac_state = 0
                self.try_start(node)
                return
            self.drop(pkt, "hop_fail")
        else:
            self._remove(node, pkt); node.cur = None
            self.proto.on_ctrl_fail(node, pkt)
        self._check_dead(node)
        node.mac_state = 0
        self.try_start(node)

    def _receive(self, rx, pkt, sender):
        rx.n_rx += 1
        if pkt.kind == "ctrl":
            self._deliver_ctrl(rx, pkt, sender)
            return
        if rx.is_gw:
            pkt.hops += 1
            self._delivered(pkt)
            return
        if rx.malicious:
            self.stats["blackholed"] = self.stats.get("blackholed", 0) + 1
            return                               # silently discarded by the blackhole
        c = pkt.clone(); c.hops += 1
        self.enqueue(rx, c)

    def _deliver_ctrl(self, rx, pkt, sender):
        rssi = self.rssi(sender.id, rx.id)
        if pkt.ctype == "beacon":
            self._on_beacon_rx(rx, pkt, sender, rssi)
        else:
            self.proto.on_ctrl_rx(rx, pkt, sender, rssi)

    def _delivered(self, pkt):
        if pkt.t_gen >= self.cfg.warmup:
            s = self.stats
            s["delivered"] += 1
            lat = self.t - pkt.t_gen
            s["lat"].append(lat)
            s["lat_cls"].setdefault(pkt.cls, []).append(lat)
            s["del_cls"][pkt.cls] = s["del_cls"].get(pkt.cls, 0) + 1
            s["delivered_payload_bits"] += pkt.body * 8
            s["hops_sum"] += pkt.hops
        if pkt.cls == "alarm":
            self._alarm_outcome(pkt, delivered=True)
        # end-to-end receipt bookkeeping (bitmap of the last 32 sequence numbers)
        src = pkt.src
        bm = self.e2e_receipts.get(src, 0)
        self.e2e_receipts[src] = bm | (1 << (pkt.payload % 64))
        self.proto.on_delivered(pkt)

    def _check_dead(self, node):
        if node.alive and node.energy <= 0.0 and not node.is_gw:
            node.alive = False
            node.dead_at = self.t
            while node.queue:
                self.drop(node.queue.popleft(), "dead_holder")
            node.mac_state = 0; node.cur = None
            self.proto.on_node_dead(node)

    # --------------------------------------------------------------- beacons
    def _send_beacon(self):
        gw = self.gw
        self.beacon_seq += 1
        want = getattr(self.proto, "wants_receipts", False)
        payload = {"seq": self.beacon_seq, "hops": 0, "energy": 1.0, "cost": 0.0,
                   "receipts": dict(self.e2e_receipts) if want else {}, "origin": gw.id}
        self.e2e_receipts = {}
        body = 16 + 8 * len(payload["receipts"])
        self.send_ctrl(gw, "beacon", payload, body, front=True)
        self.push(self.t + self.cfg.beacon_period, EV_BEACON)

    def _on_beacon_rx(self, rx, pkt, sender, rssi):
        p = pkt.payload
        # neighbour table: (rssi_ewma, hops, residual-energy fraction, cost_to_sink, t_last)
        old = rx.nbr.get(sender.id)
        r = rssi if old is None else 0.7 * old[0] + 0.3 * rssi
        adv_hops = 1 if sender.malicious else p["hops"]
        rx.nbr[sender.id] = (r, adv_hops, p["energy"], p["cost"], self.t)
        if rx.is_gw:
            self.proto.on_beacon(rx, sender, p, rssi)
            return
        if p["seq"] > rx.last_beacon_seq:
            rx.last_beacon_seq = p["seq"]
            rx.hops = adv_hops + 1
            if p["origin"] == self.gw.id:
                rx.state["_receipts"] = p["receipts"].get(rx.id, 0)
                self.proto.on_receipts(rx, p["receipts"].get(rx.id, 0))
            # re-broadcast once after a short random delay
            self.push(self.t + self.rng_mac.uniform(0.002, 0.030), EV_REBCAST, rx.id, p["seq"])
        elif adv_hops + 1 < rx.hops:
            rx.hops = adv_hops + 1
        self.proto.on_beacon(rx, sender, p, rssi)

    def _rebroadcast(self, node, seq):
        if not node.alive or seq != node.last_beacon_seq:
            return
        cost = self.proto.advertised_cost(node)
        payload = {"seq": seq, "hops": node.hops, "energy": max(node.energy, 0.0) / node.e0,
                   "cost": cost, "receipts": {}, "origin": node.id}
        self.send_ctrl(node, "beacon", payload, 16, front=True)

    # ---------------------------------------------------------------- alarms
    def _inject_alarm(self):
        srcs = [n for n in self.nodes[:-1] if n.alive and n.crit >= 1.0]
        if srcs:
            src = srcs[int(self.rng_alarm.integers(len(srcs)))]
            aid = self.new_pid()
            self.stats["alarms"] += 1
            self.stats.setdefault("_alarm_open", {})[aid] = [self.cfg.alarm_burst, None]
            for k in range(self.cfg.alarm_burst):
                self.push(self.t + 0.05 * k, EV_ALARM, src.id, ("pkt", aid))
        self.push(self.t + self.rng_alarm.exponential(1.0 / self.cfg.alarm_rate), EV_ALARM, -1, ("new",))

    def _alarm_outcome(self, pkt, delivered):
        rec = self.stats.get("_alarm_open", {}).get(pkt.ctype)
        if rec is None:
            return
        rec[0] -= 1
        if delivered and rec[1] is None:
            rec[1] = self.t - pkt.t_gen
            self.stats["alarm_lat"].append(rec[1])
        if rec[0] == 0 and rec[1] is None:
            self.stats["alarms_missed"] += 1

    # ------------------------------------------------------------------ run
    def run(self):
        cfg = self.cfg
        for n in self.nodes[:-1]:
            if n.rate > 0:
                self._schedule_gen(n)
        self.push(0.0, EV_BEACON)
        self.push(cfg.window, EV_WINDOW)
        if cfg.alarm_rate > 0:
            self.push(cfg.warmup + self.rng_alarm.exponential(1.0 / cfg.alarm_rate), EV_ALARM, -1, ("new",))
        self.proto.start()
        heap = self.heap
        while heap:
            t, _, code, nid, payload = heapq.heappop(heap)
            if t > cfg.duration:
                break
            self.t = t
            if code == EV_ATTEMPT:
                self._attempt(self.nodes[nid], payload)
            elif code == EV_TXEND:
                self._txend(self.nodes[nid], payload)
            elif code == EV_GEN:
                n = self.nodes[nid]
                if n.alive:
                    self.generate(n)
                    self._schedule_gen(n)
            elif code == EV_WINDOW:
                self.w += 1
                self.proto.on_window(self.w)
                if cfg.energy_sample_s > 0 and (self.w % int(round(cfg.energy_sample_s / cfg.window))) == 0:
                    sens = self.nodes[:-1]
                    self.stats.setdefault("energy_trace", []).append(
                        (t, sum(max(n.energy, 0.0) for n in sens) / (len(sens) * cfg.e0),
                         sum(1 for n in sens if n.alive)))
                if cfg.trace_node >= 0:
                    self.trace.append((t, self.proto.trace_state(self.nodes[cfg.trace_node])))
                self.push(t + cfg.window, EV_WINDOW)
            elif code == EV_BEACON:
                self._send_beacon()
            elif code == EV_REBCAST:
                self._rebroadcast(self.nodes[nid], payload)
            elif code == EV_TIMER:
                self.proto.on_timer(payload, self.nodes[nid] if nid >= 0 else None)
            elif code == EV_ALARM:
                if payload[0] == "new":
                    self._inject_alarm()
                else:
                    src = self.nodes[nid]
                    if src.alive:
                        pkt = Packet(self.new_pid(), src.id, self.t, cls="alarm", ctype=payload[1])
                        src.sent_seq += 1; pkt.payload = src.sent_seq
                        if self.t >= cfg.warmup:
                            self.stats["generated"] += 1
                            self.stats["gen_cls"]["alarm"] = self.stats["gen_cls"].get("alarm", 0) + 1
                        self.enqueue(src, pkt, front=True)
        self.t = cfg.duration
        return self.summary()

    # ------------------------------------------------------------- summary
    def summary(self):
        cfg = self.cfg
        s = self.stats
        meas = cfg.duration - cfg.warmup
        lat = np.array(s["lat"]) if s["lat"] else np.array([np.nan])
        sensors = self.nodes[:-1]
        consumed = np.array([n.e0 - max(n.energy, 0.0) for n in sensors])
        dead = [n.dead_at for n in sensors if n.dead_at is not None]
        out = {
            "protocol": cfg.protocol, "seed": cfg.seed, "velocity": cfg.velocity, "load": cfg.load,
            "generated": s["generated"], "delivered": s["delivered"],
            "pdr": s["delivered"] / max(1, s["generated"]),
            "lat_mean_ms": float(np.nanmean(lat) * 1e3), "lat_p95_ms": float(np.nanpercentile(lat, 95) * 1e3),
            "lat_median_ms": float(np.nanmedian(lat) * 1e3),
            "throughput_kbps": s["delivered_payload_bits"] / meas / 1e3,
            "energy_mean_mJ": float(consumed.mean() * 1e3), "energy_max_mJ": float(consumed.max() * 1e3),
            "energy_std_mJ": float(consumed.std() * 1e3),
            "residual_mean_pct": float(100.0 * (1.0 - consumed / cfg.e0).mean()),
            "fnd_s": float(min(dead)) if dead else float("nan"),
            "dead_count": len(dead),
            "ctrl_frames_per_s": s["ctrl_frames"] / cfg.duration,
            "ctrl_bytes_per_delivered": s["ctrl_bytes"] / max(1, s["delivered"]),
            "retx_ratio": s["data_retx"] / max(1, s["data_tx"]),
            "collisions": s["collisions"],
            "mean_hops": s["hops_sum"] / max(1, s["delivered"]),
            "alarms": s["alarms"], "alarms_missed": s["alarms_missed"],
            "alarm_lat_median_ms": float(np.median(s["alarm_lat"]) * 1e3) if s["alarm_lat"] else float("nan"),
            "alarm_lat_p95_ms": float(np.percentile(s["alarm_lat"], 95) * 1e3) if s["alarm_lat"] else float("nan"),
        }
        for c in ("data", "crit", "alarm"):
            g = s["gen_cls"].get(c, 0); d = s["del_cls"].get(c, 0)
            out[f"pdr_{c}"] = d / g if g else float("nan")
            out[f"lat_{c}_ms"] = float(np.mean(s["lat_cls"][c]) * 1e3) if c in s["lat_cls"] else float("nan")
        for k, v in s["dropped"].items():
            out[f"drop_{k}"] = v
        if "energy_trace" in s:
            out["_energy_trace"] = s["energy_trace"]
        out["_dead_times"] = sorted(dead)
        out["blackholed"] = s.get("blackholed", 0)
        return out
