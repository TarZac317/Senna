import numpy as np, re
from mathutils import Matrix
def load_bvh(path):
    toks=open(path).read().split()
    i=0; joints=[]; stack=[]; chans={}
    order=[]
    while toks[i]!='MOTION':
        t=toks[i]
        if t in ('ROOT','JOINT'):
            name=toks[i+1]; joints.append(name); stack.append(name); i+=2; continue
        if t=='End': stack.append(None); i+=2; continue
        if t=='}': stack.pop(); i+=1; continue
        if t=='CHANNELS':
            n=int(toks[i+1]); ch=toks[i+2:i+2+n]; chans[stack[-1]]=ch; order.append((stack[-1],ch)); i+=2+n; continue
        i+=1
    i+=1; nf=int(toks[i+1]); i+=2; i+=3  # Frames: n Frame Time: x
    vals=np.array([float(x) for x in toks[i:]]).reshape(nf,-1)
    frames=[]
    for f in range(nf):
        k=0; fr={}
        for j,ch in order:
            v=vals[f,k:k+len(ch)]; k+=len(ch)
            R=Matrix.Identity(3)
            for c,a in zip(ch,v):
                if c.endswith('rotation'):
                    R=R@Matrix.Rotation(np.radians(a),3,c[0])
            fr[j]=R
        frames.append(fr)
    return frames
