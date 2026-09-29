"""
Body-area channel, PHY and radio-energy models for the PhysaRoute simulator.

Everything here is *parametric* and every constant is traceable to a public
source (see docs/SIMULATOR.md and the manuscript, Section 7):

* Path loss: IEEE 802.15.6 channel model CM3 (body-surface to body-surface,
  2.4 GHz, hospital room) from Yazdandoost & Sayrafian-Pour, IEEE
  P802.15-08-0780-12-0006 (2010):  PL(d)[dB] = a*log10(d[mm]) + b + N,
  a = 6.6, b = 36.1, sigma_N = 3.8 dB.
* Temporal dynamics: an AR(1) log-normal process whose standard deviation and
  coherence time depend on walking speed (coherence time ~10-70 ms while
  walking/running, ~seconds while quasi-static: Zhang et al. AWPL 2009, Smith
  et al. Electron. Lett. 2009 / Ann. Telecommun. 2011), plus posture-driven
  deep-fade events of 10-35 dB (body shadowing; Dong & Smith 2013, Smith et
  al. 2013 survey).
* PHY: IEEE 802.15.6 narrowband 2.4 GHz, 971.4 kb/s pi/4-DQPSK with
  BCH(63,51); differential-detection BER from Proakis; receiver noise figure
  and implementation loss set so that the 10 % PER sensitivity for a 255-byte
  PSDU is close to the -83 dBm required by the standard (Table 52) plus a
  6 dB margin typical of commercial radios.
* Energy: radio-only run currents of the Nordic nRF52840 product
  specification (TX 0 dBm 4.8 mA, RX 4.6 mA, DC/DC, 3 V).
"""
from __future__ import annotations

import math
import numpy as np
from scipy import special as _sp
from scipy.stats import ncx2 as _ncx2

# ---------------------------------------------------------------------------
# PHY timing (IEEE 802.15.6-2012, 2.4 GHz narrowband PHY)
# ---------------------------------------------------------------------------
SYMBOL_RATE = 600_000.0            # symbols/s
T_PREAMBLE = 90 / SYMBOL_RATE      # 90 symbols = 150 us
T_PLCP_HDR = 31 * 4 / SYMBOL_RATE  # 31 coded bits, pi/2-DBPSK, spreading 4 -> 206.7 us
P_SIFS = 75e-6                     # pSIFS
SLOT = 145e-6                      # pCSMASlotLength = pCCATime + pCSMAMACPHYTime
MAC_HDR_BYTES = 7
FCS_BYTES = 2
BCH_N, BCH_K, BCH_T = 63, 51, 2
BITS_PER_SYMBOL = 2                # pi/4-DQPSK


def psdu_codewords(body_bytes: int) -> int:
    """Number of BCH(63,51) codewords for a frame with `body_bytes` of MAC body."""
    n_bits = (MAC_HDR_BYTES + body_bytes + FCS_BYTES) * 8
    return int(math.ceil(n_bits / BCH_K))


def frame_airtime(body_bytes: int) -> float:
    """On-air duration (s) of a frame with the given MAC body length
    (IEEE 802.15.6-2012 eq. 67/77: shortened BCH codewords, 12 parity bits each)."""
    n_bits = (MAC_HDR_BYTES + body_bytes + FCS_BYTES) * 8
    n_cw = psdu_codewords(body_bytes)
    coded_bits = n_bits + n_cw * (BCH_N - BCH_K)
    return T_PREAMBLE + T_PLCP_HDR + coded_bits / BITS_PER_SYMBOL / SYMBOL_RATE


T_ACK = frame_airtime(0)           # I-Ack: header + FCS only (9 octets)


# ---------------------------------------------------------------------------
# BER / PER model
# ---------------------------------------------------------------------------
def ber_dqpsk(gamma_b: np.ndarray) -> np.ndarray:
    """BER of pi/4-DQPSK with differential detection (Proakis, eq. 5-2-71)."""
    g = np.asarray(gamma_b, dtype=float)
    a = np.sqrt(2.0 * g * (1.0 - 1.0 / math.sqrt(2.0)))
    b = np.sqrt(2.0 * g * (1.0 + 1.0 / math.sqrt(2.0)))
    q1 = _ncx2.sf(b ** 2, 2, a ** 2)               # Marcum Q_1(a,b)
    return np.clip(q1 - 0.5 * _sp.i0e(a * b) * np.exp(a * b - (a ** 2 + b ** 2) / 2.0), 0.0, 0.5)


def codeword_error_prob(ber: np.ndarray) -> np.ndarray:
    """Probability that a BCH(63,51) codeword (t=2) is not decodable."""
    p = np.asarray(ber, dtype=float)
    ok = 0.0
    for k in range(BCH_T + 1):
        ok = ok + _sp.comb(BCH_N, k) * p ** k * (1.0 - p) ** (BCH_N - k)
    return np.clip(1.0 - ok, 1e-15, 1.0)


