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
def clean_material(obj, tex_size=2048, roughness=None):
    """Щадящий ремонт родного материала Meshy: убираем только мусор
    (эмиссив-дубль, накрученный спекуляр, ложную прозрачность). Базовый
    цвет, normal map и roughness-карта остаются оригинальными — модель
    выглядит на ~100% как в Meshy."""
    imgs = set()
    for mat in obj.data.materials:
        if not mat or not mat.use_nodes:
            continue
        nt = mat.node_tree
        pr = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if pr is None:
            continue
        ec = pr.inputs.get('Emission Color')
        if ec:
            for l in list(ec.links):
                nt.links.remove(l)
        if 'Emission Strength' in pr.inputs:
            pr.inputs['Emission Strength'].default_value = 0.0
        for nm in ('Specular IOR Level', 'Specular Tint'):
            inp = pr.inputs.get(nm)
            if inp:
                for l in list(inp.links):
                    nt.links.remove(l)
                if nm == 'Specular IOR Level':
                    inp.default_value = 0.5
        a = pr.inputs.get('Alpha')
        if a:
            for l in list(a.links):
                nt.links.remove(l)
            a.default_value = 1.0
        try:
            mat.blend_method = 'OPAQUE'
        except Exception:
            pass
        base_img = None
        bc = pr.inputs.get('Base Color')
        node = bc.links[0].from_node if (bc and bc.links) else None
        for _ in range(4):
            if node is None:
                break
            if node.type == 'TEX_IMAGE':
                base_img = node.image
                break
            node = (node.inputs[0].links[0].from_node
                    if node.inputs and node.inputs[0].links else None)
        for n in nt.nodes:
            if n.type == 'TEX_IMAGE' and n.image is not None:
                imgs.add((n.image, n.image is base_img))
    for img, is_base in imgs:
        cap = tex_size if is_base else min(tex_size, 1024)
        if max(img.size) > cap:
            img.scale(cap, cap)


def _apply_mod(obj, mod):
    dg = bpy.context.evaluated_depsgraph_get()
    newmesh = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    obj.modifiers.remove(mod)
    old = obj.data
    obj.data = newmesh
    if old.users == 0:
        bpy.data.meshes.remove(old)


def decimate(obj, target_polys, planar=False):
    n = len(obj.data.polygons)
    if n <= target_polys:
        return
    if planar:
        # плоские плиты: DISSOLVE (коллапс рвёт в дыры), затем ОБЯЗАТЕЛЬНО
        # триангуляция (коллапс по н-гонам снова дырявит), затем коллапс
        mod = obj.modifiers.new('dec', 'DECIMATE')
        mod.decimate_type = 'DISSOLVE'
        mod.angle_limit = math.radians(15)
        _apply_mod(obj, mod)
        tri = obj.modifiers.new('tri', 'TRIANGULATE')
        _apply_mod(obj, tri)
    n2 = len(obj.data.polygons)
    if n2 > target_polys and not planar:  # коллапс дырявит плоские плиты
        mod = obj.modifiers.new('dec', 'DECIMATE')
        mod.ratio = target_polys / n2
        _apply_mod(obj, mod)
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


def load_asset(fname, name, height=None, width=None, polys=8000, tex=1024,
               planar=False):
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
    decimate(keep, polys, planar=planar)
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


def merged_from(src_obj, name, transforms):
    """Один меш из множества размещений src_obj (matrix-список).
    Сотни маленьких объектов = сотни draw calls; слитый меш = один."""
    import bmesh
    bm = bmesh.new()
    for M in transforms:
        tmp = src_obj.data.copy()
        tmp.transform(M)
        bm.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mat in src_obj.data.materials:
        me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    scene.collection.objects.link(obj)
    print(f'[merge] {name}: {len(transforms)} placements, '
          f'{len(me.polygons)} polys, 1 draw call')
    return obj


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
    'house': 'house.glb',
    'fence': 'fence.glb',
    'slide': 'slide.glb',
    'swing': 'swings.glb',
    'sandbox': 'sandbox.glb',
    'bench': 'bench.glb',
    'tree': 'tree_new.glb',
    'bush': 'bush.glb',
    'grass': 'grass_tuft.glb',
    'daisy': 'daisies.glb',
    'cloud': 'cloud.glb',
    'ball': 'ball_soccer.glb',
    'blocks': 'blocks_abc.glb',
    'chalk': 'chalk_sticks.glb',
    'gate': 'gate.glb',
    'pave': 'pave_tile.glb',
    'fountain': 'fountain.glb',
}

