"""Площадка v2 из ассетов Meshy (папка "3d meshed elements").

Выход: public/assets/environment2.glb
 - все модели: чистый PBR (basecolor + roughness), текстуры <=1024,
   децимация до игровых бюджетов, пивот в центре подошвы;
 - композиция: полукруг горка/качели/песочница сзади, дом и скамейка по
   бокам, кольцо забора, деревья/кусты/ромашки, облака (Cloud1..4);
 - Blocks и Chalk переезжают из старого environment.glb (нужны минигре);
 - узел GrassTuft спрятан под островом — движок строит из него
   InstancedMesh травы.

Запуск:
  /Applications/Blender.app/Contents/MacOS/Blender --background \
      --python tools/blender/build_environment2.py
"""

import math
import os

import bpy
from mathutils import Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DIR = os.path.join(ROOT, '3d meshed elements')
OLD_ENV = os.path.join(ROOT, 'public', 'assets', 'environment.glb')
OUT = os.path.join(ROOT, 'public', 'assets', 'environment2.glb')
OUT_PREVIEW = os.path.join(ROOT, 'tools', 'blender', 'preview_env2.png')

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# три-координаты (x, z) -> блендер (x, -z). Остров R=13.5, забор R~12.9.
def b(x_three, z_three):
    return (x_three, -z_three)

# ------------------------------------------------------------ helpers
def clean_material(obj, tex_size=1024, roughness=0.8):
    """Мусорный материал Meshy -> Principled: basecolor + roughness."""
    src_img = None
    for mat in obj.data.materials:
        if not mat or not mat.use_nodes:
            continue
        pr = next((n for n in mat.node_tree.nodes
                   if n.type == 'BSDF_PRINCIPLED'), None)
        if pr is None:
            continue
        inp = pr.inputs.get('Base Color')
        node = inp.links[0].from_node if (inp and inp.links) else None
        for _ in range(4):
            if node is None:
                break
            if node.type == 'TEX_IMAGE':
                src_img = node.image
                break
            node = (node.inputs[0].links[0].from_node
                    if node.inputs and node.inputs[0].links else None)
        if src_img:
            break
    clean = bpy.data.materials.new(obj.name + 'Mat')
    clean.use_nodes = True
    cpr = next(n for n in clean.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    cpr.inputs['Roughness'].default_value = roughness
    if src_img is not None:
        if max(src_img.size) > tex_size:
            src_img.scale(tex_size, tex_size)
        tex = clean.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image = src_img
        clean.node_tree.links.new(tex.outputs['Color'], cpr.inputs['Base Color'])
    obj.data.materials.clear()
    obj.data.materials.append(clean)


def decimate(obj, target_polys):
    n = len(obj.data.polygons)
    if n <= target_polys:
        return
    mod = obj.modifiers.new('dec', 'DECIMATE')
    mod.ratio = target_polys / n
    dg = bpy.context.evaluated_depsgraph_get()
    newmesh = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    obj.modifiers.remove(mod)
    old = obj.data
    obj.data = newmesh
    old_users = old.users
    if old_users == 0:
        bpy.data.meshes.remove(old)
    print(f'[dec] {obj.name}: {n} -> {len(obj.data.polygons)}')


def normalize(obj, height=None, width=None):
    """Пивот в центр подошвы + масштаб по росту/ширине (в данных меша)."""
    obj.data.transform(obj.matrix_world)
    obj.matrix_world = Matrix.Identity(4)
    vs = obj.data.vertices
    xs = [v.co.x for v in vs]
    ys = [v.co.y for v in vs]
    zs = [v.co.z for v in vs]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    obj.data.transform(Matrix.Translation((-cx, -cy, -min(zs))))
    dz = max(zs) - min(zs)
    dx = max(xs) - min(xs)
    s = (height / dz) if height else (width / dx)
    obj.data.transform(Matrix.Scale(s, 4))


def load_asset(fname, name, height=None, width=None, polys=8000,
               tex=1024):
    pre = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(SRC_DIR, fname))
    new = [o for o in bpy.data.objects if o not in pre]
    meshes = [o for o in new if o.type == 'MESH']
    keep = max(meshes, key=lambda o: len(o.data.vertices))
    for o in new:
        if o is not keep:
            bpy.data.objects.remove(o, do_unlink=True)
    keep.name = name
    keep.data.name = name
    clean_material(keep, tex_size=tex)
    decimate(keep, polys)
    normalize(keep, height=height, width=width)
    return keep


