"""Bruno для Sophie & Friends — модель + риг + 9 клипов. Blender 5.x.

ДЛЯ ПРОСМОТРА В ОТКРЫТОМ BLENDER (твой режим):
  Вкладка Scripting -> Text -> Open -> этот файл -> Run Script (▶).
  Скрипт НЕ трогает остальную сцену: всё строится в коллекцию "Bruno",
  при повторном запуске старый Бруно удаляется и собирается заново —
  правь числа и жми Run снова.
  Анимации: выбери Bruno_Rig -> редактор NLA -> solo (звёздочка) на треке
  (IdleSad, Walk, SmallWave, ...) -> пробел = play.

ЭКСПОРТ (headless, запускается отдельно):
  /Applications/Blender.app/Contents/MacOS/Blender --background --python tools/blender/build_bruno.py
  -> public/assets/bruno.glb + tools/blender/preview_bruno.png

ГДЕ ЧТО КРУТИТЬ:
  COL        — все цвета (sRGB 0-255)
  ELS        — силуэт тела (metaball: центры и радиусы, поверхность ~0.75*r)
  Секция "детали" — глаз/уши/кепка/веснушки/рот/клык/руки/кеды;
                    всё лицевое садится на поверхность рейкастом (surf_y).

Референс: высокий светло-голубой блоб, голова = половина роста, одно
огромное око с бликами, кремовые веснушки, широкая мягкая улыбка с одним
клыком, острые уши-рожки, розовая кепка набекрень, длиннющие висячие руки,
зелёные кеды с белым носком/подошвой/полосками. Морда в +Y.
"""

import math
import os
import struct
import json as jsonlib

import bmesh
import bpy
from mathutils import Vector, noise

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_GLB = os.path.join(ROOT, 'public', 'assets', 'bruno.glb')
OUT_PREVIEW = os.path.join(ROOT, 'tools', 'blender', 'preview_bruno.png')
HEADLESS = bpy.app.background

CLIP_NAMES = ['IdleSad', 'IdleOpen', 'Walk', 'HandToChest', 'SmallWave',
              'SitAlone', 'TryJoinClumsy', 'TryAgainSucceed', 'PlayIncluded']

# Гибрид: кепка и кеды вырезаются из Tripo-модели (текстурные, детальные),
# остальное — процедурное. Если файла нет, всё строится процедурно.
TRIPO_SRC = os.path.join(ROOT, 'public', 'assets', 'bruno_tripo.glb')
HYBRID = os.path.isfile(TRIPO_SRC)


def srgb(r, g, b):
    return tuple((c / 255.0) ** 2.2 for c in (r, g, b)) + (1.0,)


COL = {
    'body': srgb(118, 182, 228),
    'freckle': srgb(246, 233, 183),
    'cap': srgb(228, 138, 190),
    'cap_dark': srgb(202, 108, 162),
    'shoe': srgb(58, 148, 82),
    'shoe_trim': srgb(242, 246, 242),
    'eye': srgb(245, 245, 241),
    'pupil': srgb(28, 32, 42),
    'highlight': srgb(255, 255, 255),
    'mouth': srgb(36, 46, 70),
    'fang': srgb(248, 246, 238),
}

# Силуэт: широченная голова (половина роста), сужение вниз, и НОГИ КАК
# ПРОДОЛЖЕНИЕ ТЕЛА — две колонны metaball-элементов, корпус плавно
# раздваивается (как на арте), без отдельных "палок".
ELS = [((0, 0, 1.85), 0.88),
       ((0, 0, 1.45), 0.75),
       ((0, 0, 1.05), 0.58),
       ((0, 0, 0.85), 0.52)]
for _sx in (1, -1):
    ELS += [((_sx * 0.16, 0.00, 0.58), 0.24),
            ((_sx * 0.175, 0.00, 0.40), 0.20),
            ((_sx * 0.18, 0.01, 0.26), 0.17)]

# Акварельная пятнистость (как на арте): базовый + тёмный/светлый тона.
MOTTLE_BASE = (118, 182, 228)
MOTTLE_DARK = (96, 158, 210)
MOTTLE_LIGHT = (152, 206, 240)


def mottle(obj, scale1=2.4, scale2=6.0):
    """Вершинные цвета с шумом — переживают экспорт в GLB (COLOR_0)."""
    me = obj.data
    attr = me.color_attributes.new(name='Col', type='BYTE_COLOR', domain='POINT')
    base = Vector([c / 255.0 for c in MOTTLE_BASE])
    dark = Vector([c / 255.0 for c in MOTTLE_DARK])
    light = Vector([c / 255.0 for c in MOTTLE_LIGHT])
    mw = obj.matrix_world
    for i, v in enumerate(me.vertices):
        co = mw @ v.co
        n = (noise.noise(co * scale1) * 0.65 + noise.noise(co * scale2) * 0.35)
        if n >= 0:
            col = base.lerp(light, min(1.0, n * 1.1))
        else:
            col = base.lerp(dark, min(1.0, -n * 1.3))
        # sRGB -> linear для BYTE_COLOR
        attr.data[i].color = tuple(c ** 2.2 for c in col) + (1.0,)

