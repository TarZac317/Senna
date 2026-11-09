import bpy, bmesh, numpy as np, sys, os, math, random, json
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
random.seed(7); np.random.seed(7)
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'stage1.blend'))
O = bpy.data.objects
body, teeth, tongue, tights, hcap, eyes, mhrig = (O[n] for n in ['Body','Teeth','Tongue','Tights','HairCap','Eyes','MHRig'])
shapes = np.load(os.path.join(HERE, 'shapes.npy'), allow_pickle=True).item()
scene = bpy.context.scene

def link(ob):
    scene.collection.objects.link(ob); return ob

# ---------------------------------------------------------------- materials
def mat(name, col, rough=0.5, metal=0.0, emit=None, estr=0.0, sss=0.0, tex=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*col, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    if emit:
        p.inputs['Emission Color'].default_value = (*emit, 1)
        p.inputs['Emission Strength'].default_value = estr
    if sss:
        p.inputs['Subsurface Weight'].default_value = sss
        p.inputs['Subsurface Radius'].default_value = (0.9, 0.35, 0.2)
        p.inputs['Subsurface Scale'].default_value = 0.01
    if tex:
        t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(tex)
        m.node_tree.links.new(t.outputs['Color'], p.inputs['Base Color'])
    m.diffuse_color = (*col, 1)
    return m
M = dict(
    skin=mat('M_Skin', (0.74, 0.52, 0.41), 0.45, sss=0.2),
    eye=mat('M_Eye', (1, 1, 1), 0.08, tex=os.path.join(HERE, 'eye_blue.png')),
    teeth=mat('M_Teeth', (0.85, 0.82, 0.74), 0.3),
    tongue=mat('M_Tongue', (0.55, 0.22, 0.22), 0.45),
    hair=mat('M_Hair_Blond', (0.78, 0.60, 0.33), 0.38),
    hair2=mat('M_Hair_Blond_Light', (0.90, 0.76, 0.48), 0.35),
    stubble=mat('M_Hair_Stubble', (0.36, 0.27, 0.15), 0.8),
    jacket=mat('M_Jacket_Techwear', (0.025, 0.03, 0.055), 0.42, 0.15),
    under=mat('M_Undersuit', (0.05, 0.05, 0.06), 0.6),
    pants=mat('M_Pants_Cargo', (0.045, 0.05, 0.045), 0.7),
    leather=mat('M_Leather', (0.16, 0.08, 0.035), 0.55),
    metal=mat('M_Metal_Gunmetal', (0.42, 0.44, 0.47), 0.42, 1.0),
    fur=mat('M_Fur', (0.26, 0.21, 0.16), 0.95),
    boots=mat('M_Boots', (0.02, 0.02, 0.022), 0.4),
    glow=mat('M_Rune_Glow', (0.0, 0.6, 0.8), 0.3, emit=(0.0, 0.85, 1.0), estr=12.0),
    glow2=mat('M_Cyber_Glow_Magenta', (0.8, 0.0, 0.5), 0.3, emit=(1.0, 0.1, 0.6), estr=10.0),
)
def setmat(ob, m):
    ob.data.materials.clear(); ob.data.materials.append(m)

setmat(body, M['skin']); setmat(eyes, M['eye'])
_bm = bmesh.new(); _bm.from_mesh(eyes.data); _uv = _bm.loops.layers.uv[0]
bmesh.ops.delete(_bm, geom=[v for v in _bm.verts if any(l[_uv].uv.x > 0.85 for l in v.link_loops)], context='VERTS')
bmesh.ops.delete(_bm, geom=[v for v in _bm.verts if v.co.x < 0], context='VERTS')
_m = bmesh.ops.mirror(_bm, geom=list(_bm.verts) + list(_bm.edges) + list(_bm.faces), axis='X', merge_dist=0.0)
_bm.to_mesh(eyes.data); _bm.free(); setmat(teeth, M['teeth'])
for v in teeth.data.vertices: v.co.y += 0.003; setmat(tongue, M['tongue'])

# ---------------------------------------------------------------- helpers
def dominant(ob):
    """dominant MH bone name per vertex"""
    names = [g.name for g in ob.vertex_groups]
    out = []
    for v in ob.data.vertices:
        best = None; bw = -1
        for g in v.groups:
            if g.weight > bw: bw = g.weight; best = names[g.group]
        out.append(best or '')
    return out

def pick(dom, prefixes):
    return [any(d.startswith(p) for p in prefixes) for d in dom]

def shell(src, name, vert_ok, offset, material, all_verts=True, solid=0.0):
    """copy faces of src whose verts satisfy vert_ok, push along normals"""
    bm = bmesh.new(); bm.from_mesh(src.data)
    bm.verts.ensure_lookup_table()
    kill = [f for f in bm.faces if (not all(vert_ok[v.index] for v in f.verts) if all_verts else not any(vert_ok[v.index] for v in f.verts))]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.normal_update()
    off = offset if callable(offset) else (lambda co, n: offset)
    for v in bm.verts:
        v.co = v.co + v.normal * off(v.co, v.normal)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = link(bpy.data.objects.new(name, me))
    for g in src.vertex_groups: ob.vertex_groups.new(name=g.name)
    setmat(ob, material)
    for p in me.polygons: p.use_smooth = True
    if solid:
        s = ob.modifiers.new('Solid', 'SOLIDIFY'); s.thickness = solid; s.offset = -1
        apply_mods(ob)
    return ob

def apply_mods(ob):
    with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob], selected_editable_objects=[ob]):
        for m in list(ob.modifiers):
            if m.type != 'ARMATURE':
                bpy.ops.object.modifier_apply(modifier=m.name)

def bvh_of(*obs):
    verts = []; polys = []; off = 0
    for ob in obs:
        mw = ob.matrix_world
        verts += [mw @ v.co for v in ob.data.vertices]
        polys += [[i + off for i in p.vertices] for p in ob.data.polygons]
        off += len(ob.data.vertices)
    return BVHTree.FromPolygons(verts, polys)

def transfer_weights(dst, src=None):
    src = src or body
    for g in src.vertex_groups:
        if g.name not in dst.vertex_groups: dst.vertex_groups.new(name=g.name)
    m = dst.modifiers.new('DT', 'DATA_TRANSFER'); m.object = src
    m.use_vert_data = True; m.data_types_verts = {'VGROUP_WEIGHTS'}
    m.vert_mapping = 'POLYINTERP_NEAREST'
    m.layers_vgroup_select_src = 'ALL'; m.layers_vgroup_select_dst = 'NAME'
    with bpy.context.temp_override(object=dst, active_object=dst, selected_objects=[dst], selected_editable_objects=[dst]):
        bpy.ops.object.modifier_move_to_index(modifier='DT', index=0)
        bpy.ops.object.modifier_apply(modifier='DT')

