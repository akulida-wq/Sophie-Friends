"""Двор дома + улица слева (v2.2) из ассетов Meshy ("3d meshed elements").

Выход: public/assets/environment2.glb
 - квадратный огороженный двор ~32x32; ворота на ЗАПАД к улице;
 - улица СЛЕВА (видна в кадре): тротуар из плит, бордюр, дорога с жёлтой
   пунктирной разметкой и белыми краевыми линиями, дома соседей фасадами
   к дороге, деревья;
 - дом справа (восток), крыльцом на запад во двор; дорожка от ворот к
   дому + ветка на площадку;
 - игровые элементы раскиданы по двору; качество моделей повышено;
 - Cloud1..4 дрейфуют, GrassTuft — источник инстансированной травы.

Запуск:
  /Applications/Blender.app/Contents/MacOS/Blender --background \
      --python tools/blender/build_environment2.py
"""

import math
import os
import random

import bpy
from mathutils import Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DIR = os.path.join(ROOT, '3d meshed elements')
OLD_ENV = os.path.join(ROOT, 'public', 'assets', 'environment.glb')
OUT = os.path.join(ROOT, 'public', 'assets', 'environment2.glb')
OUT_PREVIEW = os.path.join(ROOT, 'tools', 'blender', 'preview_env2.png')

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
random.seed(7)

YARD = 15.8
GATE_Z = (0.0, 3.0)   # проём ворот на западной стороне (three-z диапазон)

def b(x_three, z_three):
    return (x_three, -z_three)

# ------------------------------------------------------------ helpers
def clean_material(obj, tex_size=1024, roughness=0.8):
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
    if old.users == 0:
        bpy.data.meshes.remove(old)
    print(f'[dec] {obj.name}: {n} -> {len(obj.data.polygons)}')


def normalize(obj, height=None, width=None):
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


def load_asset(fname, name, height=None, width=None, polys=8000, tex=1024):
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
    obj.rotation_mode = 'XYZ'  # glTF-импорт даёт QUATERNION: euler игнорится
    obj.location = (xz[0], xz[1], 0)
    obj.rotation_euler = (0, 0, math.radians(rot_deg))
    obj.scale = (scale, scale, scale)


def linked_copy(obj, name):
    c = obj.copy()
    c.name = name
    scene.collection.objects.link(c)
    return c