# ------------------------------------------------------------ подготовка
if HEADLESS:
    bpy.ops.wm.read_factory_settings(use_empty=True)

scene = bpy.context.scene
scene.render.fps = 24

# Убрать предыдущего Бруно (повторные запуски в GUI).
old = bpy.data.collections.get('Bruno')
if old:
    for o in list(old.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(old)
for act in list(bpy.data.actions):
    if act.name.startswith('BR_'):
        bpy.data.actions.remove(act)
for blocks in (bpy.data.meshes, bpy.data.materials, bpy.data.metaballs,
               bpy.data.armatures):
    for db in list(blocks):
        if db.users == 0 and (db.name.startswith('Bruno') or
                              db.name.startswith('BR_')):
            blocks.remove(db)

bruno_col = bpy.data.collections.new('Bruno')
scene.collection.children.link(bruno_col)


def _find_layer(lc, col):
    if lc.collection == col:
        return lc
    for c in lc.children:
        r = _find_layer(c, col)
        if r:
            return r
    return None


lc = _find_layer(bpy.context.view_layer.layer_collection, bruno_col)
if lc:
    bpy.context.view_layer.active_layer_collection = lc

_mats = {}


def mat(key, roughness=0.9):
    if key not in _mats:
        m = bpy.data.materials.new(f'Bruno_{key}')
        m.use_nodes = True
        bsdf = m.node_tree.nodes['Principled BSDF']
        bsdf.inputs['Base Color'].default_value = COL[key]
        bsdf.inputs['Roughness'].default_value = roughness
        if key == 'body':
            # Акварельная пятнистость через вершинные цвета (COLOR_0 в GLB).
            vc = m.node_tree.nodes.new('ShaderNodeVertexColor')
            vc.layer_name = 'Col'
            m.node_tree.links.new(vc.outputs['Color'], bsdf.inputs['Base Color'])
        _mats[key] = m
    return _mats[key]


def smooth(obj):
    for p in obj.data.polygons:
        p.use_smooth = True


def sphere(name, r, loc, scale=(1, 1, 1), key='body', rot=(0, 0, 0), seg=32):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, rotation=rot,
                                         segments=seg, ring_count=seg // 2)
    o = bpy.context.active_object
    o.name = f'BR_{name}'
    o.scale = scale
    o.data.materials.append(mat(key))
    smooth(o)
    return o


def rbox(name, size, loc, key, rot=(0, 0, 0), bevel=0.03):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = f'BR_{name}'
    o.scale = size
    o.data.materials.append(mat(key))
    b = o.modifiers.new('Bevel', 'BEVEL')
    b.width = 0.25
    b.segments = 3
    smooth(o)
    return o


parts = []

# ------------------------------------------------------- тело-голова (блоб)
bpy.ops.object.metaball_add(type='BALL', location=(0, 0, 0))
mball = bpy.context.active_object
mball.data.resolution = 0.042
e0 = mball.data.elements[0]
e0.co, e0.radius = ELS[0]
for co, r in ELS[1:]:
    e = mball.data.elements.new()
    e.co = co
    e.radius = r
bpy.ops.object.convert(target='MESH')
blob = bpy.context.active_object
blob.name = 'BR_Body'
blob.data.materials.append(mat('body'))
sm = blob.modifiers.new('Smooth', 'SMOOTH')
sm.factor = 1.0
sm.iterations = 6
smooth(blob)
mottle(blob)


def surf_y(x, z):
    hit, loc, _n, _i = blob.ray_cast((x, 4.0, z), (0, -1, 0))
    return loc.y if hit else 0.5


def surf_x(z, y=0.0):
    hit, loc, _n, _i = blob.ray_cast((4.0, y, z), (-1, 0, 0))
    return loc.x if hit else 0.55


def top_z():
    hit, loc, _n, _i = blob.ray_cast((0, 0, 5.0), (0, 0, -1))
    return loc.z if hit else 2.45


Z_TOP = top_z()

# ------------------------------------------ Tripo-детали (кепка + кеды)
tripo_parts = {}
if HYBRID:
    from mathutils import Matrix as _M
    _before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=TRIPO_SRC)
    _imp = [o for o in bpy.data.objects if o not in _before]
    _tripo = max((o for o in _imp if o.type == 'MESH'),
                 key=lambda o: len(o.data.vertices))
    for o in _imp:
        if o is not _tripo:
            bpy.data.objects.remove(o, do_unlink=True)
    _mw = _tripo.matrix_world.copy()
    _tripo.parent = None
    _tripo.data.transform(_M.Rotation(math.pi, 4, 'Z') @ _mw)
    _tripo.matrix_world = _M.Identity(4)
    _th = max(v.co.z for v in _tripo.data.vertices)

    # Классификация вершин по цвету текстуры (кепка розовая, тело голубое).
    _img = None
    for _m in _tripo.data.materials:
        if _m and _m.use_nodes:
            for _n in _m.node_tree.nodes:
                if _n.type == 'TEX_IMAGE' and _n.image:
                    _img = _n.image
                    break
    _vert_rgb = {}
    if _img:
        _uvl = _tripo.data.uv_layers.active
        _w, _h = _img.size
        _px = _img.pixels[:]
        for _poly in _tripo.data.polygons:
            for _li in _poly.loop_indices:
                _vi = _tripo.data.loops[_li].vertex_index
                if _vi in _vert_rgb:
                    continue
                _uv = _uvl.data[_li].uv
                _x = int(_uv.x * _w) % _w
                _y = int(_uv.y * _h) % _h
                _i = 4 * (_y * _w + _x)
                _vert_rgb[_vi] = (_px[_i], _px[_i + 1], _px[_i + 2])

    def _is_pink(vi):
        r, g, b = _vert_rgb.get(vi, (0, 0, 1))
        return r > 0.25 and r > g * 1.25 and b > g * 0.7

    def _extract(cond, name):
        o = _tripo.copy()
        o.data = _tripo.data.copy()
        bruno_col.objects.link(o)
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bm.verts.ensure_lookup_table()
        doomed = [v for v in bm.verts if not cond(v.index, v.co)]
        bmesh.ops.delete(bm, geom=doomed, context='VERTS')
        bm.to_mesh(o.data)
        bm.free()
        o.name = f'BR_{name}'
        smooth(o)
        return o

    def _fit(o, scale, loc, rot=(0, 0, 0)):
        o.scale = (scale, scale, scale)
        o.rotation_euler = rot
        o.location = loc

    CAP_CUT = 0.868 * _th
    SHOE_CUT = 0.14 * _th
    # кепка: без ушей (|x|) и без макушки головы под куполом (радиус)
    cap_t = _extract(lambda vi, c: c.z > CAP_CUT and _is_pink(vi), 'CapT')
    shoeL_t = _extract(lambda vi, c: c.z < SHOE_CUT and c.x >= 0, 'ShoeT.L')
    shoeR_t = _extract(lambda vi, c: c.z < SHOE_CUT and c.x < 0, 'ShoeT.R')

    def _bbox(o):
        xs = [v.co.x for v in o.data.vertices]
        ys = [v.co.y for v in o.data.vertices]
        zs = [v.co.z for v in o.data.vertices]
        return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))

    (cx0, cx1), (cy0, cy1), (cz0, cz1) = _bbox(cap_t)
    cap_scale = 0.95 / max(cx1 - cx0, 1e-4)
    _fit(cap_t, cap_scale,
         (0.05 - cap_scale * (cx0 + cx1) / 2,
          -cap_scale * (cy0 + cy1) / 2,
          Z_TOP - 0.22 - cap_scale * cz0),
         rot=(-0.05, 0.16, 0))

    for st, sx in ((shoeL_t, 1), (shoeR_t, -1)):
        (bx0, bx1), (by0, by1), (bz0, bz1) = _bbox(st)
        s = 0.50 / max(by1 - by0, 1e-4)
        _fit(st, s,
             (sx * 0.18 - s * (bx0 + bx1) / 2,
              0.08 - s * (by0 + by1) / 2,
              0.005 - s * bz0))
    tripo_parts = {'cap': cap_t, 'shoeL': shoeL_t, 'shoeR': shoeR_t}
    bpy.data.objects.remove(_tripo, do_unlink=True)
    print('[hybrid] Tripo cap+shoes extracted')