def mesh_obj(name, verts, faces, material):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.validate(); me.update()
    ob = link(bpy.data.objects.new(name, me)); setmat(ob, material)
    for p in me.polygons: p.use_smooth = True
    return ob

def tube(points, radius, sides=6, taper=None, closed_caps=True, flat=1.0, up=None):
    """tube mesh along polyline; radius may be list. returns verts, faces"""
    P = [Vector(p) for p in points]; n = len(P)
    rad = radius if isinstance(radius, (list, tuple, np.ndarray)) else [radius] * n
    V = []; Fc = []
    prev_n = None
    for i in range(n):
        t = (P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized()
        if prev_n is None:
            a = up if up is not None else (Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0)))
            nx = t.cross(a).normalized()
        else:
            nx = (prev_n - t * prev_n.dot(t)).normalized()
        prev_n = nx; ny = t.cross(nx)
        for k in range(sides):
            a = 2 * math.pi * k / sides
            V.append(P[i] + (nx * math.cos(a) + ny * math.sin(a) * flat) * rad[i])
    for i in range(n - 1):
        for k in range(sides):
            a = i * sides + k; b = i * sides + (k + 1) % sides
            Fc.append([a, b, b + sides, a + sides])
    if closed_caps:
        V.append(P[0]); V.append(P[-1]); c0 = len(V) - 2; c1 = len(V) - 1
        for k in range(sides):
            Fc.append([c0, (k + 1) % sides, k])
            Fc.append([c1, (n - 1) * sides + k, (n - 1) * sides + (k + 1) % sides])
    return V, Fc

class Builder:
    def __init__(s): s.V = []; s.F = []
    def add(s, V, F):
        o = len(s.V); s.V += [tuple(v) for v in V]; s.F += [[i + o for i in f] for f in F]

def project_line(pts2d, plane, tree, center, lift=0.002, samples=6):
    """pts2d in plane coords; plane='front'|'back'|'left': cast toward object and return surface points"""
    out = []
    for a, b in zip(pts2d[:-1], pts2d[1:]):
        for j in range(samples):
            t = j / samples
            u = a[0] + (b[0] - a[0]) * t; w = a[1] + (b[1] - a[1]) * t
            if plane == 'front': o = Vector((u, -1.0, w)); d = Vector((0, 1, 0))
            elif plane == 'back': o = Vector((u, 1.0, w)); d = Vector((0, -1, 0))
            elif plane == 'left': o = Vector((1.0, u, w)); d = Vector((-1, 0, 0))
            hit = tree.ray_cast(o, d)
            if hit[0] is not None: out.append(hit[0] + hit[1] * lift)
    if pts2d:
        pass
    return out

# ---------------------------------------------------------------- key positions
bones = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in mhrig.data.bones}
head_c = (bones['head'][0] + bones['head'][1]) / 2 + Vector((0, -0.012, 0.0))
neck_z = bones['neck01'][0].z
body_tree = bvh_of(body)
dom_t = dominant(tights)
dom_b = dominant(body)
tv = [v.co for v in tights.data.vertices]
bvco = [v.co for v in body.data.vertices]

# ---------------------------------------------------------------- outfit
TORSO = ('spine', 'breast', 'clavicle', 'shoulder', 'neck')
ARMS = ('upperarm', 'lowerarm')
LEGS = ('root', 'pelvis', 'upperleg', 'lowerleg')

# undersuit (long sleeve compression top)
ok = pick(dom_t, TORSO + ARMS)
under = shell(tights, 'Undersuit', ok, 0.0025, M['under'])

# pants, tucked into boots
ok = [d and z > 0.30 for d, z in zip(pick(dom_t, LEGS + ('spine05',)), [c.z for c in tv])]
pants = shell(tights, 'Pants', ok, lambda co, n: 0.006 + 0.006 * max(0, min(1, (0.75 - abs(co.z - 0.62) * 3))), M['pants'])

# cargo pockets + thigh straps (techwear)
pk_tree = bvh_of(pants)
pocket_parts = []
strap_b = Builder()
for side in (1, -1):
    sn = 'L' if side > 0 else 'R'
    a = bones[f'upperleg01.{sn}'][0]; b_ = bones[f'upperleg02.{sn}'][1]
    c = a.lerp(b_, 0.52)
    hit = pk_tree.ray_cast(Vector((side * 1.0, c.y, c.z)), Vector((-side, 0, 0)))
    if not hit[0]: continue
    bmp = bmesh.new(); bmesh.ops.create_cube(bmp, size=1.0)
    bmesh.ops.scale(bmp, vec=(0.03, 0.10, 0.12), verts=bmp.verts)
    bmesh.ops.bevel(bmp, geom=list(bmp.edges), offset=0.006, segments=2, affect='EDGES')
    bmesh.ops.translate(bmp, vec=hit[0] + Vector((side * 0.008, 0, 0)), verts=bmp.verts)
    mp_ = bpy.data.meshes.new('Pocket'); bmp.to_mesh(mp_); bmp.free()
    po = link(bpy.data.objects.new('Pocket', mp_)); setmat(po, M['pants'])
    pocket_parts.append(po)
    for dz in (0.035, -0.035):
        ring = []
        for k in range(24):
            ang = 2 * math.pi * k / 24; d = Vector((math.cos(ang), math.sin(ang), 0))
            cc = Vector((c.x, c.y, c.z + dz))
            h2 = pk_tree.ray_cast(cc + d * 0.3, -d)
            r = (h2[0] - cc).length if h2[0] else 0.08
            if d.x * side > 0.5: r += 0.03
            ring.append(cc + d * (r + 0.005))
        ring.append(ring[0])
        V, Fc = tube(ring, 0.006, 4, closed_caps=False, flat=0.35, up=Vector((0, 0, 1))); strap_b.add(V, Fc)
straps = mesh_obj('ThighStraps', strap_b.V, strap_b.F, M['leather'])

