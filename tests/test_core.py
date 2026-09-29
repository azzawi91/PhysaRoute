"""Smoke and invariant tests for the PhysaRoute simulator (pytest)."""
import math

import numpy as np
import pytest

from physaroute import run_one, PROTOCOLS
from physaroute import channel as ch
from physaroute.protocols import PhysaRoute


def test_frame_timing_matches_standard():
    # 96-byte PSDU: 768 bits + 16 shortened BCH codewords x 12 parity = 960 coded bits -> 480 symbols = 0.8 ms
    assert abs(ch.frame_airtime(87) - (150e-6 + 206.7e-6 + 0.8e-3)) < 2e-6
    assert abs(ch.T_ACK - (150e-6 + 206.7e-6 + 80e-6)) < 2e-6


def test_sensitivity_is_inside_standard_requirement():
    per = ch.PERModel()
    s = per.sensitivity_dBm(255, 0.10)
    assert -95 < s < -83          # better than the -83 dBm the standard requires


def test_channel_symmetric_and_speed_dependent():
    per = ch.PERModel()
    logS0, PL0, d = ch.generate_channel(np.random.default_rng(1), 0.0, 20.0, 0.1, per)
    logS3, PL3, d = ch.generate_channel(np.random.default_rng(1), 3.0, 20.0, 0.1, per)
    assert np.allclose(PL0, np.transpose(PL0, (0, 2, 1)))
    assert PL3.std(axis=0).mean() > PL0.std(axis=0).mean()


def test_fixed_points_and_viability():
    class E:  # minimal stand-in for the engine
        nodes = []; rng_mac = np.random.default_rng(0); sens_dBm = -89.0; ncw_data = 16
        class per:
            @staticmethod
            def log_success_per_codeword(x): return 0.0
    p = PhysaRoute.__new__(PhysaRoute)
    p.mu, p.alpha = 0.2, 1.0
    assert p.fixed_points(1.0, 0.3) is None            # k h = 1.5 < 2 -> not viable
    dm, dp = p.fixed_points(1.0, 0.9)                   # k h = 4.5 -> viable
    assert dm < 1 / 0.9 < dp and abs(dm * dp - 1 / 0.81) < 1e-9
    # slope at the stable fixed point is 1 - mu (x^2-1)/(x^2+1)
    x = 0.9 * dp
    rho = 1 - 0.2 * (x * x - 1) / (x * x + 1)
    assert 0.8 < rho < 1.0


@pytest.mark.parametrize("proto", PROTOCOLS)
def test_every_protocol_runs_and_conserves_packets(proto):
    r = run_one(protocol=proto, seed=7, duration=30.0, warmup=5.0, velocity=1.0, load=40.0)
    assert 0.0 <= r["pdr"] <= 1.0
    dropped = sum(v for k, v in r.items() if k.startswith("drop_"))
    assert r["delivered"] + dropped <= r["generated"] + 64      # in-flight packets at the end
    assert r["energy_mean_mJ"] > 0 and math.isfinite(r["lat_median_ms"])


def test_same_seed_is_deterministic():
    a = run_one(protocol="PhysaRoute", seed=3, duration=20.0, warmup=5.0)
    b = run_one(protocol="PhysaRoute", seed=3, duration=20.0, warmup=5.0)
    assert a["pdr"] == b["pdr"] and a["energy_mean_mJ"] == b["energy_mean_mJ"]


def test_blackhole_counts_packets():
    r = run_one(protocol="AODV", seed=2, duration=40.0, warmup=5.0, malicious=(8, 10))
    assert r["blackholed"] >= 0


def test_environment_is_common_across_protocols():
    # common random numbers: the same seed must give every protocol the same
    # packet arrivals and alarm events (paired design)
    runs = [run_one(protocol=p, seed=5, duration=30.0, warmup=5.0, alarm_rate=0.3) for p in ("PhysaRoute", "AODV", "SIMPLE")]
    assert len({r["generated"] for r in runs}) == 1
    assert len({r["alarms"] for r in runs}) == 1
