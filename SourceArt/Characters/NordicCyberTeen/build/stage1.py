import bpy, bmesh, numpy as np, sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import mh, bvh
from mathutils import Vector, Matrix
D=mh.D
bpy.ops.wm.read_factory_settings(use_empty=True)

V,VT,F,FT,G = mh.build()
bones, sk = mh.joints_and_bones(V)
B = mh.mh_to_blender(V)
# normalise: feet at z=0, height 1.78
body_f=[i for i,g in enumerate(G) if g=='body']
bv=np.unique(np.concatenate([F[i] for i in body_f]))
z0=B[bv,2].min(); H=B[bv,2].max()-z0; S=1.78/H
def xf(p): p=np.array(p,float).copy(); p[...,2]-=z0; return p*S
B=xf(B)
for b in bones.values(): b['head']=xf(b['head']); b['tail']=xf(b['tail'])
np.save(os.path.join(os.path.dirname(__file__),'B.npy'),B)
json.dump({'z0':float(z0),'S':float(S)},open(os.path.join(os.path.dirname(__file__),'xf.json'),'w'))

def make_mesh(name, groups, mat=None):
    fids=[i for i,g in enumerate(G) if g in groups]
    used=np.unique(np.concatenate([F[i] for i in fids]))
    remap={int(v):k for k,v in enumerate(used)}
    me=bpy.data.meshes.new(name)
    me.from_pydata(B[used].tolist(),[],[[remap[v] for v in F[i]] for i in fids])
    uv=me.uv_layers.new(name='UVMap')
    li=0
    for fi in fids:
        for t in FT[fi]:
            uv.data[li].uv=VT[t] if t>=0 else (0,0); li+=1
    me.validate(); me.update()
    for p in me.polygons: p.use_smooth=True
    ob=bpy.data.objects.new(name,me); bpy.context.scene.collection.objects.link(ob)
    ob['mh_index']=used.tolist()
    return ob, used

body, body_idx = make_mesh('Body',{'body'})
teeth, teeth_idx = make_mesh('Teeth',{'helper-upper-teeth','helper-lower-teeth'})
tongue, tongue_idx = make_mesh('Tongue',{'helper-tongue'})
tights, tights_idx = make_mesh('Tights',{'helper-tights'})
hair, hair_idx = make_mesh('HairCap',{'helper-hair'})

# eyes from proxy
Vfull=V
pv,objp=mh.fit_proxy(os.path.join(D,'eyes','high-poly','high-poly.mhclo'),Vfull)
EV,EVT,EF,EFT,EG=mh.load_obj(objp)
pb=xf(mh.mh_to_blender(pv))
me=bpy.data.meshes.new('Eyes'); me.from_pydata(pb.tolist(),[],EF)
uv=me.uv_layers.new(name='UVMap'); li=0
for ft in EFT:
    for t in ft: uv.data[li].uv=EVT[t]; li+=1
for p in me.polygons: p.use_smooth=True
eyes=bpy.data.objects.new('Eyes',me); bpy.context.scene.collection.objects.link(eyes)

# MH armature
arm_d=bpy.data.armatures.new('MHRig'); arm=bpy.data.objects.new('MHRig',arm_d); bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active=arm; bpy.ops.object.mode_set(mode='EDIT')
for n,b in bones.items():
    e=arm_d.edit_bones.new(n); e.head=Vector(b['head']); e.tail=Vector(b['tail'])
    if (e.tail-e.head).length<1e-4: e.tail=e.head+Vector((0,0,0.01))
for n,b in bones.items():
    if b['parent']: arm_d.edit_bones[n].parent=arm_d.edit_bones[b['parent']]
bpy.ops.object.mode_set(mode='OBJECT')

W=mh.weights()
def skin(ob, idx, use_mh=True):
    pos={int(v):k for k,v in enumerate(idx)}
    for bn,lst in W.items():
        vg=None
        for vi,w in lst:
            k=pos.get(vi)
            if k is None: continue
            if vg is None: vg=ob.vertex_groups.get(bn) or ob.vertex_groups.new(name=bn)
            vg.add([k],w,'REPLACE')
    m=ob.modifiers.new('Armature','ARMATURE'); m.object=arm
for ob,idx in [(body,body_idx),(teeth,teeth_idx),(tongue,tongue_idx),(tights,tights_idx),(hair,hair_idx)]:
    skin(ob,idx)
# eyes: weight to eye bones by side
vgL=eyes.vertex_groups.new(name='eye.L'); vgR=eyes.vertex_groups.new(name='eye.R')
for v in eyes.data.vertices:
    (vgL if v.co.x>0 else vgR).add([v.index],1.0,'REPLACE')
m=eyes.modifiers.new('Armature','ARMATURE'); m.object=arm

# --- face shape keys from MH face pose units
frames=bvh.load_bvh(os.path.join(D,'poseunits','face-poseunits.bvh'))
names=json.load(open(os.path.join(D,'poseunits','face-poseunits.json')))['framemapping']
dg=bpy.context.evaluated_depsgraph_get()
def coords(ob):
    e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get()); m=e.to_mesh()
    c=np.array([v.co[:] for v in m.vertices]); e.to_mesh_clear(); return c
rest={ob.name:coords(ob) for ob in (body,teeth,tongue)}
shapes={}
for fi,nm in enumerate(names):
    if fi==0: continue
    fr=frames[fi]
    for pbn in arm.pose.bones:
        R=fr.get(pbn.name)
        if R is None: pbn.matrix_basis=Matrix.Identity(4); continue
        Rr=pbn.bone.matrix_local.to_3x3()
        Bm=Rr.inverted()@R@Rr
        pbn.matrix_basis=Bm.to_4x4()
    bpy.context.view_layer.update()
    shapes[nm]={ob.name:coords(ob)-rest[ob.name] for ob in (body,teeth,tongue)}
for pbn in arm.pose.bones: pbn.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
np.save(os.path.join(os.path.dirname(__file__),'shapes.npy'),shapes,allow_pickle=True)
# quick diagnostics
for nm in ['JawDrop','LeftUpperLidClosed','MouthLeftPullUp','LeftBrowDown']:
    d=shapes[nm]['Body']; mag=np.linalg.norm(d,axis=1); i=mag.argmax()
    sel=mag>mag.max()*0.3
    print(nm,'max',mag.max().round(4),'meanpos',body.data.vertices[int(i)].co[:],'meandelta',d[sel].mean(0).round(4))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(__file__),'stage1.blend'))