# jacket: torso + upper arms + sleeves to mid forearm
zj = bones['spine05'][0].z - 0.07
ok = [d and c.z > zj for d, c in zip(pick(dom_t, TORSO + ('upperarm', 'lowerarm01', 'root', 'pelvis', 'upperleg')), tv)]
jacket = shell(tights, 'Jacket', ok, 0.014, M['jacket'])
# collar + hem by extruding boundary loops
bm = bmesh.new(); bm.from_mesh(jacket.data)
bnd = [e for e in bm.edges if e.is_boundary]
collar_e = [e for e in bnd if all(v.co.z > neck_z - 0.06 and abs(v.co.x) < 0.11 for v in e.verts)]
hem_e = [e for e in bnd if all(v.co.z < zj + 0.06 for v in e.verts)]
def extrude(edges, fn, steps=1):
    cur = edges
    for s in range(steps):
        r = bmesh.ops.extrude_edge_only(bm, edges=cur)
        nv = [g for g in r['geom'] if isinstance(g, bmesh.types.BMVert)]
        for v in nv: v.co = fn(v.co, s)
        cur = [g for g in r['geom'] if isinstance(g, bmesh.types.BMEdge) and all(x in nv for x in g.verts)]
nc = Vector((0, bones['neck01'][0].y, 0))
def collar_fn(co, s):
    r = Vector((co.x, co.y - nc.y, 0)); r = r.normalized() * (r.length + 0.006)
    return Vector((r.x, r.y + nc.y, co.z + 0.022))
extrude(collar_e, collar_fn, 2)
def hem_fn(co, s):
    r = Vector((co.x, co.y - bones['root'][0].y, 0)); r = r.normalized() * (r.length + 0.012)
    return Vector((r.x, r.y + bones['root'][0].y, co.z - 0.07))
bm.to_mesh(jacket.data); bm.free()
s = jacket.modifiers.new('Solid', 'SOLIDIFY'); s.thickness = 0.004; s.offset = 1
apply_mods(jacket)
transfer_weights(jacket)

# fur mantle across shoulders (Nordic)
jt = [v.co.copy() for v in jacket.data.vertices]
sh_z = bones['clavicle.L'][0].z
def mantle_ok_fn(co):
    return co.z > sh_z - 0.075 - 0.07 * min(1, max(0, co.y) * 12) and abs(co.x) < 0.23 and co.z < neck_z + 0.03
src_bm_ok = [mantle_ok_fn(c) for c in tv]
mantle = shell(tights, 'FurMantle', src_bm_ok, 0.030, M['fur'], solid=0.006)
# fur tufts
tb = Builder()
mp = mantle.data.polygons
for p in mp:
    if random.random() > 0.97: continue
    c = p.center; n = p.normal
    if n.z < -0.3: continue
    dn = Vector((random.uniform(-.25, .25), random.uniform(-.1, .1), -1)); dn = (dn - n * dn.dot(n)).normalized()
    d = (dn + n * 0.25).normalized()
    L = random.uniform(0.016, 0.028)
    pts = [c - n * 0.004, c + d * L * 0.5 + n * 0.008, c + d * L + n * 0.004]
    V, Fc = tube(pts, [0.008, 0.006, 0.001], sides=6, closed_caps=False, flat=0.25, up=n)
    tb.add(V, Fc)
tufts = mesh_obj('FurTufts', tb.V, tb.F, M['fur'])

# metal pauldron on left shoulder
pl = bones['shoulder01.L'][1]
paul_ok = [ (c - pl).length < 0.11 and c.z > pl.z - 0.05 for c in tv]
paul = shell(tights, 'Pauldron', paul_ok, 0.042, M['metal'], solid=0.006)

# bracers on forearms (leather) with metal rings + glow band
bb = Builder(); gb = Builder()
for side in ('L', 'R'):
    a = bones[f'lowerarm01.{side}'][0]; w = bones[f'wrist.{side}'][0]
    ax = (w - a)
    for t0, kind in ((0.45, 'm'), (0.97, 'm'), (0.72, 'g')):
        c = a + ax * t0
        # radius from body
        rs = []
        perp = ax.normalized().cross(Vector((0, 0, 1))).normalized(); perp2 = ax.normalized().cross(perp)
        ring = []
        for k in range(16):
            ang = 2 * math.pi * k / 16
            d = perp * math.cos(ang) + perp2 * math.sin(ang)
            hit = body_tree.ray_cast(c + d * 0.2, -d)
            r = (hit[0] - c).length if hit[0] else 0.035
            ring.append(c + d * (r + (0.016 if kind == 'm' else 0.0135)))
        ring.append(ring[0])
        V, Fc = tube(ring, 0.004 if kind == 'm' else 0.0025, sides=6, closed_caps=False)
        (bb if kind == 'm' else gb).add(V, Fc)
ok = [d.startswith('lowerarm') and ((c - bones['lowerarm01.L' if c.x > 0 else 'lowerarm01.R'][0]).length > 0.10) for d, c in zip(dom_t, tv)]
bracers = shell(tights, 'Bracers', ok, 0.012, M['leather'], solid=0.004)

# boots from body
ok = [0.09 < c.z < 0.36 for c in bvco]
boots = shell(body, 'Boots', ok, 0.011, M['boots'], solid=0.004)
boot_feet = []
for side in (1, -1):
    pts = [c for c in bvco if c.z < 0.13 and c.x * side > 0]
    bmf = bmesh.new()
    for p in pts: bmf.verts.new(p)
    bmesh.ops.convex_hull(bmf, input=list(bmf.verts))
    bmesh.ops.delete(bmf, geom=[v for v in bmf.verts if not v.link_faces], context='VERTS')
    cen = sum((v.co for v in bmf.verts), Vector()) / len(bmf.verts)
    for v in bmf.verts:
        d = v.co - cen
        v.co = cen + Vector((d.x * 1.12, d.y * 1.07, d.z * 1.05))
        if v.co.z < 0.006: v.co.z = -0.012
    mf = bpy.data.meshes.new('BootFoot'); bmf.to_mesh(mf); bmf.free()
    fo = link(bpy.data.objects.new('BootFoot', mf)); setmat(fo, M['boots'])
    sub = fo.modifiers.new('Sub', 'SUBSURF'); sub.levels = 2; sub.render_levels = 2
    apply_mods(fo)
    for p in fo.data.polygons: p.use_smooth = True
    boot_feet.append(fo)
# glow ring at boot top
for side in (1, -1):
    k = bones['lowerleg02.L' if side > 0 else 'lowerleg02.R']
    c = Vector((k[0].x, k[0].y, 0.345)); ring = []
    for i in range(20):
        ang = 2 * math.pi * i / 20; d = Vector((math.cos(ang), math.sin(ang), 0))
        hit = body_tree.ray_cast(c + d * 0.2, -d)
        r = (hit[0] - c).length if hit[0] else 0.05
        ring.append(c + d * (r + 0.014))
    ring.append(ring[0]); V, Fc = tube(ring, 0.003, sides=6, closed_caps=False); gb.add(V, Fc)