def place(obj, xz, rot_deg=0.0, scale=1.0):
    obj.location = (xz[0], xz[1], 0)
    obj.rotation_euler = (0, 0, math.radians(rot_deg))
    obj.scale = (scale, scale, scale)


def linked_copy(obj, name):
    c = obj.copy()  # общий меш — glTF дедуплицирует
    c.name = name
    scene.collection.objects.link(c)
    return c

# ------------------------------------------------------------ ассеты
F = {
    'house': 'Meshy_AI_Cozy_Clay_Cottage_0820123027_texture.glb',
    'fence': 'Meshy_AI_Rounded_Wooden_Fence_0820122801_texture.glb',
    'slide': 'Meshy_AI_Sagewood_Slide_0820122354_texture.glb',
    'swing': 'Meshy_AI_Woodland_Swing_Set_0820122118_texture.glb',
    'sandbox': 'Meshy_AI_Sandbox_Playset_0820122335_texture.glb',
    'bench': 'Meshy_AI_Garden_Bench_0820122320_texture.glb',
    'tree': 'Meshy_AI_Golden_Leaf_Whimsy_0820122208_texture.glb',
    'bush': 'Meshy_AI_Soft_Succulent_Canopy_0820122344_texture.glb',
    'grass': 'Meshy_AI_Emerald_Sprout_Cluste_0820122405_texture.glb',
    'daisy': 'Meshy_AI_Fabric_Daisy_Garden_0820122159_texture.glb',
    'cloud': 'Meshy_AI_Soft_Cloud_Cluster_0820122418_texture.glb',
    'ball': 'Meshy_AI_Vintage_Kickoff_0820122137_texture.glb',
}

house = load_asset(F['house'], 'House', height=3.4, polys=22000)
fence = load_asset(F['fence'], 'FenceSeg', width=2.3, polys=1600, tex=512)
slide = load_asset(F['slide'], 'Slide', height=2.3, polys=8000)
swing = load_asset(F['swing'], 'Swing', height=2.3, polys=8000)
sandbox = load_asset(F['sandbox'], 'Sandbox', width=3.0, polys=7000)
bench = load_asset(F['bench'], 'Bench', width=1.9, polys=5000)
tree = load_asset(F['tree'], 'Tree', height=3.8, polys=11000)
bush = load_asset(F['bush'], 'Bush0', width=1.7, polys=6000, tex=512)
grass = load_asset(F['grass'], 'GrassTuft', height=0.34, polys=2500, tex=512)
daisy = load_asset(F['daisy'], 'Daisy0', height=0.6, polys=4500, tex=512)
cloud = load_asset(F['cloud'], 'Cloud1', width=4.0, polys=2500, tex=256)
ball = load_asset(F['ball'], 'Ball', height=0.55, polys=2200, tex=512)

# ------------------------------------------------- Blocks/Chalk из старого
pre = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=OLD_ENV)
new = [o for o in bpy.data.objects if o not in pre]
kept_old = []
for want in ('Blocks', 'Chalk'):
    node = next((o for o in new if o.name.split('.')[0] == want), None)
    if node is not None:
        kept_old.append(node)
        node.name = want
        for ch in node.children_recursive:
            kept_old.append(ch)
keep_set = set(kept_old)
for o in new:
    if o not in keep_set and o.type in ('MESH', 'EMPTY', 'LIGHT', 'CAMERA', 'ARMATURE'):
        if o not in keep_set:
            bpy.data.objects.remove(o, do_unlink=True)
blocks = bpy.data.objects.get('Blocks')
chalk = bpy.data.objects.get('Chalk')

# ------------------------------------------------------------ композиция
place(house, b(-7.6, -7.9), rot_deg=-40)
place(slide, b(-1.7, -10.2), rot_deg=15)
place(swing, b(2.7, -11.2), rot_deg=4)
place(sandbox, b(5.4, -8.2), rot_deg=-12)
place(bench, b(8.0, -3.0), rot_deg=-65)
place(ball, b(3.5, 1.5), rot_deg=20)
if blocks:
    blocks.location = (-4, 2.5, 0)
if chalk:
    chalk.location = (1.5, 4, 0)

place(tree, b(6.4, -5.4), rot_deg=30)
t1 = linked_copy(tree, 'TreeDeco1')
place(t1, b(-11.0, -2.4), rot_deg=140, scale=0.9)
t2 = linked_copy(tree, 'TreeDeco2')
place(t2, b(9.6, -10.6), rot_deg=260, scale=1.12)
t3 = linked_copy(tree, 'TreeDeco3')
place(t3, b(-10.4, 3.6), rot_deg=80, scale=0.8)