# бюджеты подняты: видимой потери качества быть не должно
house = load_asset(F['house'], 'House', height=5.6, polys=60000, tex=2048)
fence = load_asset(F['fence'], 'FenceSeg', width=2.3, polys=1200, tex=512)
slide = load_asset(F['slide'], 'Slide', height=2.3, polys=20000)
swing = load_asset(F['swing'], 'Swing', height=2.4, polys=20000)
sandbox = load_asset(F['sandbox'], 'Sandbox', width=3.0, polys=18000)
bench = load_asset(F['bench'], 'Bench', width=1.9, polys=12000)
tree = load_asset(F['tree'], 'Tree', height=4.3, polys=30000)
bush = load_asset(F['bush'], 'Bush0', width=1.6, polys=12000, tex=512)
grass = load_asset(F['grass'], 'GrassTuft', height=0.26, polys=220, tex=512)
daisy = load_asset(F['daisy'], 'Daisy0', height=0.55, polys=9000, tex=512)
cloud = load_asset(F['cloud'], 'Cloud1', width=4.5, polys=5000, tex=256)
ball = load_asset(F['ball'], 'Ball', height=0.55, polys=6000, tex=512)
fountain = load_asset(F['fountain'], 'Fountain', height=1.8, polys=22000, tex=1024)
blocks = load_asset(F['blocks'], 'Blocks', width=1.1, polys=9000, tex=1024)
chalk = load_asset(F['chalk'], 'Chalk', width=0.55, polys=16000, tex=512)
gate = load_asset(F['gate'], 'Gate', width=4.7, polys=10000, tex=1024)
# Плитка: меш Meshy не переживает никакую дециматизацию (двойная
# оболочка рвётся в дыры). Решение: простой слэб со скруглённой фаской,
# на который ЗАПЕКАЕТСЯ оригинальная текстура плитки.
def make_baked_tile():
    pre = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(SRC_DIR, F['pave']))
    new = [o for o in bpy.data.objects if o not in pre]
    src = max((o for o in new if o.type == 'MESH'),
              key=lambda o: len(o.data.vertices))
    for o in new:
        if o is not src:
            bpy.data.objects.remove(o, do_unlink=True)
    clean_material(src, tex_size=512)
    normalize(src, width=0.98)

    W, H = 0.98, 0.12
    me = bpy.data.meshes.new('PaveTile')
    hw = W / 2
    vs = [(-hw, -hw, 0), (hw, -hw, 0), (hw, hw, 0), (-hw, hw, 0),
          (-hw, -hw, H), (hw, -hw, H), (hw, hw, H), (-hw, hw, H)]
    fs = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2),
          (2, 6, 7, 3), (3, 7, 4, 0)]
    me.from_pydata(vs, [], fs)
    me.validate()
    slab = bpy.data.objects.new('PaveTile', me)
    scene.collection.objects.link(slab)
    bev = slab.modifiers.new('b', 'BEVEL')
    bev.width = 0.035
    bev.segments = 2
    _apply_mod(slab, bev)
    # простые box-UV вручную (ops в headless ненадёжны)
    uv = slab.data.uv_layers.new(name='UVMap')
    for poly in slab.data.polygons:
        n = poly.normal
        ax = 2 if abs(n.z) >= max(abs(n.x), abs(n.y)) else (0 if abs(n.x) > abs(n.y) else 1)
        for li in poly.loop_indices:
            co = slab.data.vertices[slab.data.loops[li].vertex_index].co
            if ax == 2:
                u, v = co.x / W + 0.5, co.y / W + 0.5
            elif ax == 0:
                u, v = co.y / W + 0.5, co.z / H
            else:
                u, v = co.x / W + 0.5, co.z / H
            uv.data[li].uv = (u, v)
    img = bpy.data.images.new('PaveBaked', 512, 512)
    mat = bpy.data.materials.new('PaveTileMat')
    mat.use_nodes = True
    prn = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    prn.inputs['Roughness'].default_value = 0.9
    texn = mat.node_tree.nodes.new('ShaderNodeTexImage')
    texn.image = img
    mat.node_tree.links.new(texn.outputs['Color'], prn.inputs['Base Color'])
    mat.node_tree.nodes.active = texn
    slab.data.materials.append(mat)

    prev_engine = scene.render.engine
    try:
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = 8
        scene.cycles.device = 'CPU'
        for o in bpy.data.objects:
            o.select_set(o in (src, slab))
        bpy.context.view_layer.objects.active = slab
        bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'},
                            use_selected_to_active=True,
                            cage_extrusion=0.1)
        print('[pave] baked original texture onto slab')
    except Exception as e:
        print('[pave] bake failed, flat colour fallback:', e)
        prn.inputs['Base Color'].default_value = (0.62, 0.6, 0.57, 1)
    finally:
        scene.render.engine = prev_engine
    bpy.data.objects.remove(src, do_unlink=True)
    # плющим и топим в газон
    slab.data.transform(Matrix.Scale(0.07 / H, 4, Vector((0, 0, 1))))
    slab.data.transform(Matrix.Translation((0, 0, -0.018)))
    print(f'[pave] slab polys: {len(slab.data.polygons)}')
    return slab