# fingerless gloves
ok = [d.startswith(('wrist', 'metacarpal', 'finger1-1')) or (d.endswith(('-1.L', '-1.R')) and d.startswith('finger')) for d in dom_b]
gloves = shell(body, 'Gloves', ok, 0.0022, M['boots'])

# belt
pants_tree = bvh_of(pants)
bz = bones['spine05'][0].z - 0.035
bc = Vector((0, bones['root'][0].y, bz))
ring = []
for i in range(48):
    ang = 2 * math.pi * i / 48; d = Vector((math.cos(ang), math.sin(ang), 0))
    hit = pants_tree.ray_cast(bc + d * 0.4, -d)
    r = (hit[0] - bc).length if hit[0] else 0.15
    ring.append((d, r))
BV = []; BF = []
for i, (d, r) in enumerate(ring):
    for h in (-0.02, 0.02):
        BV.append(bc + d * (r + 0.006) + Vector((0, 0, h)))
for i in range(48):
    a = 2 * i; b = 2 * ((i + 1) % 48)
    BF.append([a, b, b + 1, a + 1])
belt = mesh_obj('Belt', BV, BF, M['leather'])
s = belt.modifiers.new('S', 'SOLIDIFY'); s.thickness = 0.005; apply_mods(belt)
# buckle (front, -Y)
fr = pants_tree.ray_cast(bc + Vector((0, -0.5, 0)), Vector((0, 1, 0)))[0]
bk = bpy.data.meshes.new('bk'); bmb = bmesh.new(); bmesh.ops.create_cube(bmb, size=1.0)
bmesh.ops.scale(bmb, vec=(0.06, 0.012, 0.045), verts=bmb.verts)
bmesh.ops.translate(bmb, vec=fr + Vector((0, -0.012, 0)), verts=bmb.verts)
bmb.to_mesh(bk); bmb.free(); buckle = link(bpy.data.objects.new('Buckle', bk)); setmat(buckle, M['metal'])
V, Fc = tube([fr + Vector((-0.018, -0.019, -0.012)), fr + Vector((0, -0.019, 0.014)), fr + Vector((0.018, -0.019, -0.012))], 0.0025, 4); gb.add(V, Fc)

# glowing runes: chest circuit lines, Algiz on the back, Tiwaz on pauldron
jtree = bvh_of(jacket)
chest_top = bones['spine01'][1].z - 0.02; chest_bot = zj + 0.05
for x in (0.075, -0.075):
    pts = project_line([(x, chest_top), (x, chest_top - 0.06), (x * 1.35, chest_top - 0.11), (x * 1.35, chest_bot)], 'front', jtree, None, 0.003)
    if len(pts) > 2: V, Fc = tube(pts, 0.0022, 4); gb.add(V, Fc)
# Algiz (ᛉ) on back
bz0 = chest_bot + 0.03; bz1 = chest_top - 0.02; mid = (bz0 + bz1) / 2
for seg in ([(0, bz0), (0, bz1)], [(0, mid), (0.08, bz1)], [(0, mid), (-0.08, bz1)]):
    pts = project_line(seg, 'back', jtree, None, 0.003, samples=24)
    if len(pts) > 2: V, Fc = tube(pts, 0.004, 4); gb.add(V, Fc)
# circle around the rune
circ = [(0.13 * math.cos(a) * 0.85, mid + 0.13 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 49)]
pts = project_line(circ, 'back', jtree, None, 0.003, samples=2)
if len(pts) > 2: V, Fc = tube(pts, 0.0025, 4); gb.add(V, Fc)
# Tiwaz (ᛏ) on pauldron, projected from the side
ptree = bvh_of(paul)
py, pz = pl.y, pl.z
for seg in ([(py, pz + 0.035), (py, pz - 0.05)], [(py - 0.03, pz + 0.0), (py, pz + 0.035)], [(py + 0.03, pz + 0.0), (py, pz + 0.035)]):
    pts = project_line(seg, 'left', ptree, None, 0.003, samples=10)
    if len(pts) > 2: V, Fc = tube(pts, 0.003, 4); gb.add(V, Fc)

# pendant: small hammer (Mjolnir nod) on a chain over the jacket
pc = jtree.ray_cast(Vector((0, -1, chest_top - 0.03)), Vector((0, 1, 0)))[0] + Vector((0, -0.012, 0))
pb_ = Builder()
chain = []
for a in np.linspace(-math.pi * 0.9, math.pi * 0.9, 40):
    pass
nb = bones['neck01'][0]
for t in np.linspace(0, 1, 30):
    # catenary-ish path from left neck side to pendant to right
    ang = math.pi * (t * 2 - 1) * 0.5
    x = math.sin(ang) * 0.075
    zc = nb.z - 0.005 - (1 - math.cos(ang)) * 0 - (pc.z - nb.z) * -(math.cos(ang) ** 2) * -1
    p = Vector((x, 0, nb.z + (pc.z - nb.z) * (math.cos(ang) ** 1.5)))
    hit = jtree.ray_cast(Vector((x, -1, p.z)), Vector((0, 1, 0)))
    if hit[0]: chain.append(hit[0] + Vector((0, -0.006, 0)))
if len(chain) > 3:
    V, Fc = tube(chain, 0.0015, 4); pb_.add(V, Fc)
hb = bmesh.new()
bmesh.ops.create_cube(hb, size=1.0); bmesh.ops.scale(hb, vec=(0.032, 0.014, 0.018), verts=hb.verts)
bmesh.ops.translate(hb, vec=pc + Vector((0, -0.004, -0.045)), verts=hb.verts)
r = bmesh.ops.create_cone(hb, cap_ends=True, segments=6, radius1=0.004, radius2=0.004, depth=0.03)
bmesh.ops.translate(hb, vec=pc + Vector((0, -0.004, -0.022)), verts=r['verts'])
hm = bpy.data.meshes.new('hm'); hb.to_mesh(hm); hb.free()
pend = link(bpy.data.objects.new('Pendant', hm)); setmat(pend, M['metal'])
chain_ob = mesh_obj('Chain', pb_.V, pb_.F, M['metal'])

# cyber implant on left temple + cheekbone: small glowing studs + line
fb = Builder()
eL = bones['eye.L'][0]
for i, (dx, dz) in enumerate([(0.035, 0.0), (0.045, 0.006), (0.055, 0.014), (0.06, 0.026)]):
    o = Vector((eL.x + dx + 0.2, eL.y + 0.02, eL.z + dz))
    target = Vector((head_c.x, eL.y + 0.02, eL.z + dz))
    d = (target - o).normalized(); hit = body_tree.ray_cast(o, d)
    if hit[0]:
        sph = bmesh.new(); bmesh.ops.create_uvsphere(sph, u_segments=8, v_segments=5, radius=0.0028)
        bmesh.ops.translate(sph, vec=hit[0] + hit[1] * 0.0008, verts=sph.verts)
        mtmp = bpy.data.meshes.new('t'); sph.to_mesh(mtmp); sph.free()
        fb.add([v.co.copy() for v in mtmp.vertices], [list(p.vertices) for p in mtmp.polygons]); bpy.data.meshes.remove(mtmp)

