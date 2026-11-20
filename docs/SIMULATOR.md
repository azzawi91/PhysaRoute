# Simulator design notes

This document explains what the discrete-event simulator models, what it does not, and where every
constant comes from. All constants are also in `params/*.yaml`.

## 1. Bodies, sensors and traffic

* 12 sensors + 1 belt gateway at fixed torso-centred positions (`channel.SENSORS`), jittered by 2 cm per run.
  Straight-line distances are inflated by 15 % to approximate creeping-wave paths around the body.
* Each sensor has a clinical criticality `c_i` (ECG, SpO2 = 1.0; BP, capnography = 0.85; EEG, respiration = 0.6;
  glucose = 0.4; temperature, motion, posture = 0.2), a share of the aggregate load and a *limb exposure*
  that sets how likely a posture transition is to fade its links.
* Traffic: independent Poisson processes per sensor; 87-byte payloads (96-byte PSDU). Frames from sensors with
  `c_i >= 0.85` are class *crit*; the ICU scenario adds *alarm* bursts (3 frames, 50 ms apart).

## 2. Channel

Received power on link (i, j) in 100-ms window w:

```
P_ij(w) = P_tx - [a log10(d_mm) + b + N_ij] - Δ_NLOS,ij - S_ij(w) - Δ_fade,ij(w)
```

* `a = 6.6, b = 36.1, σ_N = 3.8 dB`: IEEE 802.15.6 CM3, 2.4 GHz, hospital room
  (Yazdandoost & Sayrafian-Pour, IEEE P802.15-08-0780-12-0006, 2010). `N_ij` is drawn once per run and link
  (symmetric): the spatial variability of the CM3 model.
* `Δ_NLOS = 12 dB` for links whose straight line crosses an elliptical torso (0.30 × 0.17 m cross-section,
  0.85 < z < 1.52 m) or a head sphere (r = 8.5 cm). Around-the-body losses of 55–75 dB were measured by
  CSIRO/NICTA and are reproduced in the CM3 document; a static offset is the simplest model of that.
* `S_ij(w)`: AR(1) Gaussian process (symmetric per link) with standard deviation `1.0 + 1.7 v` dB and coherence
  time `2.0 exp(-1.23 v)` s (2 s quasi-static → 50 ms at 3 m/s), consistent with coherence times of 10–70 ms
  reported for walking/running (Zhang et al., AWPL 2009; Smith et al., Electron. Lett. 2009) and standard
  deviations up to ~7 dB during walking (Mohamed et al., EURASIP JWCN 2019).
* Posture transitions: Poisson with rate `0.05 + 0.3 v` s⁻¹; each hits every link independently with probability
  `1 - (1 - e_i)(1 - e_j)` (limb exposures) and adds a fade of U(10, 35) dB for an Exp(mean 0.6 s) duration
  (body-shadowing events of 20–40 dB: Smith et al., IEEE AP Mag 2013).
* `P_tx = -10 dBm`.
* A `channel_trace` (windows × nodes × nodes path-loss array in dB) can replace the parametric dynamics.

## 3. PHY and PER

IEEE 802.15.6-2012 narrowband PHY, 2.4 GHz, 971.4 kb/s: π/4-DQPSK, BCH(63,51), 600 ksymbol/s, preamble 150 µs,
PLCP header 206.7 µs, payload `(N_PSDU + 12 N_cw) / 2 / 600e3` s (shortened codewords). A 96-byte PSDU lasts
1.1567 ms; an I-Ack (9 octets) 0.4367 ms. BER is the differential-detection DQPSK expression (Proakis), codeword
error the t = 2 bound, PER = 1 - (1 - P_cw)^N_cw. With NF = 13 dB and 3 dB implementation loss the 10 %-PER
sensitivity of a 255-byte PSDU is -89 dBm (standard requires -83 dBm).

## 4. MAC

CSMA/CA over a single collision domain:

* contention windows per class (Table 20 of the standard): data [8, 32] (UP2/3), critical [4, 8] (UP5),
  alarm [1, 4] (UP7), control [4, 8]; CW doubles after every failed attempt up to CWmax;
* pSIFS = 75 µs, slot = 145 µs (pCSMASlotLength at 2.4 GHz), CCA = 105 µs: two transmissions that start within
  the CCA window of one another collide;
* immediate ACK after pSIFS; ACK loss triggers a retransmission and the receiver drops the duplicate;
* 3 retransmissions per hop (4 attempts), then the routing protocol may re-route (up to 3 times per hop),
  24 attempts per packet, 2-s packet lifetime, 32-frame queues;
* control frames may bypass data frames that are held waiting for a route (AODV discovery, PhysaRoute hold).

## 5. Energy

Airtime × radio current × 3 V with nRF52840 PS v1.7 currents (3.15 mA at -10 dBm TX, 4.6 mA RX, DC/DC):
10.9 µJ per data frame sent, 16.0 µJ received, 6.0 µJ per ACK sent or received; broadcasts are received (and
charged) by every alive node; unicasts only by the addressee. Idle listening and sensing are excluded (identical
across protocols). Each sensor has a 0.5 J routing-radio budget; a node with no energy is dead.

## 6. Common control substrate

Every 2 s the gateway broadcasts a beacon (16 bytes + 8 bytes per source of receipts when the protocol uses
them); each sensor that hears a new beacon re-broadcasts it once after 2–30 ms with its hop count, residual
energy fraction and protocol cost field. All protocols obtain neighbour RSSI, hop counts and residual energies
from this substrate; nothing else is exchanged unless the protocol sends it.

## 7. Attacks and interference

* BLE coexistence: each frame is hit by a co-channel burst with the given airtime fraction and then lost with
  probability 0.9.
* Jamming: every frame to or from the jammed node is lost with probability 0.9.
* Black-hole relays: acknowledge every frame, forward nothing, and lie in control fields (hop count 1,
  potential 0, best Q = 0, RREP with hop count 0).

## 8. Common random numbers

Run r of every cell uses environment seed `20260425 + r`. Everything a protocol cannot influence is drawn from
streams seeded by that seed alone — placement, channel realisation and fades (`rng_env`), packet arrivals (one
stream per source, `rng_traffic`) and alarm events (`rng_alarm`) — so every protocol sees the identical environment
and comparisons are paired (`tests/test_core.py::test_environment_is_common_across_protocols`). Randomness whose
consumption depends on the protocol (backoff, frame-error and interference draws, re-broadcast jitter, next-hop
sampling) uses `rng_mac`, seeded with a CRC of the protocol name, so every run is bit-reproducible across processes.

## 9. Statistics

`physaroute/stats.py` reports, for PhysaRoute versus every baseline and metric: mean paired difference,
bootstrap 95 % CI (5000 resamples), paired t, Cohen's d_z, Wilcoxon signed-rank p, and Holm–Bonferroni adjusted
p over the whole family of tests.

## 10. What is not modelled

Hidden terminals, antenna detuning, inter-subject variation, MAC scheduled access (only CSMA/CA), packet
aggregation, security handshakes, and the sensing electronics' energy.
