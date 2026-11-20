import sys, json
from multiprocessing import Pool
import numpy as np
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physaroute import run_one
V={
 "base":{}, "fb":dict(fb_metric=True), "fb+pot":dict(fb_metric=True,pot_all=True),
 "fb+pot+bcn":dict(fb_metric=True,pot_all=True,beacon_reseed=True),
 "all+greedy.1":dict(fb_metric=True,pot_all=True,beacon_reseed=True,greedy_eps=0.1),
 "all+k4":dict(fb_metric=True,pot_all=True,beacon_reseed=True,kappa=4.0,kappa_crit=6.0),
}
V.update(json.loads(sys.argv[4]) if len(sys.argv)>4 else {})
def job(a):
    k,v,s,extra=a
    kw=dict(protocol="PhysaRoute", seed=20260425+s, velocity=v, load=80.0, duration=200.0, warmup=20.0, proto_kw=V[k]); kw.update(extra)
    r=run_one(**kw)
    return k,v,r['pdr'],r['lat_median_ms'],r['lat_p95_ms'],r['energy_mean_mJ'],r['energy_max_mJ']
if __name__=="__main__":
    ks=sys.argv[1].split(',') if sys.argv[1]!="all" else list(V); vs=[float(x) for x in sys.argv[2].split(',')]; n=int(sys.argv[3])
    extra=json.loads(sys.argv[5]) if len(sys.argv)>5 else {}
    with Pool(2) as pool: res=pool.map(job,[(k,v,s,extra) for k in ks for v in vs for s in range(n)])
    for v in vs:
        for k in ks:
            a=np.array([r[2:] for r in res if r[0]==k and r[1]==v])
            print(f"v={v} {k:15s} pdr={100*a[:,0].mean():.2f}±{100*1.96*a[:,0].std(ddof=1)/np.sqrt(len(a)):.2f} med={a[:,1].mean():.2f} p95={a[:,2].mean():.1f} E={a[:,3].mean():.1f} Emax={a[:,4].mean():.0f}")
