import sys, json
from multiprocessing import Pool
import numpy as np
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physaroute import run_one
def job(a):
    p,v,s,extra=a
    r=run_one(protocol=p, seed=20260425+s, velocity=v, load=80.0, duration=200.0, warmup=20.0, **extra)
    return p,v,r['pdr'],r['lat_median_ms'],r['lat_p95_ms'],r['energy_mean_mJ'],r['energy_max_mJ']
if __name__=="__main__":
    protos=sys.argv[1].split(','); vs=[float(x) for x in sys.argv[2].split(',')]; n=int(sys.argv[3])
    extra=json.loads(sys.argv[4]) if len(sys.argv)>4 else {}
    jobs=[(p,v,s,extra) for p in protos for v in vs for s in range(n)]
    with Pool(2) as pool: res=pool.map(job,jobs)
    for v in vs:
        for p in protos:
            a=np.array([r[2:] for r in res if r[0]==p and r[1]==v])
            print(f"v={v} {p:15s} pdr={100*a[:,0].mean():.2f}±{100*1.96*a[:,0].std(ddof=1)/np.sqrt(len(a)):.2f} med={a[:,1].mean():.2f} p95={a[:,2].mean():.1f} E={a[:,3].mean():.1f} Emax={a[:,4].mean():.0f}")