# ------------------------------------------------------------------ детали
# Острые уши-рожки: торчат вбок-вверх из-под краёв кепки, заметные.
for side, sx in (('L', 1), ('R', -1)):
    bpy.ops.mesh.primitive_cone_add(radius1=0.17, radius2=0.015, depth=0.46,
                                    location=(sx * 0.42, -0.02, Z_TOP - 0.30),
                                    rotation=(0, sx * 0.85, 0), vertices=16)
    ear = bpy.context.active_object
    ear.name = f'BR_Ear.{side}'
    ear.data.materials.append(mat('body'))
    ss = ear.modifiers.new('Subsurf', 'SUBSURF')
    ss.levels = 2
    ss.render_levels = 2
    smooth(ear)
    mottle(ear)
    parts.append((ear, 'head'))

# Огромное око: белок (вертикальный овал), зрачок, два блика.
EYE_Z = 1.80
eye_y = surf_y(0, EYE_Z) - 0.10
eye = sphere('Eye', 0.26, (0, eye_y, EYE_Z), scale=(0.92, 0.55, 1.08))
eye.data.materials.clear()
eye.data.materials.append(mat('eye', roughness=0.3))
parts.append((eye, 'head'))
pupil_y = eye_y + 0.26 * 0.55 - 0.035
pupil = sphere('Pupil', 0.13, (0, pupil_y, EYE_Z - 0.01), scale=(0.95, 0.45, 1.1))
pupil.data.materials.clear()
pupil.data.materials.append(mat('pupil', roughness=0.35))
parts.append((pupil, 'head'))
for gname, gx, gz, gr in (('Gleam1', 0.055, EYE_Z + 0.07, 0.034),
                          ('Gleam2', -0.035, EYE_Z - 0.075, 0.018)):
    g = sphere(gname, gr, (gx, pupil_y + 0.05, gz), seg=12)
    g.data.materials.clear()
    g.data.materials.append(mat('highlight', roughness=0.2))
    parts.append((g, 'head'))