class PERModel:
    """Maps received power (dBm) to log(1 - P_cw); frame success = exp(N_cw * that)."""

    def __init__(self, data_rate=971_400.0, noise_figure_dB=13.0, impl_loss_dB=3.0):
        self.data_rate = data_rate
        # Eb/N0 [dB] = Prx - (-174 + NF + IL + 10 log10 Rb)
        self.noise_ref_dBm = -174.0 + noise_figure_dB + impl_loss_dB + 10.0 * math.log10(data_rate)
        self._prx_grid = np.linspace(-130.0, -40.0, 1801)
        ebn0 = 10.0 ** ((self._prx_grid - self.noise_ref_dBm) / 10.0)
        pcw = codeword_error_prob(ber_dqpsk(ebn0))
        self._log1m_pcw = np.log1p(-pcw)

    def log_success_per_codeword(self, prx_dBm):
        return np.interp(prx_dBm, self._prx_grid, self._log1m_pcw, left=self._log1m_pcw[0], right=0.0)

    def sensitivity_dBm(self, body_bytes=255, per=0.10) -> float:
        n_cw = psdu_codewords(body_bytes)
        p_ok = np.exp(n_cw * self._log1m_pcw)
        idx = np.searchsorted(p_ok, 1.0 - per)
        return float(self._prx_grid[min(idx, len(self._prx_grid) - 1)])


# ---------------------------------------------------------------------------
# Radio energy (nRF52840 PS v1.7, radio-only, DC/DC, 3 V)
# ---------------------------------------------------------------------------
V_SUPPLY = 3.0
I_TX_mA = {0.0: 4.8, -4.0: 3.1, -8.0: 3.3, -10.0: 3.15, -12.0: 3.0, -20.0: 2.7}
I_RX_mA = 4.6


def p_tx_W(ptx_dBm: float) -> float:
    return I_TX_mA.get(ptx_dBm, 4.8) * 1e-3 * V_SUPPLY


P_RX_W = I_RX_mA * 1e-3 * V_SUPPLY


# ---------------------------------------------------------------------------
# Body model: 12 sensors + belt-worn gateway (metres, torso-centred frame)
# ---------------------------------------------------------------------------
# name, criticality c_i, traffic weight w_i, limb-exposure e_i, position (x, y, z)
SENSORS = [
    ("ECG",        1.00, 6.0, 0.15, (0.00, 0.09, 1.30)),   # chest, front
    ("SpO2",       1.00, 2.0, 0.55, (0.32, 0.12, 0.92)),   # wrist (arm hanging)
    ("BP",         0.85, 1.0, 0.45, (0.21, 0.04, 1.30)),   # upper arm
    ("Capno",      0.85, 2.0, 0.20, (0.00, 0.11, 1.62)),   # nasal cannula sensor, face
    ("EEG",        0.60, 4.0, 0.20, (0.00, 0.06, 1.70)),   # forehead
    ("Resp",       0.60, 2.0, 0.15, (-0.10, 0.08, 1.24)),  # left chest band
    ("Glucose",    0.40, 0.5, 0.25, (-0.13, 0.05, 1.05)),  # left flank
    ("Temp",       0.20, 0.5, 0.30, (0.15, 0.00, 1.38)),   # axilla
    ("Accel-hip",  0.20, 1.0, 0.25, (0.12, 0.06, 0.95)),   # right hip
    ("Accel-ankle",0.20, 1.0, 0.60, (0.08, 0.04, 0.12)),   # right ankle
    ("Motion",     0.20, 1.0, 0.35, (0.16, -0.02, 1.45)),  # shoulder
    ("Posture",    0.20, 0.5, 0.20, (0.00, -0.12, 1.15)),  # mid back
]
GATEWAY_POS = (0.00, 0.10, 0.95)   # belt, front
N_SENSORS = len(SENSORS)
GATEWAY = N_SENSORS                 # node index of the gateway
N_NODES = N_SENSORS + 1


