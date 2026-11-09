import bpy, sys, os, math, json
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE); import render
from mathutils import Euler, Quaternion
OUT=sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE,'stage2.blend'))
arm=bpy.data.objects['Armature']
for o in bpy.data.objects:
    if o.type=='MESH': o.select_set(True)
arm.select_set(True)
# save editable source + export FBX for UE4.27
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'NordicCyberTeen.blend'))
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT,'SK_NordicCyberTeen.fbx'), use_selection=False,
    object_types={'ARMATURE','MESH'}, apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
    use_mesh_modifiers=False, mesh_smooth_type='FACE', add_leaf_bones=False,
    primary_bone_axis='Y', secondary_bone_axis='X', use_armature_deform_only=False,
    bake_anim=False, path_mode='COPY', embed_textures=True, use_tspace=False)
PV=os.path.join(OUT,'previews'); os.makedirs(PV,exist_ok=True)
arm.hide_render=True
co=render.setup(1000,32)
render.shot(co,PV+'/01_front.png',(0,0,0.92),4.3,0,el=4)
render.shot(co,PV+'/02_three_quarter.png',(0,0,0.92),4.3,35,el=6)
render.shot(co,PV+'/03_back.png',(0,0,0.92),4.3,180,el=6)
render.shot(co,PV+'/04_face.png',(0,-0.06,1.62),0.75,20,el=3,lens=70)
render.shot(co,PV+'/05_head_back.png',(0,0.02,1.55),1.1,145,el=10,lens=60)
# expressions
body=bpy.data.objects['SK_Body']
expr={'neutral':{}, 'smile':{'mouthSmileLeft':1,'mouthSmileRight':1,'cheekSquintLeft':0.6,'cheekSquintRight':0.6},
      'blink':{'eyeBlinkLeft':1,'eyeBlinkRight':1}, 'jaw_open':{'jawOpen':1,'browInnerUp':0.6},
      'angry':{'browDownLeft':1,'browDownRight':1,'noseSneer':0.7,'mouthFrownLeft':0.7,'mouthFrownRight':0.7},
      'surprised':{'browInnerUp':1,'browOuterUpLeft':1,'browOuterUpRight':1,'eyeWideLeft':1,'eyeWideRight':1,'jawOpen':0.5}}
shaped=[o for o in bpy.data.objects if o.type=='MESH' and o.data.shape_keys]
bpy.context.scene.render.resolution_x=600; bpy.context.scene.render.resolution_y=600
for nm,keys in expr.items():
    for o in shaped:
        for kb in o.data.shape_keys.key_blocks[1:]: kb.value=keys.get(kb.name,0)
    render.shot(co,PV+f'/expr_{nm}.png',(0,-0.06,1.63),0.6,12,el=3,lens=75)
for o in shaped:
    for kb in o.data.shape_keys.key_blocks[1:]: kb.value=0
# pose test
P=arm.pose.bones
def rot(b,x=0,y=0,z=0):
    P[b].rotation_mode='XYZ'; P[b].rotation_euler=(math.radians(x),math.radians(y),math.radians(z))
rot('upperarm_l',0,0,0); 
import mathutils
def world_rot(bname, axis, deg):
    pb=P[bname]; M=pb.bone.matrix_local.to_3x3()
    q=mathutils.Matrix.Rotation(math.radians(deg),3,axis)
    pb.rotation_mode='QUATERNION'; pb.rotation_quaternion=(M.inverted()@q@M).to_quaternion()
world_rot('upperarm_r','Y',-35); world_rot('lowerarm_r','X',-70)
world_rot('upperarm_l','Y',40); world_rot('upperarm_l','Y',40)
world_rot('lowerarm_l','Z',-60)
world_rot('thigh_l','X',-40); world_rot('calf_l','X',60)
world_rot('head','Z',20); world_rot('spine_02','Z',-10)
for i in range(1,5): world_rot(f'hair_braid_0{i}','Y',10)
for f in ['index','middle','ring','pinky']:
    for j in (1,2,3): world_rot(f'{f}_0{j}_l','X',50)
bpy.context.scene.render.resolution_x=1000; bpy.context.scene.render.resolution_y=1000
render.shot(co,PV+'/06_pose_test.png',(0,0,0.92),4.3,30,el=6)
print('DONE')