glow = mesh_obj('RuneGlow', gb.V, gb.F, M['glow'])
implant = mesh_obj('CyberImplant', fb.V, fb.F, M['glow2'])
metal_rings = mesh_obj('BracerRings', bb.V, bb.F, M['metal'])

# ---------------------------------------------------------------- hair
def is_scalp_dir(d):
    # hairline: above forehead, above/behind ears, down to nape
    if d.y < -0.2 and d.z < 0.55: return False      # face / forehead
    if d.z < -0.25: return False                     # nape below hairline
    if abs(d.x) > 0.62 and d.z < 0.28: return False  # ears
    if d.y < 0.25 and d.z < 0.05: return False       # sideburn/cheek
    return True
dom_head = [d == 'head' or d.startswith(('temporalis', 'oculi')) for d in dom_b]
eyeL = bones['eye.L'][0]
def scalp_pt(p):
    if (p - head_c).length > 0.16: return False
    dy = p.y - eyeL.y; dz = p.z - eyeL.z
    if dy < 0.05: return dz > 0.075          # forehead hairline
    if dy > 0.135: return dz > -0.07         # back of head down to nape
    return dz > 0.03                         # sides, above the ears
scalp_ok = [h and scalp_pt(c) for h, c in zip(dom_head, bvco)]
stub = shell(body, 'HairStubble', scalp_ok, 0.0018, M['stubble'])
_bm = bmesh.new(); _bm.from_mesh(stub.data)
_bd = [v for v in _bm.verts if v.is_boundary]
for it in range(12): bmesh.ops.smooth_vert(_bm, verts=_bd, factor=0.7, use_axis_x=True, use_axis_y=True, use_axis_z=True)
for v in _bd:
    loc, nrm, i_, dist = body_tree.find_nearest(v.co)
    if loc is not None: v.co = loc + nrm * 0.0012
_bm.to_mesh(stub.data); _bm.free()
head_tree = body_tree
def scalp(d):
    hit = head_tree.ray_cast(head_c + d * 0.3, -d)
    return (hit[0] - head_c).length if hit[0] else None
hb2 = Builder(); hb3 = Builder()
tie_dir = Vector((0, 0.80, 0.45)).normalized()
roots = []
for i in range(20000):
    d = Vector(np.random.normal(size=3)).normalized()
    if not is_scalp_dir(d) or d.z < 0.35: continue
    if abs(d.x) > 0.40: continue   # undercut: long hair only on a wide top strip
    if d.y < -0.2 and d.z < 0.62: continue  # keep hairline back from forehead
    roots.append(d)
    if len(roots) >= 300: break
def slerp(a, b, t):
    om = math.acos(max(-1, min(1, a.dot(b))))
    if om < 1e-4: return a
    return (a * math.sin((1 - t) * om) + b * math.sin(t * om)) / math.sin(om)
for k, d0 in enumerate(roots):
    jitter = Vector((random.uniform(-0.18, 0.18), random.uniform(-0.05, 0.05), random.uniform(-0.08, 0.08)))
    dT = (tie_dir + jitter * 0.5).normalized()
    front = max(0, -d0.y)  # front strands get more lift (swept-back quiff)
    pts = []; rad = []
    N = 16
    for i in range(N):
        t = i / (N - 1)
        d = slerp(d0, dT, t).normalized()
        d = (d + Vector((-d.x * 0.25 * t, 0, 0))).normalized()  # converge toward centre
        r0 = scalp(d) or 0.1
        lift = 0.002 + (0.012 + 0.022 * front) * math.sin(math.pi * min(1, t * 1.15)) ** 0.6 + 0.004 * t
        pts.append(head_c + d * (r0 + lift))
        rad.append(0.0042 * (1 - 0.45 * t) + 0.001)
    V, Fc = tube(pts, rad, sides=5)
    (hb2 if k % 4 else hb3).add(V, Fc)
# a few loose front strands
for x in ():
    d0 = Vector((x * 5, -0.75, 0.62)).normalized()
    r0 = scalp(d0) or 0.1; p0 = head_c + d0 * (r0 + 0.006)
    pts = [p0, p0 + Vector((x * 0.6, -0.025, 0.012)), p0 + Vector((x * 1.2, -0.04, -0.02)), p0 + Vector((x * 1.8, -0.042, -0.055))]
    V, Fc = tube(pts, [0.004, 0.0035, 0.0025, 0.0008], sides=5); hb3.add(V, Fc)

# braid from tie point down the back, over the mantle
outer_tree = bvh_of(body, jacket, mantle, tufts)
T0 = head_c + tie_dir * ((scalp(tie_dir) or 0.1) + 0.012)
braid_len = 0.30
cl = []
for i in range(40):
    s_ = i / 39; z = T0.z - braid_len * s_
    hit = outer_tree.ray_cast(Vector((0, 1.0, z)), Vector((0, -1, 0)))
    ysurf = hit[0].y if hit[0] else T0.y
    y = max(ysurf + 0.02, T0.y - 0.0 if s_ < 0.05 else ysurf + 0.02)
    cl.append(Vector((0, y, z)))
# smooth centreline
for it in range(6):
    cl = [cl[0]] + [(cl[i - 1] + cl[i] * 2 + cl[i + 1]) / 4 for i in range(1, len(cl) - 1)] + [cl[-1]]
braid_pts = cl
bb2 = Builder()
for k in range(3):
    pts = []; rad = []
    for i, c in enumerate(cl):
        s_ = i / (len(cl) - 1); ph = s_ * 2 * math.pi * 4.5 + 2 * math.pi * k / 3
        w = 0.011 * (1 - 0.35 * s_)
        pts.append(c + Vector((w * math.sin(ph), 0.006 * math.sin(2 * ph), 0)))
        rad.append(0.0095 * (1 - 0.35 * s_))
    V, Fc = tube(pts, rad, sides=8); bb2.add(V, Fc)
# end tuft
E = cl[-1]
for j in range(14):
    a = 2 * math.pi * j / 14
    pts = [E + Vector((0, 0, 0.01)), E + Vector((math.cos(a) * 0.008, math.sin(a) * 0.004, -0.03)), E + Vector((math.cos(a) * 0.014, math.sin(a) * 0.007 + 0.004, -0.06))]
    V, Fc = tube(pts, [0.004, 0.003, 0.0006], sides=5); bb2.add(V, Fc)
