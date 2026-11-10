import sys, time; sys.path.insert(0,'.')
import numpy as np
_t=time.time()
def T(m): print(m, round(time.time()-_t,1), flush=True)
from possession import data
d=data.load_atd(); g=data.graded_mask(); P=data.PITCH; T("loaded")
ball=d['ball']; pl=d['players']; team=d['team']; vis=np.isfinite(ball[:,0])
with np.errstate(all='ignore'): ms=np.nanmean(d['pspeed'],axis=1)
def mm(x,k):
    ok=np.isfinite(x); v=np.where(ok,x,0)
    c=np.concatenate(([0],np.cumsum(v))); n=np.concatenate(([0],np.cumsum(ok)))
    i=np.arange(len(x)); lo=np.maximum(0,i-k//2); hi=np.minimum(len(x),i+k//2+1)
    with np.errstate(all='ignore'): return (c[hi]-c[lo])/(n[hi]-n[lo])
sm=mm(ms,25); x=sm[g]; x=x[np.isfinite(x)]
print('speed pct 1,5,10,25,50,75,90,95,99',np.percentile(x,[1,5,10,25,50,75,90,95,99]).round(2))
h,e=np.histogram(x,bins=30); print(np.c_[e[:-1].round(2),h].tolist()); T("speed")
dm=np.full((len(ball),2),np.nan)
for t in (0,1):
    dd=np.sqrt(((pl[:,team==t,:]-ball[:,None,:])**2).sum(-1))
    dd[~np.isfinite(dd)]=np.inf; mn=dd.min(1); mn[~np.isfinite(mn)]=np.nan; dm[:,t]=mn
T("dist")
m=g&vis; dmin=np.fmin(dm[:,0],dm[:,1])
print('dmin pct 10,25,50,75,90',np.nanpercentile(dmin[m],[10,25,50,75,90]).round(2))
h,e=np.histogram(dmin[m][np.isfinite(dmin[m])],bins=np.arange(0,16,1)); print(np.c_[e[:-1],h].tolist())
bx,by=ball[:,0],ball[:,1]
outd=np.maximum.reduce([-bx,bx-P[0],-by,by-P[1],np.zeros(len(bx))])
o=outd[m]; print('out >0,.5,1,2',[(o>v).mean().round(4) for v in (0,.5,1,2)])
bs=np.full(len(ball),np.nan); w=5
bs[w:-w]=np.hypot(ball[2*w:,0]-ball[:-2*w,0],ball[2*w:,1]-ball[:-2*w,1])/(2*w/25)
print('bspeed pct',np.nanpercentile(bs[m],[10,25,50,75,90,99]).round(2),'file',np.nanpercentile(d['bspeed_file'][m],[10,25,50,75,90,99]).round(2))
print('pspeed p99,99.5,99.9',np.nanpercentile(d['pspeed'][g],[99,99.5,99.9]).round(2)); T("ball")
sp=data.load_set_pieces(); offs=np.arange(-30,41,5)*25
for ty in ['throw-in','goal kick','corner kick','free kick']:
    ev=[s['start_frame'] for s in sp if s['type']==ty]
    r=[];ro=[]
    for off in offs:
        idx=[f+off for f in ev if g[f+off]]
        r.append(np.nanmean(sm[idx])); ro.append(np.nanmean(outd[idx]>0.5))
    print(ty,len(ev),'offs(s)',(offs//25).tolist()); print(' spd',np.round(r,2).tolist()); print(' out',np.round(ro,2).tolist())
T("done")