# Тонкое верхнее веко (цвет тела) — едва заметная полоска, как на арте.
lid = sphere('Eyelid', 1.0, (0, eye_y + 0.065, EYE_Z + 0.185),
             scale=(0.235, 0.095, 0.05), rot=(-0.25, 0, 0))
mottle(lid)
parts.append((lid, 'head'))

# Кремовые веснушки — по 5 разного размера на щёку, как на арте.
freckles = [(0.30, 1.62, 0.052), (0.40, 1.68, 0.042),
            (0.34, 1.52, 0.036), (0.44, 1.56, 0.047),
            (0.38, 1.61, 0.026)]
for i, (fx, fz, fr) in enumerate(freckles):
    for sx in (1, -1):
        fy = surf_y(sx * fx, fz) - fr * 0.35
        f = sphere(f'Freckle{i}{"LR"[sx < 0]}', fr, (sx * fx, fy, fz), seg=14)
        f.data.materials.clear()
        f.data.materials.append(mat('freckle'))
        parts.append((f, 'head'))

# Широкая мягкая улыбка — нижняя половина тонкого тора (дуга), + клык.
MOUTH_Z = 1.42
bpy.ops.mesh.primitive_torus_add(major_radius=0.19, minor_radius=0.016,
                                 location=(0, 0, 0),
                                 major_segments=32, minor_segments=8)
mouth = bpy.context.active_object
mouth.name = 'BR_Mouth'
me = mouth.data
bm = bmesh.new()
bm.from_mesh(me)
doomed = [v for v in bm.verts if v.co.y > 0.015]
bmesh.ops.delete(bm, geom=doomed, context='VERTS')
bm.to_mesh(me)
bm.free()
mouth.rotation_euler = (math.radians(90), 0, 0)
mouth.scale = (1.0, 1.0, 0.5)  # z после поворота = глубина дуги
mouth_y = surf_y(0, MOUTH_Z) - 0.012
mouth.location = (0, mouth_y, MOUTH_Z)
mouth.data.materials.append(mat('mouth'))
smooth(mouth)
parts.append((mouth, 'head'))

fang_x = 0.075
fang_y = surf_y(fang_x, MOUTH_Z - 0.05) - 0.005
bpy.ops.mesh.primitive_cone_add(radius1=0.042, radius2=0.01, depth=0.12,
                                location=(fang_x, fang_y, MOUTH_Z - 0.105),
                                rotation=(math.pi, 0, 0), vertices=12)
fang = bpy.context.active_object
fang.name = 'BR_Fang'
fang.data.materials.append(mat('fang'))
smooth(fang)
parts.append((fang, 'head'))

# Маленькая розовая кепка набекрень: купол + тёмная окантовка + пуговка
# + козырёк (как на арте). В гибриде — вырезанная из Tripo.
if HYBRID:
    parts.append((tripo_parts['cap'], 'head'))