braid = mesh_obj('HairBraid', bb2.V, bb2.F, M['hair'])
hair_main = mesh_obj('Hair', hb2.V, hb2.F, M['hair'])
hair_hi = mesh_obj('HairHighlights', hb3.V, hb3.F, M['hair2'])
# braid bands: metal + glow
band = Builder(); bandg = Builder()
for s_ in (0.02, 0.97):
    i = int(s_ * (len(cl) - 1)); c = cl[i]
    ring = [c + Vector((math.cos(a) * 0.016, math.sin(a) * 0.013, 0)) for a in np.linspace(0, 2 * math.pi, 17)]
    V, Fc = tube(ring, 0.004, 6, closed_caps=False); band.add(V, Fc)
    ring = [c + Vector((math.cos(a) * 0.0175, math.sin(a) * 0.0145, 0)) for a in np.linspace(0, 2 * math.pi, 17)]
    V, Fc = tube(ring, 0.0015, 4, closed_caps=False); bandg.add(V, Fc)
bands = mesh_obj('BraidBands', band.V, band.F, M['metal'])
bandsg = mesh_obj('BraidBandsGlow', bandg.V, bandg.F, M['glow'])

# eyebrows (follow facial shapes)
ebb = Builder()
for side in (1, -1):
    e = bones['eye.L' if side > 0 else 'eye.R'][0]
    for j in range(46):
        u = random.random()
        x = e.x + side * (-0.017 + 0.052 * u)
        z = e.z + 0.020 + 0.010 * math.sin(math.pi * min(1, u * 1.2)) - 0.004 * u + random.uniform(-0.002, 0.002)
        hit = body_tree.ray_cast(Vector((x, -0.6, z)), Vector((0, 1, 0)))
        if not hit[0]: continue
        p = hit[0] + hit[1] * 0.0005
        dirv = Vector((side * 0.9, 0, 0.35 - 0.6 * u)).normalized()
        dirv = (dirv - hit[1] * dirv.dot(hit[1])).normalized()
        L = 0.006 + 0.004 * (1 - u)
        V, Fc = tube([p, p + dirv * L * 0.5 + hit[1] * 0.0008, p + dirv * L], [0.0009, 0.0007, 0.0002], sides=3, closed_caps=False)
        ebb.add(V, Fc)
brows = mesh_obj('Eyebrows', ebb.V, ebb.F, M['hair'])

# ---------------------------------------------------------------- weights for generated meshes
for ob in boot_feet + pocket_parts + [straps, mantle, tufts, paul, bracers, boots, gloves, belt, buckle, glow, implant, metal_rings, stub, pend, chain_ob, brows, under, pants]:
    if ob in (under, pants, bracers, boots, gloves, mantle, paul, stub):
        # already carry src groups; refine from body for smoothness
        for g in list(ob.vertex_groups): ob.vertex_groups.remove(g)
    transfer_weights(ob)

# ---------------------------------------------------------------- UE4 skeleton
def H(n): return bones[n][0]
def T(n): return bones[n][1]
UE = {}  # name: (head, tail, parent)
UE['root'] = (Vector((0, 0, 0)), Vector((0, 0.15, 0)), None)  # UE4 mannequin root lies flat at floor
UE['pelvis'] = (H('spine05'), H('spine05') + Vector((0, 0, 0.1)), 'root')
UE['spine_01'] = (H('spine05'), T('spine04'), 'pelvis')
UE['spine_02'] = (H('spine03'), T('spine03'), 'spine_01')
UE['spine_03'] = (H('spine02'), T('spine01'), 'spine_02')
UE['neck_01'] = (H('neck01'), T('neck03'), 'spine_03')
UE['head'] = (H('head'), T('head'), 'neck_01')
UE['jaw'] = (H('jaw'), T('jaw'), 'head')
for s, S in (('L', 'l'), ('R', 'r')):
    UE[f'eye_{S}'] = (H(f'eye.{s}'), T(f'eye.{s}'), 'head')
    UE[f'clavicle_{S}'] = (H(f'clavicle.{s}'), T(f'shoulder01.{s}'), 'spine_03')
    UE[f'upperarm_{S}'] = (H(f'upperarm01.{s}'), T(f'upperarm02.{s}'), f'clavicle_{S}')
    UE[f'upperarm_twist_01_{S}'] = (H(f'upperarm02.{s}'), T(f'upperarm02.{s}'), f'upperarm_{S}')
    UE[f'lowerarm_{S}'] = (H(f'lowerarm01.{s}'), T(f'lowerarm02.{s}'), f'upperarm_{S}')
    UE[f'lowerarm_twist_01_{S}'] = (H(f'lowerarm02.{s}'), T(f'lowerarm02.{s}'), f'lowerarm_{S}')
    UE[f'hand_{S}'] = (H(f'wrist.{s}'), T(f'wrist.{s}'), f'lowerarm_{S}')
    for fi, fn in enumerate(['thumb', 'index', 'middle', 'ring', 'pinky']):
        for j in range(3):
            par = f'hand_{S}' if j == 0 else f'{fn}_0{j}_{S}'
            UE[f'{fn}_0{j+1}_{S}'] = (H(f'finger{fi+1}-{j+1}.{s}'), T(f'finger{fi+1}-{j+1}.{s}'), par)
    UE[f'thigh_{S}'] = (H(f'upperleg01.{s}'), T(f'upperleg02.{s}'), 'pelvis')
    UE[f'thigh_twist_01_{S}'] = (H(f'upperleg02.{s}'), T(f'upperleg02.{s}'), f'thigh_{S}')
    UE[f'calf_{S}'] = (H(f'lowerleg01.{s}'), T(f'lowerleg02.{s}'), f'thigh_{S}')
    UE[f'calf_twist_01_{S}'] = (H(f'lowerleg02.{s}'), T(f'lowerleg02.{s}'), f'calf_{S}')
    UE[f'foot_{S}'] = (H(f'foot.{s}'), T(f'foot.{s}'), f'calf_{S}')
    bh = H(f'toe3-1.{s}'); UE[f'ball_{S}'] = (bh, bh + Vector((0, -0.05, 0)), f'foot_{S}')
# IK helper bones (same names/hierarchy as the UE4 Mannequin)
UE['ik_foot_root'] = (Vector((0, 0, 0)), Vector((0, 0, 0.1)), 'root')
UE['ik_hand_root'] = (Vector((0, 0, 0)), Vector((0, 0, 0.1)), 'root')
for S, s in (('l', 'L'), ('r', 'R')):
    UE[f'ik_foot_{S}'] = (H(f'foot.{s}'), H(f'foot.{s}') + Vector((0, 0, 0.08)), 'ik_foot_root')
