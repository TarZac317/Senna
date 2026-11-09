# Load MakeHuman (CC0) base mesh data, apply targets, return arrays in Blender coords (meters, Z-up, front -Y)
import numpy as np, json, os
D = os.path.join(os.path.dirname(__file__), '..', 'dl', 'mh', 'makehuman', 'data')

def load_obj(path):
    V=[]; VT=[]; F=[]; FT=[]; G=[]; g=None
    for line in open(path):
        if line.startswith('v '): V.append([float(x) for x in line.split()[1:4]])
        elif line.startswith('vt '): VT.append([float(x) for x in line.split()[1:3]])
        elif line.startswith('g '): g=line.split()[1]
        elif line.startswith('f '):
            idx=[p.split('/') for p in line.split()[1:]]
            F.append([int(p[0])-1 for p in idx])
            FT.append([int(p[1])-1 if len(p)>1 and p[1] else -1 for p in idx])
            G.append(g)
    return np.array(V), np.array(VT) if VT else None, F, FT, G

def load_target(path):
    idx=[];d=[]
    for line in open(path):
        if not line.strip() or line[0]=='#': continue
        p=line.split(); idx.append(int(p[0])); d.append([float(x) for x in p[1:4]])
    return np.array(idx,dtype=int), np.array(d).reshape(-1,3)

def mh_to_blender(a):
    a=np.asarray(a); return np.stack([a[...,0], -a[...,2], a[...,1]], -1)*0.1

def build(age_young=0.55, muscle=0.62, weight=0.42, height=0.6):
    V,VT,F,FT,G = load_obj(os.path.join(D,'3dobjs','base.obj'))
    V=V.copy()
    T=os.path.join(D,'targets','macrodetails')
    ages={'young':age_young,'child':1-age_young}
    def mw(v):  # min/average/max split of a 0..1 slider
        if v<0.5: return {'min':(0.5-v)*2,'average':1-(0.5-v)*2,'max':0}
        return {'min':0,'average':1-(v-0.5)*2,'max':(v-0.5)*2}
    mus=mw(muscle); wts=mw(weight)
    def add(name,w):
        if w<=1e-6: return
        i,d=load_target(os.path.join(T,name))
        if len(i): V[i]+=d*w
    for a,aw in ages.items():
        add(f'caucasian-male-{a}.target',aw)
        for m,mwv in mus.items():
            for wn,ww in wts.items():
                add(f'universal-male-{a}-{m}muscle-{wn}weight.target',aw*mwv*ww)
                if height>0.5: add(f'height/male-{a}-{m}muscle-{wn}weight-maxheight.target',aw*mwv*ww*(height-0.5)*2)
                add(f'proportions/male-{a}-{m}muscle-{wn}weight-idealproportions.target',aw*mwv*ww*0.6)
    return V,VT,F,FT,G

def joints_and_bones(Vmh):
    sk=json.load(open(os.path.join(D,'rigs','default.mhskel')))
    J={k:Vmh[v].mean(0) for k,v in sk['joints'].items()}
    bones={}
    for n,b in sk['bones'].items():
        bones[n]=dict(head=mh_to_blender(J[b['head']]), tail=mh_to_blender(J[b['tail']]), parent=b['parent'])
    return bones, sk

def weights():
    return json.load(open(os.path.join(D,'rigs','default_weights.mhw')))['weights']

def fit_proxy(mhclo_path, Vmh_full):
    # returns proxy verts (blender coords) from mhclo binding
    lines=open(mhclo_path).read().split('\n')
    sc={}; refs=[]; mode=None; objf=None
    for l in lines:
        p=l.split()
        if not p or p[0].startswith('#'): continue
        if p[0] in ('x_scale','y_scale','z_scale'): sc[p[0][0]]=(int(p[1]),int(p[2]),float(p[3]))
        elif p[0]=='obj_file': objf=p[1]
        elif p[0]=='verts': mode='v'; continue
        elif mode=='v' and len(p)==9:
            refs.append(p)
        elif mode=='v' and len(p)==1: refs.append(p)
        elif mode=='v' and p[0] in ('delete_verts',): mode=None
    s=np.ones(3)
    for k,ax in zip('xyz',range(3)):
        a,b,d=sc[k]; s[ax]=abs(Vmh_full[a][ax]-Vmh_full[b][ax])/d
    out=[]
    for r in refs:
        if len(r)==1: out.append(Vmh_full[int(r[0])]); continue
        i=[int(x) for x in r[:3]]; w=[float(x) for x in r[3:6]]; o=np.array([float(x) for x in r[6:9]])
        out.append(sum(Vmh_full[i[k]]*w[k] for k in range(3))+o*s)
    return np.array(out), os.path.join(os.path.dirname(mhclo_path),objf)