pave = make_baked_tile()

# ------------------------------------------------------- двор: композиция
# Дом СПРАВА, крыльцом на запад (в сторону двора и улицы).
place(house, b(10.2, -3.0), rot_deg=-82)

# площадка на севере
place(slide, b(-3.0, -11.6), rot_deg=15)
place(swing, b(4.4, -12.6), rot_deg=4)
place(sandbox, b(7.4, -9.4), rot_deg=-12)
place(bench, b(6.2, 8.6), rot_deg=-115)
place(fountain, b(-5.5, 9.6), rot_deg=15)

# интерактив по всей территории
place(ball, b(8.6, 5.4), rot_deg=20)           # юго-восток
place(blocks, b(-9.4, -2.0), rot_deg=25)       # запад
place(chalk, b(-5.6, 3.4), rot_deg=-40)        # у дорожки, юго-запад
place(gate, b(-15.8, 2.28), rot_deg=-90)       # калитка перекрывает проём

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
              ((0.6, 13.8), 260, 0.8), ((12.4, 4.8), 120, 0.75)]
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
SEG = 2.28
n_side = int(math.ceil(2 * YARD / SEG))
fence_tf = []

def fence_at(x_b, y_b, rot_z):
    fence_tf.append(Matrix.Translation((x_b, y_b, 0))
                    @ Matrix.Rotation(rot_z, 4, 'Z'))

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
merged_from(fence, 'FenceRing', fence_tf)
bpy.data.objects.remove(fence, do_unlink=True)

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

# Все плитки живут на ОДНОЙ сетке (шаг P, начало 0.87): пересечения
# дорожек делят общие клетки — стыки всегда ровные.
P = TILE + GAP
G0 = 0.87

def cell(k):
    return G0 + k * P

cells = set()
def add_run(ks_x, ks_z):
    for kx in ks_x:
        for kz in ks_z:
            cells.add((kx, kz))

# главная: от ворот до восточного края дома (ряды z k=0,1)
add_run(range(-16, 14), (0, 1))
# ветка на площадку (колонки x k=0,1)
add_run((0, 1), range(-13, 0))
# кольцо вокруг дома: восток (k=13), север (z k=-7), запад-крыльцо (k=5)
add_run((13,), range(-7, 0))
add_run(range(5, 14), (-7,))
add_run((5,), range(-7, 0))
# южные ветки: к фонтану и к лавке
add_run((-6,), range(2, 9))
add_run((5,), range(2, 7))

path_tf = []
for (kx, kz) in sorted(cells):
    cx, cz = cell(kx), cell(kz)
    if abs(cx) > YARD - 0.1 or abs(cz) > YARD - 0.1:
        continue
    sc = 1.0 + random.uniform(-0.02, 0.02)
    path_tf.append(
        Matrix.Translation((cx, -cz, 0.0))
        @ Matrix.Rotation(math.radians(random.choice([0, 90, 180, 270])), 4, 'Z')
        @ Matrix.Diagonal((sc, sc, 1.0, 1.0)))
merged_from(pave, 'Path', path_tf)

# ------------------------------------- улица слева: тротуар/бордюр/дорога
side_tf = []
for i in range(int(64 / (TILE + GAP))):
    t = -32 + i * (TILE + GAP)
    for lane in (-17.15, -18.15):
        side_tf.append(
            Matrix.Translation((lane, t, 0.0))
            @ Matrix.Rotation(math.radians(random.choice([0, 90, 180, 270])), 4, 'Z'))
merged_from(pave, 'Sidewalk', side_tf)
bpy.data.objects.remove(pave, do_unlink=True)
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
    export_image_format='JPEG',  # без альфы; режет вес файла в разы
    export_jpeg_quality=82,
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