UE['ik_hand_gun'] = (H('wrist.R'), H('wrist.R') + Vector((0, 0, 0.08)), 'ik_hand_root')
for S, s in (('l', 'L'), ('r', 'R')):
    UE[f'ik_hand_{S}'] = (H(f'wrist.{s}'), H(f'wrist.{s}') + Vector((0, 0, 0.08)), 'ik_hand_gun')
# braid bones for physics (AnimDynamics / RigidBody in UE)
nb_ = 4
for i in range(nb_):
    a = braid_pts[int(i * (len(braid_pts) - 1) / nb_)]; b = braid_pts[int((i + 1) * (len(braid_pts) - 1) / nb_)]
    UE[f'hair_braid_0{i+1}'] = (a, b, 'head' if i == 0 else f'hair_braid_0{i}')

arm_d = bpy.data.armatures.new('Armature'); arm = link(bpy.data.objects.new('Armature', arm_d))
arm_d.display_type = 'STICK'
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
for n, (h, t, p) in UE.items():
    e = arm_d.edit_bones.new(n); e.head = h; e.tail = t if (t - h).length > 1e-3 else h + Vector((0, 0, 0.02))
for n, (h, t, p) in UE.items():
    if p: arm_d.edit_bones[n].parent = arm_d.edit_bones[p]
for n in ['upperarm_twist_01_l', 'upperarm_twist_01_r', 'thigh_twist_01_l', 'thigh_twist_01_r']:
    pass
bpy.ops.object.mode_set(mode='OBJECT')

# MH -> UE weight map
def ue_for(mhn):
    side = 'l' if mhn.endswith('.L') else ('r' if mhn.endswith('.R') else '')
    b = mhn.split('.')[0]
    if b in ('root',) or b.startswith('pelvis'): return 'pelvis'
    if b in ('spine05', 'spine04'): return 'spine_01'
    if b == 'spine03': return 'spine_02'
    if b in ('spine02', 'spine01', 'breast'): return 'spine_03'
    if b.startswith('neck'): return 'neck_01'
    if b in ('jaw', 'special04') or b.startswith('tongue') or b in ('oris05', 'oris06') or (b in ('oris06',) and side): return 'jaw'
    if b == 'eye': return f'eye_{side}'
    if b in ('clavicle', 'shoulder01'): return f'clavicle_{side}'
    if b == 'upperarm01': return f'upperarm_{side}'
    if b == 'upperarm02': return f'upperarm_twist_01_{side}'
    if b == 'lowerarm01': return f'lowerarm_{side}'
    if b == 'lowerarm02': return f'lowerarm_twist_01_{side}'
    if b in ('wrist',) or b.startswith('metacarpal'): return f'hand_{side}'
    if b.startswith('finger'):
        f, j = b[6:].split('-'); return f"{['thumb','index','middle','ring','pinky'][int(f)-1]}_0{j}_{side}"
    if b == 'upperleg01': return f'thigh_{side}'
    if b == 'upperleg02': return f'thigh_twist_01_{side}'
    if b == 'lowerleg01': return f'calf_{side}'
    if b == 'lowerleg02': return f'calf_twist_01_{side}'
    if b == 'foot': return f'foot_{side}'
    if b.startswith('toe'): return f'ball_{side}'
    return 'head'

def remap(ob, override=None):
    names = [g.name for g in ob.vertex_groups]
    acc = [dict() for _ in ob.data.vertices]
    for v in ob.data.vertices:
        for g in v.groups:
            u = override or ue_for(names[g.group])
            acc[v.index][u] = acc[v.index].get(u, 0) + g.weight
    for g in list(ob.vertex_groups): ob.vertex_groups.remove(g)
    groups = {}
    for i, d in enumerate(acc):
        if not d: d = {override or 'head': 1.0}
        items = sorted(d.items(), key=lambda x: -x[1])[:4]
        tot = sum(w for _, w in items) or 1
        for u, w in items:
            if u not in groups: groups[u] = ob.vertex_groups.new(name=u)
            groups[u].add([i], w / tot, 'REPLACE')
    for m in list(ob.modifiers):
        if m.type == 'ARMATURE': ob.modifiers.remove(m)
    m = ob.modifiers.new('Armature', 'ARMATURE'); m.object = arm
    ob.parent = arm

def rigid(ob, bone):
    for g in list(ob.vertex_groups): ob.vertex_groups.remove(g)
    g = ob.vertex_groups.new(name=bone); g.add(list(range(len(ob.data.vertices))), 1.0, 'REPLACE')
    for m in list(ob.modifiers):
        if m.type == 'ARMATURE': ob.modifiers.remove(m)
    m = ob.modifiers.new('Armature', 'ARMATURE'); m.object = arm; ob.parent = arm

skinned = boot_feet + pocket_parts + [straps, body, teeth, tongue, under, pants, jacket, mantle, tufts, paul, bracers, boots, gloves, belt, buckle, metal_rings, implant, pend, chain_ob, brows, stub]
for ob in skinned: remap(ob)
# glow pieces: transfer per-piece from body weights already (data transfer), remap
remap(glow)
for ob in (hair_main, hair_hi): rigid(ob, 'head')
# eyes
for g in list(eyes.vertex_groups): eyes.vertex_groups.remove(g)
gl = eyes.vertex_groups.new(name='eye_l'); gr = eyes.vertex_groups.new(name='eye_r')
for v in eyes.data.vertices: (gl if v.co.x > 0 else gr).add([v.index], 1.0, 'REPLACE')
for m in list(eyes.modifiers): eyes.modifiers.remove(m)
m = eyes.modifiers.new('Armature', 'ARMATURE'); m.object = arm; eyes.parent = arm
# braid: weights along chain
for ob in (braid, bands, bandsg):
    for g in list(ob.vertex_groups): ob.vertex_groups.remove(g)
    gs = [ob.vertex_groups.new(name='head')] + [ob.vertex_groups.new(name=f'hair_braid_0{i+1}') for i in range(nb_)]
    z_top = braid_pts[0].z; z_bot = braid_pts[-1].z
    for v in ob.data.vertices:
        s_ = max(0, min(1, (z_top - v.co.z) / (z_top - z_bot))) * nb_  # 0..4
        i0 = int(math.floor(s_)); f = s_ - i0
        # bone i covers segment i; blend at joints
        idx = min(i0 + 1, nb_)  # group index: 0=head, 1..4 braid
        if s_ < 0.15: gs[0].add([v.index], 1.0, 'REPLACE'); continue
        gs[idx].add([v.index], 1.0 - 0.5 * max(0, f - 0.5) * 2 * (idx < nb_), 'REPLACE')
        if idx < nb_ and f > 0.5: gs[idx + 1].add([v.index], 0.5 * (f - 0.5) * 2, 'REPLACE')
    for m in list(ob.modifiers): ob.modifiers.remove(m)
    m = ob.modifiers.new('Armature', 'ARMATURE'); m.object = arm; ob.parent = arm