CAP_TILT = 0.22  # наклон вправо
if not HYBRID:
    CAP_C = (0.07, 0.0, Z_TOP + 0.05)
    cap = sphere('Cap', 0.50, CAP_C, scale=(0.62, 0.62, 0.38),
                 rot=(-0.06, CAP_TILT, 0))
    cap.data.materials.clear()
    cap.data.materials.append(mat('cap'))
    parts.append((cap, 'head'))
    band = sphere('CapBand', 0.50, (CAP_C[0], CAP_C[1], CAP_C[2] - 0.075),
                  scale=(0.64, 0.64, 0.10), rot=(-0.06, CAP_TILT, 0))
    band.data.materials.clear()
    band.data.materials.append(mat('cap_dark'))
    parts.append((band, 'head'))
    button = sphere('CapButton', 0.045,
                    (CAP_C[0] + 0.04, CAP_C[1], CAP_C[2] + 0.185), seg=14)
    button.data.materials.clear()
    button.data.materials.append(mat('cap_dark'))
    parts.append((button, 'head'))
    bpy.ops.mesh.primitive_cylinder_add(radius=0.15, depth=0.038,
                                        location=(0.11, 0.30, CAP_C[2] - 0.05),
                                        rotation=(0.12, CAP_TILT * 0.5, 0), vertices=24)
    brim = bpy.context.active_object
    brim.name = 'BR_CapBrim'
    brim.scale = (1.35, 1.0, 1.0)
    brim.data.materials.append(mat('cap'))
    smooth(brim)
    parts.append((brim, 'head'))

# Руки-«ласты» как на арте: длинные, расширяются книзу, слегка выгнуты
# наружу. Каждая — своя metaball-цепочка (строим по одной: металлболы
# одной "семьи" сливаются, пока сосуществуют).
def build_arm(side, sx):
    bpy.ops.object.metaball_add(type='BALL', location=(0, 0, 0))
    mb = bpy.context.active_object
    mb.data.resolution = 0.045
    # Плотная цепочка (шаг ~0.13), иначе поля элементов не сольются.
    # Выгнута наружу сильнее, крепится выше — как на арте.
    chain = []
    steps = 9
    for i in range(steps):
        t = i / (steps - 1)
        bow = math.sin(t * math.pi) * 0.05  # лёгкий изгиб наружу в середине
        cx = sx * (0.50 + 0.17 * t + bow)
        cy = 0.02 * t
        cz = 1.48 - 1.12 * t
        cr = 0.125 + 0.065 * t
        chain.append(((cx, cy, cz), cr))
    el = mb.data.elements[0]
    el.co, el.radius = chain[0]
    for co, r in chain[1:]:
        e = mb.data.elements.new()
        e.co = co
        e.radius = r
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.active_object
    o.name = f'BR_Arm.{side}'
    o.data.materials.append(mat('body'))
    asm = o.modifiers.new('Smooth', 'SMOOTH')
    asm.factor = 1.0
    asm.iterations = 5
    smooth(o)
    mottle(o)
    return o


for side, sx in (('L', 1), ('R', -1)):
    parts.append((build_arm(side, sx), f'arm.{side}'))

# Кеды побольше с белыми деталями (ноги — уже часть тела-блоба).
for side, sx in (('L', 1), ('R', -1)):
    shoe = rbox(f'Shoe.{side}', (0.18, 0.34, 0.12), (sx * 0.17, 0.06, 0.115),
                'shoe')
    parts.append((shoe, f'leg.{side}'))
    sole = rbox(f'Sole.{side}', (0.19, 0.36, 0.042), (sx * 0.17, 0.06, 0.032),
                'shoe_trim')
    parts.append((sole, f'leg.{side}'))
    toe = sphere(f'Toe.{side}', 1.0, (sx * 0.17, 0.245, 0.11),
                 scale=(0.14, 0.11, 0.09))
    toe.data.materials.clear()
    toe.data.materials.append(mat('shoe_trim'))
    parts.append((toe, f'leg.{side}'))
    for si in range(3):
        stripe = rbox(f'Stripe{si}.{side}',
                      (0.015, 0.05, 0.09),
                      (sx * (0.17 + 0.086), 0.10 - si * 0.075, 0.115),
                      'shoe_trim', rot=(0, 0, sx * 0.3))
        parts.append((stripe, f'leg.{side}'))

# --------------------------------------------------------------------- риг
bpy.ops.object.armature_add(location=(0, 0, 0))
arm_obj = bpy.context.active_object
arm_obj.name = 'Bruno_Rig'
arm_obj.data.name = 'Bruno_RigData'
bpy.ops.object.mode_set(mode='EDIT')
eb = arm_obj.data.edit_bones
eb.remove(eb[0])
BONES = {
    'root': ((0, 0, 0.05), (0, 0, 0.55), None),
    'spine': ((0, 0, 0.55), (0, 0, 1.50), 'root'),
    'head': ((0, 0, 1.50), (0, 0, Z_TOP), 'spine'),
    'arm.L': ((0.52, 0, 1.48), (0.67, 0, 0.34), 'spine'),
    'arm.R': ((-0.52, 0, 1.48), (-0.67, 0, 0.34), 'spine'),
    'leg.L': ((0.17, 0, 0.60), (0.17, 0, 0.08), 'root'),
    'leg.R': ((-0.17, 0, 0.60), (-0.17, 0, 0.08), 'root'),
}
created = {}
for name, (bhead, tail, parent) in BONES.items():
    b = eb.new(name)
    b.head = bhead
    b.tail = tail
    b.roll = 0
    if parent:
        b.parent = created[parent]
    created[name] = b