def boxes_mesh(name, boxes, colors, roughness=0.9):
    verts, faces, cols = [], [], []
    for (cx, cy, z0, w, d, h), col in zip(boxes, colors):
        i = len(verts)
        x0, x1 = cx - w / 2, cx + w / 2
        y0, y1 = cy - d / 2, cy + d / 2
        z1 = z0 + h
        verts += [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                  (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        faces += [(i, i + 1, i + 2, i + 3), (i + 4, i + 7, i + 6, i + 5),
                  (i, i + 4, i + 5, i + 1), (i + 1, i + 5, i + 6, i + 2),
                  (i + 2, i + 6, i + 7, i + 3), (i + 3, i + 7, i + 4, i)]
        cols += [col] * 8
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    attr = mesh.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    for i, c in enumerate(cols):
        attr.data[i].color = (*c, 1.0)
    mat = bpy.data.materials.new(name + 'Mat')
    mat.use_nodes = True
    pr = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    pr.inputs['Roughness'].default_value = roughness
    vc = mat.node_tree.nodes.new('ShaderNodeVertexColor')
    vc.layer_name = 'Col'
    mat.node_tree.links.new(vc.outputs['Color'], pr.inputs['Base Color'])
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    return obj

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

# бюджеты подняты: видимой потери качества быть не должно
house = load_asset(F['house'], 'House', height=5.6, polys=60000, tex=2048)
fence = load_asset(F['fence'], 'FenceSeg', width=2.3, polys=3500, tex=512)
slide = load_asset(F['slide'], 'Slide', height=2.3, polys=20000)
swing = load_asset(F['swing'], 'Swing', height=2.4, polys=20000)
sandbox = load_asset(F['sandbox'], 'Sandbox', width=3.0, polys=18000)
bench = load_asset(F['bench'], 'Bench', width=1.9, polys=12000)
tree = load_asset(F['tree'], 'Tree', height=4.3, polys=30000)
bush = load_asset(F['bush'], 'Bush0', width=1.6, polys=12000, tex=512)
grass = load_asset(F['grass'], 'GrassTuft', height=0.26, polys=450, tex=512)
daisy = load_asset(F['daisy'], 'Daisy0', height=0.55, polys=9000, tex=512)
cloud = load_asset(F['cloud'], 'Cloud1', width=4.5, polys=5000, tex=256)
ball = load_asset(F['ball'], 'Ball', height=0.55, polys=6000, tex=512)

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
        kept_old.extend(node.children_recursive)
keep_set = set(kept_old)
for o in new:
    if o not in keep_set:
        bpy.data.objects.remove(o, do_unlink=True)
blocks = bpy.data.objects.get('Blocks')
chalk = bpy.data.objects.get('Chalk')

# ------------------------------------------------------- двор: композиция
# Дом СПРАВА, крыльцом на запад (в сторону двора и улицы).
place(house, b(10.2, -3.0), rot_deg=-82)

# площадка на севере
place(slide, b(-3.0, -11.6), rot_deg=15)
place(swing, b(4.4, -12.6), rot_deg=4)
place(sandbox, b(7.4, -9.4), rot_deg=-12)
place(bench, b(6.2, 8.6), rot_deg=-115)

# интерактив по всей территории
place(ball, b(8.6, 5.4), rot_deg=20)          # юго-восток
if blocks:
    blocks.location = (*b(-9.4, -2.0), 0)      # запад
if chalk:
    chalk.location = (*b(-5.6, 3.4), 0)        # у дорожки, юго-запад

place(tree, b(-8.6, -6.4), rot_deg=30)         # интерактивное дерево, СЗ
t1 = linked_copy(tree, 'TreeDeco1')
place(t1, b(-13.6, -13.4), rot_deg=140, scale=0.92)
t2 = linked_copy(tree, 'TreeDeco2')
place(t2, b(13.5, -13.6), rot_deg=260, scale=1.08)
t3 = linked_copy(tree, 'TreeDeco3')
place(t3, b(-12.6, 11.8), rot_deg=80, scale=0.85)

bushes_parent = bpy.data.objects.new('Bushes', None)
scene.collection.objects.link(bushes_parent)
BUSH_SPOTS = [((-6.2, -13.9), 0, 1.0), ((13.9, -7.2), 70, 0.85),
              ((-14.3, -2.0), 30, 0.9), ((10.4, 13.6), 160, 0.8),
              ((14.2, 9.0), 200, 0.9), ((-8.8, 13.9), 300, 0.85),
              ((0.6, 13.8), 260, 0.8), ((13.8, 1.4), 120, 0.75)]
for i, (xz, rd, sc) in enumerate(BUSH_SPOTS):
    bobj = bush if i == 0 else linked_copy(bush, f'Bush{i}')
    place(bobj, b(*xz), rot_deg=rd, scale=sc)
    bobj.parent = bushes_parent

DAISY_SPOTS = [((4.0, -4.2), 15, 1.0), ((-11.8, -9.2), 120, 0.85),
               ((5.6, -11.8), 230, 0.9), ((-12.0, 5.4), 60, 0.8),
               ((11.8, -11.2), 310, 0.75), ((-3.6, 11.4), 200, 0.9),
               ((12.4, 5.2), 40, 0.8), ((-9.0, 8.0), 150, 0.85)]
for i, (xz, rd, sc) in enumerate(DAISY_SPOTS):
    dobj = daisy if i == 0 else linked_copy(daisy, f'Daisy{i}')
    place(dobj, b(*xz), rot_deg=rd, scale=sc)

# --------------------------------------------------- забор по периметру
fence_parent = bpy.data.objects.new('FenceRing', None)
scene.collection.objects.link(fence_parent)
SEG = 2.28
n_side = int(math.ceil(2 * YARD / SEG))
idx = 0

def fence_at(x_b, y_b, rot_z):
    global idx
    fobj = fence if idx == 0 else linked_copy(fence, f'FenceSeg{idx}')
    fobj.rotation_mode = 'XYZ'
    fobj.location = (x_b, y_b, 0)
    fobj.rotation_euler = (0, 0, rot_z)
    fobj.parent = fence_parent
    idx += 1

for i in range(n_side):
    x = -YARD + SEG / 2 + i * SEG
    fence_at(x, -YARD, 0)                            # юг
    fence_at(x, YARD, math.pi)                       # север
for i in range(n_side):
    y = -YARD + SEG / 2 + i * SEG
    # запад: проём ворот к улице (three z 0..3 -> y_b -3..0)
    if not (-GATE_Z[1] - SEG / 2 < y < -GATE_Z[0] + SEG / 2):
        fence_at(-YARD, y, -math.pi / 2)
    fence_at(YARD, y, math.pi / 2)                   # восток
print(f'[fence] {idx} segments')

# --------------------------------------------------- дорожка из плиток
TILE = 0.92
GAP = 0.14
def path_tiles(boxes, cols, x0, z0, x1, z1):
    horizontal = abs(x1 - x0) > abs(z1 - z0)
    length = abs((x1 - x0) if horizontal else (z1 - z0))
    n = int(length / (TILE + GAP)) + 1
    for i in range(n):
        t = i * (TILE + GAP)
        for lane in (-0.55, 0.55):
            if horizontal:
                cx = min(x0, x1) + t
                cz = z0 + lane
            else:
                cx = x0 + lane
                cz = min(z0, z1) + t
            shade = 0.56 + random.uniform(-0.05, 0.05)
            warm = random.uniform(0, 0.03)
            boxes.append((cx, -cz, 0.02, TILE, TILE, 0.055))
            cols.append((shade + warm, shade, shade - warm * 0.5))

pt_boxes, pt_cols = [], []
path_tiles(pt_boxes, pt_cols, -15.8, 1.4, 7.2, 1.4)   # ворота(запад) -> дом
path_tiles(pt_boxes, pt_cols, 1.4, 0.6, 1.4, -13.2)   # ветка на площадку
boxes_mesh('Path', pt_boxes, pt_cols)

# ------------------------------------- улица слева: тротуар/бордюр/дорога
side_boxes, side_cols = [], []
for i in range(int(64 / (TILE + GAP))):
    t = -32 + i * (TILE + GAP)
    for lane in (-17.15, -18.15):
        shade = 0.6 + random.uniform(-0.04, 0.04)
        side_boxes.append((lane, t, 0.015, TILE, TILE, 0.05))
        side_cols.append((shade, shade, shade - 0.02))
boxes_mesh('Sidewalk', side_boxes, side_cols)
boxes_mesh('Curb', [(-18.9, 0, 0.0, 0.45, 64, 0.15)], [(0.63, 0.63, 0.6)])
road_boxes = [(-21.6, 0, -0.015, 4.6, 64, 0.05)]
road_cols = [(0.33, 0.34, 0.36)]
# жёлтый пунктир по центру + белые краевые линии
dash_boxes, dash_cols = [], []
for i in range(16):
    dash_boxes.append((-21.6, -30 + i * 4.0, 0.045, 0.24, 1.7, 0.012))
    dash_cols.append((0.95, 0.75, 0.15))
for edge in (-19.5, -23.7):
    dash_boxes.append((edge, 0, 0.045, 0.16, 63, 0.01))
    dash_cols.append((0.9, 0.9, 0.86))
boxes_mesh('Road', road_boxes + dash_boxes, road_cols + dash_cols)

# дома соседей за дорогой, фасадами на восток (к дороге и нам)
n1 = linked_copy(house, 'NeighborHouse1')
place(n1, b(-28.5, -12.0), rot_deg=95, scale=0.92)
n2 = linked_copy(house, 'NeighborHouse2')
place(n2, b(-29.0, 2.0), rot_deg=82, scale=1.02)
n3 = linked_copy(house, 'NeighborHouse3')
place(n3, b(-27.5, 14.5), rot_deg=100, scale=0.85)
for j, (xz, rd, sc) in enumerate([((-26.0, -20.0), 40, 1.0),
                                  ((-25.5, -5.0), 200, 0.9),
                                  ((-26.5, 8.5), 90, 1.05),
                                  ((-25.0, 20.0), 10, 0.95),
                                  ((8.0, -20.0), 180, 1.0),
                                  ((22.0, -12.0), 300, 1.05),
                                  ((23.0, 6.0), 60, 0.95),
                                  ((10.0, 21.0), 250, 1.0)]):
    ot = linked_copy(tree, f'OutTree{j}')
    place(ot, b(*xz), rot_deg=rd, scale=sc)
for j, (xz, rd, sc) in enumerate([((-16.9, -10.0), 0, 1.0),
                                  ((-16.8, 8.0), 120, 0.9),
                                  ((-16.9, 14.5), 70, 0.85),
                                  ((20.0, 14.0), 30, 0.9)]):
    ob = linked_copy(bush, f'OutBush{j}')
    place(ob, b(*xz), rot_deg=rd, scale=sc)

# --------------------------------------------------------------- облака
# blender y_b = -z_three: облака на СЕВЕРЕ (z_three < 0) — видны камере
# далеко на севере и крупно: в игровой камере видна лишь полоса у
# горизонта — облака живут именно там, над крышами соседей
CLOUDS = [((-20.0, 58.0), 1.5, 2.2, 0), ((8.0, 62.0), 2.5, 2.8, 40),
          ((28.0, 60.0), 2.0, 2.4, 200), ((-5.0, 66.0), 3.0, 3.0, 120)]
for i, (xz, h, sc, rd) in enumerate(CLOUDS):
    cobj = cloud if i == 0 else linked_copy(cloud, f'Cloud{i + 1}')
    cobj.rotation_mode = 'XYZ'
    cobj.location = (xz[0], xz[1], h)
    cobj.rotation_euler = (0, 0, math.radians(rd))
    cobj.scale = (sc, sc, sc)

grass.location = (0, 0, -4)

# ------------------------------------------------------------ экспорт
for o in bpy.data.objects:
    o.select_set(True)
bpy.ops.export_scene.gltf(
    filepath=OUT,
    export_format='GLB',
    use_selection=True,
    export_apply=False,
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
scene.render.resolution_x = 950
scene.render.resolution_y = 950

def shot(loc, look, path_):
    cam.location = loc
    d = Vector(look) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = path_
    bpy.ops.render.render(write_still=True)

shot((-4, -6, 56), (-4, 0, 0), OUT_PREVIEW.replace('.png', '_top.png'))
shot((4, -34, 20), (-4, 4, 0.5), OUT_PREVIEW.replace('.png', '_persp.png'))
print('[preview] done')
