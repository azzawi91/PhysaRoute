"""PhysaRoute: discrete-event simulator for adaptive routing in healthcare WBANs."""
from .engine import Engine, RunConfig
from .protocols import make_protocol, PROTOCOLS, ABLATIONS


def run_one(**cfg_kw):
    """Run a single simulation and return its summary dict."""
    cfg = RunConfig(**cfg_kw)
    eng = Engine(cfg, lambda e: make_protocol(cfg.protocol, e, **cfg.proto_kw))
    out = eng.run()
    if cfg.trace_node >= 0:
        out["_trace"] = eng.trace
    return out