bpy.ops.object.mode_set(mode='OBJECT')

# Мягкий скиннинг блоба: верх -> head, середина -> spine, низ плавно
# расходится на leg.L / leg.R (тело переходит в ноги и они анимируются).
vg_spine = blob.vertex_groups.new(name='spine')
vg_head = blob.vertex_groups.new(name='head')
vg_legL = blob.vertex_groups.new(name='leg.L')
vg_legR = blob.vertex_groups.new(name='leg.R')
for v in blob.data.vertices:
    z = v.co.z
    x = v.co.x
    if z >= 1.30:
        t = min(1.0, (z - 1.30) / 0.45)
        if t < 1.0:
            vg_spine.add([v.index], 1.0 - t, 'REPLACE')
        if t > 0.0:
            vg_head.add([v.index], t, 'REPLACE')
    elif z >= 0.64:
        vg_spine.add([v.index], 1.0, 'REPLACE')
    else:
        t = min(1.0, (0.64 - z) / 0.20)  # 0.64 -> 0.44: полностью ноги
        side_l = max(0.0, min(1.0, (x + 0.06) / 0.12))
        if t < 1.0:
            vg_spine.add([v.index], 1.0 - t, 'REPLACE')
        if t * side_l > 0.0:
            vg_legL.add([v.index], t * side_l, 'REPLACE')
        if t * (1.0 - side_l) > 0.0:
            vg_legR.add([v.index], t * (1.0 - side_l), 'REPLACE')
m = blob.modifiers.new('Armature', 'ARMATURE')
m.object = arm_obj
blob.parent = arm_obj

for obj, bone in parts:
    vg = obj.vertex_groups.new(name=bone)
    vg.add(list(range(len(obj.data.vertices))), 1.0, 'REPLACE')
    am = obj.modifiers.new('Armature', 'ARMATURE')
    am.object = arm_obj
    obj.parent = arm_obj

for pb in arm_obj.pose.bones:
    pb.rotation_mode = 'XYZ'

# --------------------------------------------------- автодетект знаков поз
def reset_pose():
    for pb in arm_obj.pose.bones:
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)


def tail_world(bone):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    eo = arm_obj.evaluated_get(dg)
    return (eo.matrix_world @ eo.pose.bones[bone].tail).copy()


def pitch_sign(bone):
    reset_pose()
    rest_y = tail_world(bone).y
    arm_obj.pose.bones[bone].rotation_euler = (0.4, 0, 0)
    bent_y = tail_world(bone).y
    reset_pose()
    return 1.0 if bent_y > rest_y else -1.0


S_HEAD = pitch_sign('head')
S_SPINE = pitch_sign('spine')
S_ARM = pitch_sign('arm.R')
S_LEG = pitch_sign('leg.R')
print(f'[signs] head={S_HEAD} spine={S_SPINE} arm={S_ARM} leg={S_LEG}')

# ------------------------------------------------------------------- клипы
arm_obj.animation_data_create()


def kf(bone, frame, pitch=None, roll=None, loc_z=None):
    pb = arm_obj.pose.bones[bone]
    if pitch is not None or roll is not None:
        e = pb.rotation_euler
        pb.rotation_euler = (pitch if pitch is not None else e.x, 0,
                             roll if roll is not None else e.z)
        pb.keyframe_insert('rotation_euler', frame=frame)
    if loc_z is not None:
        pb.location = (0, loc_z, 0) if bone == 'root' else (0, 0, loc_z)
        pb.keyframe_insert('location', frame=frame)


def begin_clip(last):
    reset_pose()
    arm_obj.animation_data.action = None
    scene.frame_start = 1
    scene.frame_end = last


def end_clip(name):
    """Action получает префикс BR_ (чтобы не задеть экшены Софи в твоём
    файле), а NLA-трек — точное имя клипа: glTF берёт имя из трека."""
    act = arm_obj.animation_data.action
    assert act is not None, f'no action for {name}'
    act.name = f'BR_{name}'
    act.use_fake_user = True
    track = arm_obj.animation_data.nla_tracks.new()
    track.name = name
    strip = track.strips.new(name, 1, act)
    if hasattr(strip, 'action_slot') and getattr(strip, 'action_slot', None) is None:
        try:
            strip.action_slot = act.slots[0]
        except Exception:
            pass
    arm_obj.animation_data.action = None


