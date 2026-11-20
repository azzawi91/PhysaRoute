import sys, json
from multiprocessing import Pool
import numpy as np
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physaroute import run_one
S={"bh3":dict(malicious=[8,10,11]),"load200":dict(load=200.0),"ble.25":dict(ble_airtime=0.25),"ble.5":dict(ble_airtime=0.5),"jam8":dict(jam_node=8),"life":dict(duration=1500.0)}
P=json.loads(sys.argv[1])   # label -> [protocol, proto_kw]
def job(a):
    lab,sc,s=a
    kw=dict(protocol=P[lab][0], proto_kw=P[lab][1], seed=20260425+s, velocity=1.0, load=80.0, duration=200.0, warmup=20.0); kw.update(S[sc])
    r=run_one(**kw); return lab,sc,r['pdr'],r['lat_p95_ms'],r['energy_mean_mJ'],r['energy_max_mJ'],r['fnd_s'] if r['fnd_s']==r['fnd_s'] else 1500
if __name__=="__main__":
    n=int(sys.argv[2]); scs=sys.argv[3].split(',') if len(sys.argv)>3 else list(S)
    with Pool(2) as p: res=p.map(job,[(q,sc,s) for q in P for sc in scs for s in range(n)])
    for sc in scs:
        for q in P:
            a=np.array([r[2:] for r in res if r[0]==q and r[1]==sc]); print(f"{sc:8s} {q:14s} pdr={100*a[:,0].mean():.2f}±{100*1.96*a[:,0].std(ddof=1)/np.sqrt(len(a)):.2f} p95={a[:,1].mean():.0f} E={a[:,2].mean():.1f} Emax={a[:,3].mean():.0f} fnd={a[:,4].mean():.0f}")
