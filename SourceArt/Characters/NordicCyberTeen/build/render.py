import bpy, math
from mathutils import Vector
def setup(res=900, samples=24):
    sc=bpy.context.scene
    sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=samples
    sc.cycles.use_denoising=True
    sc.render.resolution_x=res; sc.render.resolution_y=res
    sc.view_settings.view_transform='AgX'; sc.view_settings.look='AgX - Medium High Contrast'
    w=bpy.data.worlds.new('W'); sc.world=w; w.use_nodes=True
    bg=w.node_tree.nodes['Background']; bg.inputs[0].default_value=(0.02,0.025,0.035,1); bg.inputs[1].default_value=1
    def light(name,loc,energy,color,size=2):
        l=bpy.data.lights.new(name,'AREA'); l.energy=energy; l.color=color; l.size=size
        o=bpy.data.objects.new(name,l); sc.collection.objects.link(o); o.location=loc
        d=Vector((0,0,1.2))-Vector(loc); o.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
    light('Key',(-2.2,-3,2.8),420,(1,0.95,0.9))
    light('Rim',(2.5,2.5,2.5),600,(0.3,0.8,1.0))
    light('Fill',(3,-2.5,1.0),110,(1,0.4,0.8))
    light('Rim2',(-2.5,2.5,2.0),260,(1.0,0.5,0.9))
    cam=bpy.data.cameras.new('Cam'); co=bpy.data.objects.new('Cam',cam); sc.collection.objects.link(co); sc.camera=co
    return co
def shot(co, path, target, dist, az, el=5, lens=50):
    t=Vector(target); a=math.radians(az); e=math.radians(el)
    co.location=t+Vector((math.sin(a)*math.cos(e), -math.cos(a)*math.cos(e), math.sin(e)))*dist
    co.data.lens=lens
    co.rotation_euler=(t-co.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.scene.render.filepath=path; bpy.ops.render.render(write_still=True)