begin_clip(72)
for f in (1, 72):
    kf('spine', f, pitch=0.16 * S_SPINE)
    kf('root', f, loc_z=-0.03)
    kf('arm.L', f, roll=-0.10)
    kf('arm.R', f, roll=0.10)
kf('head', 1, pitch=0.38 * S_HEAD)
kf('head', 36, pitch=0.44 * S_HEAD)
kf('head', 72, pitch=0.38 * S_HEAD)
kf('spine', 36, pitch=0.19 * S_SPINE)
end_clip('IdleSad')

begin_clip(72)
kf('head', 1, pitch=-0.06 * S_HEAD)
kf('head', 72, pitch=-0.06 * S_HEAD)
kf('spine', 1, pitch=-0.04 * S_SPINE, roll=0.03)
kf('spine', 36, pitch=-0.04 * S_SPINE, roll=-0.03)
kf('spine', 72, pitch=-0.04 * S_SPINE, roll=0.03)
kf('arm.L', 1, roll=0.10)
kf('arm.R', 1, roll=-0.10)
kf('arm.L', 72, roll=0.10)
kf('arm.R', 72, roll=-0.10)
end_clip('IdleOpen')

begin_clip(24)
for f, a in ((1, 0.45), (13, -0.45), (24, 0.45)):
    kf('leg.L', f, pitch=a * S_LEG)
    kf('leg.R', f, pitch=-a * S_LEG)
    kf('arm.L', f, pitch=-a * 0.35 * S_ARM)
    kf('arm.R', f, pitch=a * 0.35 * S_ARM)
for f, z in ((1, -0.015), (7, 0.02), (13, -0.015), (19, 0.02), (24, -0.015)):
    kf('root', f, loc_z=z)
kf('spine', 1, pitch=0.05 * S_SPINE)
kf('spine', 24, pitch=0.05 * S_SPINE)
end_clip('Walk')

begin_clip(48)
kf('arm.R', 1, pitch=0.0)
kf('arm.R', 16, pitch=1.15 * S_ARM, roll=0.5)
kf('arm.R', 48, pitch=1.15 * S_ARM, roll=0.5)
kf('head', 1, pitch=0.30 * S_HEAD)
kf('head', 28, pitch=0.10 * S_HEAD)
kf('head', 48, pitch=0.10 * S_HEAD)
kf('spine', 1, pitch=0.12 * S_SPINE)
kf('spine', 48, pitch=0.10 * S_SPINE)
end_clip('HandToChest')

begin_clip(48)
kf('arm.R', 1, pitch=0.0, roll=0.0)
kf('arm.R', 10, pitch=2.3 * S_ARM, roll=0.0)
for f, r in ((16, 0.28), (24, -0.28), (32, 0.28), (40, 0.0)):
    kf('arm.R', f, pitch=2.3 * S_ARM, roll=r)
kf('arm.R', 48, pitch=1.1 * S_ARM, roll=0.0)
kf('head', 1, pitch=0.05 * S_HEAD)
kf('head', 20, pitch=-0.05 * S_HEAD)
kf('head', 48, pitch=0.0)
end_clip('SmallWave')

begin_clip(60)
for f in (1, 60):
    kf('root', f, loc_z=-0.32)
    kf('leg.L', f, pitch=1.4 * S_LEG)
    kf('leg.R', f, pitch=1.4 * S_LEG)
    kf('spine', f, pitch=0.22 * S_SPINE)
kf('head', 1, pitch=0.34 * S_HEAD)
kf('head', 30, pitch=0.40 * S_HEAD)
kf('head', 60, pitch=0.34 * S_HEAD)
end_clip('SitAlone')

begin_clip(60)
kf('spine', 1, pitch=0.10 * S_SPINE, roll=0.0)
kf('spine', 16, pitch=0.22 * S_SPINE, roll=0.0)
for f, r in ((24, 0.12), (32, -0.12), (40, 0.06)):
    kf('spine', f, pitch=0.18 * S_SPINE, roll=r)
kf('root', 1, loc_z=0.0)
kf('root', 30, loc_z=-0.06)
kf('root', 46, loc_z=0.0)
kf('spine', 60, pitch=0.08 * S_SPINE, roll=0.0)
kf('head', 1, pitch=0.0)
kf('head', 30, pitch=0.15 * S_HEAD)
kf('head', 60, pitch=0.05 * S_HEAD)
end_clip('TryJoinClumsy')