bushes_parent = bpy.data.objects.new('Bushes', None)
scene.collection.objects.link(bushes_parent)
BUSH_SPOTS = [((-5.4, -11.4), 0, 1.0), ((11.2, -5.8), 70, 0.85),
              ((-11.8, 1.2), 30, 0.9), ((7.9, 3.6), 160, 0.8),
              ((-3.2, -12.4), 200, 0.75), ((11.6, 0.8), 300, 0.95)]
for i, (xz, rd, sc) in enumerate(BUSH_SPOTS):
    bobj = bush if i == 0 else linked_copy(bush, f'Bush{i}')
    place(bobj, b(*xz), rot_deg=rd, scale=sc)
    bobj.parent = bushes_parent

DAISY_SPOTS = [((2.4, -2.3), 15, 1.0), ((-6.2, -4.4), 120, 0.85),
               ((4.6, -10.9), 230, 0.9), ((-8.9, 1.8), 60, 0.8),
               ((10.4, -8.7), 310, 0.75)]
for i, (xz, rd, sc) in enumerate(DAISY_SPOTS):
    dobj = daisy if i == 0 else linked_copy(daisy, f'Daisy{i}')
    place(dobj, b(*xz), rot_deg=rd, scale=sc)

# кольцо забора
FENCE_R = 12.9
seg_w = 2.3
n_seg = int(math.ceil(2 * math.pi * FENCE_R / (seg_w * 0.9)))
fence_parent = bpy.data.objects.new('FenceRing', None)
scene.collection.objects.link(fence_parent)
for i in range(n_seg):
    a = i / n_seg * 2 * math.pi
    fobj = fence if i == 0 else linked_copy(fence, f'FenceSeg{i}')
    fobj.location = (math.cos(a) * FENCE_R, math.sin(a) * FENCE_R, 0)
    fobj.rotation_euler = (0, 0, a + math.pi / 2)
    fobj.parent = fence_parent
print(f'[fence] {n_seg} segments')

# облака (движок дрейфует Cloud1..4)
CLOUDS = [((-9.0, 5.5), 11.0, 1.0, 0), ((6.5, -12.5), 13.5, 1.3, 40),
          ((13.0, 2.0), 12.0, 0.8, 200), ((-4.0, -14.0), 14.5, 1.1, 120)]
for i, (xz, h, sc, rd) in enumerate(CLOUDS):
    cobj = cloud if i == 0 else linked_copy(cloud, f'Cloud{i + 1}')
    cobj.location = (xz[0], xz[1], h)
    cobj.rotation_euler = (0, 0, math.radians(rd))
    cobj.scale = (sc, sc, sc)

# источник травы — под островом, движок его прячет и инстансит
grass.location = (0, 0, -4)

# ------------------------------------------------------------ экспорт
for o in bpy.data.objects:
    o.select_set(True)
bpy.ops.export_scene.gltf(
    filepath=OUT,
    export_format='GLB',
    use_selection=True,
    export_apply=False,
    export_animation_mode='NONE' if 'NONE' in
        bpy.ops.export_scene.gltf.get_rna_type().properties['export_animation_mode'].enum_items
        else 'ACTIONS',
    export_skins=False,
    export_yup=True,
)
print('[export] wrote', OUT, os.path.getsize(OUT), 'bytes')

# ------------------------------------------------------------ превью
from mathutils import Euler
w = bpy.data.worlds.new('W')
scene.world = w
w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (0.85, 0.9, 0.95, 1)
sun = bpy.data.objects.new('S', bpy.data.lights.new('S', 'SUN'))
sun.data.energy = 3
sun.rotation_euler = Euler((math.radians(50), 0, math.radians(30)))
scene.collection.objects.link(sun)
cam = bpy.data.objects.new('C', bpy.data.cameras.new('C'))
scene.collection.objects.link(cam)
scene.camera = cam
scene.render.engine = 'BLENDER_EEVEE'
try:
    scene.view_settings.view_transform = 'Standard'
except Exception:
    pass
scene.render.resolution_x = 900
scene.render.resolution_y = 900

def shot(loc, look, path):
    cam.location = loc
    d = Vector(look) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

shot((0, -1, 34), (0, 0, 0), OUT_PREVIEW.replace('.png', '_top.png'))
shot((0, -22, 14), (0, 2, 0.5), OUT_PREVIEW.replace('.png', '_persp.png'))
print('[preview] done')