# ---------------------------------------------------------------- facial shape keys (ARKit-style names where they match)
ARK = {
 'LeftBrowDown': 'browDownLeft', 'RightBrowDown': 'browDownRight', 'LeftOuterBrowUp': 'browOuterUpLeft', 'RightOuterBrowUp': 'browOuterUpRight',
 ('LeftInnerBrowUp', 'RightInnerBrowUp'): 'browInnerUp', 'NoseWrinkler': 'noseSneer',
 'LeftUpperLidClosed': 'eyeBlinkLeft', 'RightUpperLidClosed': 'eyeBlinkRight', 'LeftUpperLidOpen': 'eyeWideLeft', 'RightUpperLidOpen': 'eyeWideRight',
 'LeftLowerLidUp': 'eyeSquintLeft', 'RightLowerLidUp': 'eyeSquintRight', 'LeftCheekUp': 'cheekSquintLeft', 'RightCheekUp': 'cheekSquintRight',
 'CheeksPump': 'cheekPuff', 'CheeksSuck': 'cheekSuck', 'NasolabialDeepener': 'nasolabialDeepen',
 'ChinLeft': 'jawLeft', 'ChinRight': 'jawRight', 'ChinForward': 'jawForward', 'ChinDown': 'chinDown', 'JawDrop': 'jawOpen', 'JawDropStretched': 'jawOpenStretched',
 'lowerLipUp': 'mouthLowerUp', 'lowerLipDown': 'mouthLowerDown', 'lowerLipBackward': 'mouthRollLower', 'lowerLipForward': 'mouthShrugLower',
 'UpperLipUp': 'mouthUpperUp', 'UpperLipBackward': 'mouthRollUpper', 'UpperLipForward': 'mouthShrugUpper', 'UpperLipStretched': 'mouthUpperStretch',
 'LipsKiss': 'mouthPucker', 'MouthMoveLeft': 'mouthLeft', 'MouthMoveRight': 'mouthRight',
 'MouthLeftPullUp': 'mouthSmileLeft', 'MouthRightPullUp': 'mouthSmileRight', 'MouthLeftPullSide': 'mouthStretchLeft', 'MouthRightPullSide': 'mouthStretchRight',
 'MouthLeftPullDown': 'mouthFrownLeft', 'MouthRightPullDown': 'mouthFrownRight', 'MouthLeftPlatysma': 'mouthPlatysmaLeft', 'MouthRightPlatysma': 'mouthPlatysmaRight',
 'TongueOut': 'tongueOut', 'TongueUshape': 'tongueUShape', 'TongueUp': 'tongueUp', 'TongueDown': 'tongueDown', 'TongueLeft': 'tongueLeft', 'TongueRight': 'tongueRight',
 'TonguePointUp': 'tonguePointUp', 'TonguePointDown': 'tonguePointDown',
}
final = {}
for k, v in ARK.items():
    ks = k if isinstance(k, tuple) else (k,)
    final[v] = {ob: sum(shapes[x][ob] for x in ks) for ob in ('Body', 'Teeth', 'Tongue')}
# combo: funnel
final['mouthFunnel'] = {ob: shapes['LipsKiss'][ob] * 0.7 + shapes['JawDrop'][ob] * 0.25 for ob in ('Body', 'Teeth', 'Tongue')}
# brows follow body via nearest vertex
from mathutils.kdtree import KDTree
kd = KDTree(len(body.data.vertices))
for v in body.data.vertices: kd.insert(v.co, v.index)
kd.balance()
brow_map = [kd.find(v.co)[1] for v in brows.data.vertices]
implant_map = [kd.find(v.co)[1] for v in implant.data.vertices]
def add_keys(ob, deltas_fn):
    ob.shape_key_add(name='Basis', from_mix=False)
    base = np.array([v.co[:] for v in ob.data.vertices])
    for nm in final:
        d = deltas_fn(nm)
        if d is None or np.abs(d).max() < 1e-5: continue
        k = ob.shape_key_add(name=nm, from_mix=False); k.value = 0.0
        k.data.foreach_set('co', (base + d).ravel())
add_keys(body, lambda nm: final[nm]['Body'])
add_keys(teeth, lambda nm: final[nm]['Teeth'])
add_keys(tongue, lambda nm: final[nm]['Tongue'])
add_keys(brows, lambda nm: final[nm]['Body'][brow_map])
add_keys(implant, lambda nm: final[nm]['Body'][implant_map])

_bm = bmesh.new(); _bm.from_mesh(body.data)
bmesh.ops.delete(_bm, geom=[f for f in _bm.faces if all(v.co.z < 0.30 for v in f.verts)], context='FACES')
bmesh.ops.delete(_bm, geom=[v for v in _bm.verts if not v.link_faces], context='VERTS')
_bm.to_mesh(body.data); _bm.free()
# ---------------------------------------------------------------- tidy + join into logical meshes
bpy.data.objects.remove(mhrig); bpy.data.objects.remove(tights); bpy.data.objects.remove(hcap)
def join(name, obs):
    obs = [o for o in obs if o and o.name in bpy.data.objects]
    tgt = obs[0]
    with bpy.context.temp_override(active_object=tgt, object=tgt, selected_objects=obs, selected_editable_objects=obs):
        bpy.ops.object.join()
    tgt.name = name; tgt.data.name = name
    return tgt
outfit = join('SK_Outfit', boot_feet + pocket_parts + [straps, jacket, under, pants, mantle, tufts, paul, bracers, metal_rings, boots, gloves, belt, buckle, pend, chain_ob, glow])
hair_all = join('SK_Hair', [hair_main, hair_hi, braid, bands, bandsg, stub])
for o in bpy.data.objects:
    if o.type == 'MESH':
        o.data.name = o.name
body.name = 'SK_Body'
stats = {o.name: (len(o.data.vertices), len(o.data.polygons), len(o.data.shape_keys.key_blocks) - 1 if o.data.shape_keys else 0) for o in bpy.data.objects if o.type == 'MESH'}
print('STATS', json.dumps(stats))
print('BONES', len(arm.data.bones))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'stage2.blend'))