begin_clip(60)
kf('spine', 1, pitch=0.15 * S_SPINE)
kf('spine', 30, pitch=0.05 * S_SPINE)
kf('spine', 60, pitch=0.02 * S_SPINE)
kf('arm.L', 1, roll=0.0)
kf('arm.R', 1, roll=0.0)
kf('arm.L', 40, roll=0.35)
kf('arm.R', 40, roll=-0.35)
kf('arm.L', 60, roll=0.30)
kf('arm.R', 60, roll=-0.30)
kf('head', 1, pitch=0.15 * S_HEAD)
kf('head', 45, pitch=-0.10 * S_HEAD)
kf('head', 60, pitch=-0.10 * S_HEAD)
end_clip('TryAgainSucceed')

begin_clip(48)
for f, z in ((1, 0.0), (12, 0.06), (24, 0.0), (36, 0.06), (48, 0.0)):
    kf('root', f, loc_z=z)
for f, a in ((1, 0.25), (24, -0.25), (48, 0.25)):
    kf('arm.L', f, pitch=a * S_ARM)
    kf('arm.R', f, pitch=-a * S_ARM)
for f, r in ((1, 0.06), (24, -0.06), (48, 0.06)):
    kf('head', f, roll=r)
kf('spine', 1, pitch=-0.03 * S_SPINE)
kf('spine', 48, pitch=-0.03 * S_SPINE)
end_clip('PlayIncluded')

reset_pose()

# ------------------------------------------------------------- верификация
rest_head_z = tail_world('head').z
act = bpy.data.actions['BR_IdleSad']
arm_obj.animation_data.action = act
scene.frame_set(36)
sad_head_z = tail_world('head').z
arm_obj.animation_data.action = None
reset_pose()
scene.frame_set(1)
print(f'[verify] head z rest={rest_head_z:.3f} IdleSad@36={sad_head_z:.3f} -> '
      f'{"OK" if sad_head_z < rest_head_z - 0.05 else "FAIL"}')

if HEADLESS:
    os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)
    for obj in bpy.data.objects:
        obj.select_set(obj.type in {'MESH', 'ARMATURE'})
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.export_scene.gltf(
        filepath=OUT_GLB,
        export_format='GLB',
        use_selection=True,
        export_apply=True,
        export_animation_mode='NLA_TRACKS',
        export_skins=True,
    )
    print('[export] wrote', OUT_GLB, os.path.getsize(OUT_GLB), 'bytes')
    with open(OUT_GLB, 'rb') as fh:
        buf = fh.read()
    json_len = struct.unpack_from('<I', buf, 12)[0]
    gltf = jsonlib.loads(buf[20:20 + json_len].decode())
    anims = [a.get('name') for a in gltf.get('animations', [])]
    print('[glb] animations:', ', '.join(anims))
    print('[glb] missing clips:', [c for c in CLIP_NAMES if c not in anims] or 'none')

    for track in arm_obj.animation_data.nla_tracks:
        track.mute = True
    reset_pose()
    scene.frame_set(1)
    bpy.ops.object.camera_add(location=(2.5, 3.4, 2.4))
    cam = bpy.context.active_object
    bpy.ops.object.empty_add(location=(0, 0, 1.3))
    target = bpy.context.active_object
    cam.constraints.new('TRACK_TO').target = target
    scene.camera = cam
    bpy.ops.object.light_add(type='SUN', location=(3, 4, 6))
    sun = bpy.context.active_object
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(-40), math.radians(20), math.radians(160))
    bpy.ops.object.light_add(type='AREA', location=(-2.5, 2.5, 2.5))
    fill = bpy.context.active_object
    fill.data.energy = 150.0
    fill.data.size = 4.0
    fill.rotation_euler = (math.radians(60), 0, math.radians(-140))
    world = bpy.data.worlds.new('W') if not bpy.data.worlds else bpy.data.worlds[0]
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (0.85, 0.90, 0.96, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = 0.7
    for engine in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH'):
        try:
            scene.render.engine = engine
            break
        except Exception:
            continue
    scene.render.resolution_x = 800
    scene.render.resolution_y = 1000
    scene.render.filepath = OUT_PREVIEW
    bpy.ops.render.render(write_still=True)
    print('[preview] wrote', OUT_PREVIEW)
else:
    for track in arm_obj.animation_data.nla_tracks:
        track.mute = True
    reset_pose()
    scene.frame_set(1)
    # Кости не мешают смотреть модель: тонкие и скрыты (глаз в Outliner
    # вернёт их для предпросмотра анимаций).
    arm_obj.data.display_type = 'WIRE'
    arm_obj.hide_set(True)
    print('Бруно собран в коллекцию "Bruno". Правь числа -> Run Script.')
    print('Клипы: включи глаз у Bruno_Rig в Outliner -> NLA -> solo -> Play.')