def body_geometry(rng: np.random.Generator, jitter_m: float = 0.02):
    """Pairwise on-body distances (mm) with per-run placement jitter, and a
    boolean matrix marking links whose straight line crosses the torso or the
    head (non-line-of-sight, 'around-the-body' propagation)."""
    pos = np.array([s[4] for s in SENSORS] + [GATEWAY_POS], dtype=float)
    pos = pos + rng.normal(0.0, jitter_m, pos.shape)
    d = np.sqrt(((pos[:, None, :] - pos[None, :, :]) ** 2).sum(-1))
    # on-body propagation follows the body surface: inflate straight-line
    # distance by a mild curvature factor (creeping-wave path, Fort et al. 2006)
    d = d * 1.15
    np.fill_diagonal(d, 0.05)
    n = len(pos)
    nlos = np.zeros((n, n), dtype=bool)
    ts = np.linspace(0.1, 0.9, 9)
    for i in range(n):
        for j in range(i + 1, n):
            seg = pos[i][None, :] + ts[:, None] * (pos[j] - pos[i])[None, :]
            x, y, z = seg[:, 0], seg[:, 1], seg[:, 2]
            torso = ((x / 0.15) ** 2 + (y / 0.085) ** 2 < 1.0) & (z > 0.85) & (z < 1.52)
            head = ((x ** 2 + (y - 0.0) ** 2 + (z - 1.62) ** 2) < 0.085 ** 2)
            nlos[i, j] = nlos[j, i] = bool(torso.any() or head.any())
    return d * 1000.0, nlos


def body_distances_mm(rng: np.random.Generator, jitter_m: float = 0.02) -> np.ndarray:
    return body_geometry(rng, jitter_m)[0]


# ---------------------------------------------------------------------------
# Dynamic channel generator
# ---------------------------------------------------------------------------
class ChannelParams:
    # CM3 2.4 GHz hospital room
    a = 6.6
    b = 36.1
    sigma_N = 3.8
    # dynamic shadowing vs speed v (m/s)
    sigma_dyn_static = 1.0          # dB, quasi-static (lying / sitting)
    sigma_dyn_slope = 1.7           # dB per (m/s): 6.1 dB at 3 m/s
    coh_static = 2.0                # s, coherence time when quasi-static
    coh_decay = 1.23                # T_c(v) = coh_static * exp(-coh_decay * v): 50 ms at 3 m/s
    # posture-transition deep fades
    fade_rate_static = 0.05         # events/s at v = 0
    fade_rate_slope = 0.30          # events/s per (m/s)
    fade_depth_lo = 10.0            # dB
    fade_depth_hi = 35.0            # dB
    fade_dur_mean = 0.6             # s
    nlos_extra_dB = 12.0            # static body-shadowing penalty for around-the-body links
    tx_power_dBm = -10.0


def generate_channel(rng: np.random.Generator, velocity: float, duration: float,
                     window: float, per_model: PERModel, params: ChannelParams = ChannelParams(),
                     trace: np.ndarray | None = None):
    """
    Returns (logS, PL) where logS[w, i, j] = log(1 - P_cw) for window w on link
    (i, j) at the configured TX power, and PL[w, i, j] is the path loss in dB.
    If `trace` (windows x N x N path-loss array, e.g. replayed from a public
    measurement set) is given it replaces the parametric dynamics.
    """
    n_w = int(math.ceil(duration / window)) + 2
    n = N_NODES
    d_mm, nlos = body_geometry(rng)
    if trace is not None:
        PL = np.asarray(trace, dtype=float)[:n_w]
    else:
        static = params.a * np.log10(d_mm) + params.b + params.nlos_extra_dB * nlos
        N = rng.normal(0.0, params.sigma_N, (n, n))
        N = np.triu(N, 1); N = N + N.T
        static = static + N
        # AR(1) dynamic component (symmetric)
        v = float(velocity)
        sigma = params.sigma_dyn_static + params.sigma_dyn_slope * v
        tc = params.coh_static * math.exp(-params.coh_decay * v)
        rho = math.exp(-window / tc)
        X = np.zeros((n_w, n, n))
        e = rng.normal(0.0, 1.0, (n_w, n, n))
        e = np.triu(e, 1); e = e + np.transpose(e, (0, 2, 1))
        X[0] = e[0]
        s = math.sqrt(1.0 - rho * rho)
        for w in range(1, n_w):
            X[w] = rho * X[w - 1] + s * e[w]
        dyn = sigma * X
        # posture-driven deep fades
        exposure = np.array([s_[3] for s_ in SENSORS] + [0.10])
        link_exp = 1.0 - (1.0 - exposure[:, None]) * (1.0 - exposure[None, :])
        rate = params.fade_rate_static + params.fade_rate_slope * v
        fades = np.zeros((n_w, n, n))
        t = 0.0
        while True:
            t += rng.exponential(1.0 / rate)
            if t >= duration:
                break
            hit = rng.random((n, n)) < link_exp
            hit = np.triu(hit, 1); hit = hit | hit.T
            if not hit.any():
                continue
            depth = rng.uniform(params.fade_depth_lo, params.fade_depth_hi)
            dur = rng.exponential(params.fade_dur_mean)
            w0 = int(t / window); w1 = min(n_w, int((t + dur) / window) + 1)
            fades[w0:w1][:, hit] += depth
        PL = static[None, :, :] + dyn + fades
    prx = params.tx_power_dBm - PL
    logS = per_model.log_success_per_codeword(prx)
    return logS.astype(np.float64), PL.astype(np.float32), d_mm
