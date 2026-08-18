"""Sophie (Meshy remeshed) — скелет с нуля + 11 клипов + экспорт.

Вход:  Meshy_AI_Sophie_remeshed.glb (корень проекта; стоячая, без рига)
Выход: public/assets/sophie_meshy.glb (риг + Idle, Walk, Run, Sit, Happy,
       Sad, Curious, Sniff, Bark, TailWag, Jump)

Запуск (headless):
  /Applications/Blender.app/Contents/MacOS/Blender --background \
      --python tools/blender/build_sophie_meshy.py

Скелет строится по замерам самого меша (кластеры лап, нос, уши, хвост),
поэтому небольшие изменения генерации Meshy скрипт переживёт. Веса — наш
проверенный ручной скиннинг (расстояние до сегмента кости) с жёсткими
зонами: колонны лап, купол головы, уши. Движения мягкие (safety-правила).
"""

import math
import os
import struct
import json as jsonlib

import bpy
from mathutils import Matrix, Vector
from mathutils.geometry import intersect_point_line

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'Meshy_AI_Sophie_remeshed.glb')
OUT = os.path.join(ROOT, 'public', 'assets', 'sophie_meshy.glb')
OUT_PREVIEW = os.path.join(ROOT, 'tools', 'blender', 'preview_sophie_meshy.png')
HEADLESS = bpy.app.background

CLIP_NAMES = ['Idle', 'Walk', 'Run', 'Sit', 'Happy', 'Sad', 'Curious',
              'Sniff', 'Bark', 'TailWag', 'Jump']

if HEADLESS:
    bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 24

bpy.ops.import_scene.gltf(filepath=SRC)
dog = max((o for o in bpy.data.objects if o.type == 'MESH'),
          key=lambda o: len(o.data.vertices))

# ------------------------------------------------- нормализация ориентации
# transform_apply в headless тихо фейлится -> запекаем через data API.
_mw = dog.matrix_world.copy()
dog.parent = None
dog.matrix_world = _mw
dog.data.transform(dog.matrix_world)
dog.matrix_world = Matrix.Identity(4)
# Морда у Meshy-экспорта смотрит в -Y; наша конвенция +Y -> флип 180.
dog.data.transform(Matrix.Rotation(math.pi, 4, 'Z'))
bpy.context.view_layer.update()

VS = [v.co.copy() for v in dog.data.vertices]
Z_MIN = min(v.z for v in VS)
Z_MAX = max(v.z for v in VS)
H = Z_MAX - Z_MIN
NOSE = max(VS, key=lambda v: v.y)
TAIL_TIP = min(VS, key=lambda v: v.y)
assert NOSE.z > TAIL_TIP.z - 0.1, 'ориентация: нос должен быть выше хвоста'

# Кластеры лап: нижние 8% высоты, квадранты (F = к морде).
feet = [v for v in VS if v.z < Z_MIN + 0.08 * H]
clusters = {}
for v in feet:
    k = ('L' if v.x > 0 else 'R') + ('F' if v.y > 0 else 'B')
    clusters.setdefault(k, []).append(v)
LEGS = {}
for k, pts in clusters.items():
    cx = sum(p.x for p in pts) / len(pts)
    cy = sum(p.y for p in pts) / len(pts)
    LEGS[k] = Vector((cx, cy, 0))
assert len(LEGS) == 4, f'ожидал 4 лапы, нашёл {len(LEGS)}: {list(LEGS)}'
print('[landmarks] nose', tuple(round(c, 2) for c in NOSE),
      'tail', tuple(round(c, 2) for c in TAIL_TIP))
for k, c in sorted(LEGS.items()):
    print(f'[landmarks] leg {k}: x={c.x:.2f} y={c.y:.2f}')

# Верх колонны лапы: докуда лапа читается как отдельный столбик.
def leg_top(center, r=0.17):
    zs = [v.z for v in VS
          if (v.xy - center.xy).length < r and v.z < Z_MIN + 0.5 * H]
    zs.sort()
    return zs[int(len(zs) * 0.97)] if zs else Z_MIN + 0.25 * H

LEG_TOP = {k: leg_top(c) for k, c in LEGS.items()}
print('[landmarks] leg tops:', {k: round(z, 2) for k, z in LEG_TOP.items()})

# Голова: центроид верхних 30% (у щенка голова = вся верхняя половина).
head_pts = [v for v in VS if v.z > Z_MAX - 0.3 * H]
HEAD_C = Vector((0,
                 sum(p.y for p in head_pts) / len(head_pts),
                 sum(p.z for p in head_pts) / len(head_pts)))
EAR_L = max(VS, key=lambda v: v.x)
EAR_R = min(VS, key=lambda v: v.x)
print('[landmarks] head center', tuple(round(c, 2) for c in HEAD_C),
      'earL', tuple(round(c, 2) for c in EAR_L))

GROUND = Z_MIN
FRONT_Y = (LEGS['LF'].y + LEGS['RF'].y) / 2
BACK_Y = (LEGS['LB'].y + LEGS['RB'].y) / 2
BODY_Z = GROUND + 0.38 * H            # центр корпуса
HEAD_BASE_Z = HEAD_C.z - 0.16 * H     # где шея переходит в голову

# Хвост-плюмаж завёрнут вверх за попой — ведём кости по его центроиду.
plume = [v for v in VS if v.y < BACK_Y - 0.13 and v.z > BODY_Z]
assert len(plume) > 100, f'не нашёл плюмаж хвоста ({len(plume)} вершин)'
PLUME_C = Vector((0,
                  sum(p.y for p in plume) / len(plume),
                  sum(p.z for p in plume) / len(plume)))
PLUME_TOP = max(plume, key=lambda v: v.z)
print('[landmarks] tail plume center', tuple(round(c, 2) for c in PLUME_C),
      'top', tuple(round(c, 2) for c in PLUME_TOP))

# --------------------------------------------------------------- арматура
arm_data = bpy.data.armatures.new('SophieRig')
arm = bpy.data.objects.new('SophieRig', arm_data)
scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')

def eb(name, head, tail, parent=None, connect=False):
    b = arm_data.edit_bones.new(name)
    b.head = head
    b.tail = tail
    if parent:
        b.parent = arm_data.edit_bones[parent]
        b.use_connect = connect
    # Детерминированный ролл: у вертикальных костей local X = мировой X
    # (чистый наклон вперёд без завала вбок), у горизонтальных local Z = верх.
    d = (Vector(tail) - Vector(head)).normalized()
    b.align_roll(Vector((0, -1, 0)) if abs(d.z) > 0.6 else Vector((0, 0, 1)))
    return b

eb('root', Vector((0, BACK_Y, BODY_Z)), Vector((0, BACK_Y + 0.25, BODY_Z)))
eb('hip', Vector((0, BACK_Y, BODY_Z)),
   Vector((0, (BACK_Y + FRONT_Y) / 2, BODY_Z + 0.02)), 'root')
eb('chest', Vector((0, (BACK_Y + FRONT_Y) / 2, BODY_Z + 0.02)),
   Vector((0, FRONT_Y + 0.05, BODY_Z + 0.05)), 'hip', connect=True)
eb('neck2', Vector((0, FRONT_Y + 0.05, BODY_Z + 0.05)),
   Vector((0, HEAD_C.y - 0.05, HEAD_BASE_Z)), 'chest', connect=True)
eb('head', Vector((0, HEAD_C.y - 0.05, HEAD_BASE_Z)),
   Vector((0, HEAD_C.y, HEAD_C.z + 0.12)), 'neck2', connect=True)
eb('snout', Vector((0, HEAD_C.y + 0.1, NOSE.z + 0.05)),
   Vector((0, NOSE.y - 0.05, NOSE.z)), 'head')
eb('earA', Vector((0.24, EAR_L.y, HEAD_C.z + 0.05)),
   Vector((EAR_L.x - 0.04, EAR_L.y, EAR_L.z)), 'head')
eb('earB', Vector((-0.24, EAR_R.y, HEAD_C.z + 0.05)),
   Vector((EAR_R.x + 0.04, EAR_R.y, EAR_R.z)), 'head')
eb('tail1', Vector((0, BACK_Y - 0.06, BODY_Z + 0.08)),
   Vector((0, PLUME_C.y, PLUME_C.z)), 'hip')
eb('tail2', Vector((0, PLUME_C.y, PLUME_C.z)),
   Vector((0, PLUME_TOP.y, PLUME_TOP.z + 0.02)), 'tail1', connect=True)

# Лапы: A = левая, B = правая (диагонали в клипах: frontA+rearB).
LEG_BONE = {}  # bone name -> cluster key
for key, cl, par in (('frontA', 'LF', 'chest'), ('frontB', 'RF', 'chest'),
                     ('rearA', 'LB', 'hip'), ('rearB', 'RB', 'hip')):
    c = LEGS[cl]
    top = Vector((c.x, c.y, LEG_TOP[cl]))
    mid = Vector((c.x, c.y, (LEG_TOP[cl] + GROUND) / 2))
    low = Vector((c.x, c.y, GROUND + 0.02))
    eb(key + '0', top, mid, par)
    eb(key + '1', mid, low, key + '0', connect=True)
    LEG_BONE[key + '0'] = cl
    LEG_BONE[key + '1'] = cl

bpy.ops.object.mode_set(mode='OBJECT')

BONES = {k: k for k in (
    'root', 'hip', 'chest', 'neck2', 'head', 'snout', 'earA', 'earB',
    'tail1', 'tail2', 'frontA0', 'frontA1', 'frontB0', 'frontB1',
    'rearA0', 'rearA1', 'rearB0', 'rearB1')}

# ---------------------------------------------- ошейник + медальон: rigid
# Жёсткие предметы нельзя растягивать между костями — "плывут". Находим их
# вершины по цвету текстуры (синий ошейник, золотой жетон) в зоне шеи и
# после сглаживания привязываем на 100% к neck2.
uv_data = dog.data.uv_layers.active.data
base_img = next((im for im in bpy.data.images if 'BaseColor' in im.name),
                None)
COLLAR = set()
if base_img is not None:
    IW, IH = base_img.size
    px = list(base_img.pixels)
    vert_uv = {}
    for loop in dog.data.loops:
        if loop.vertex_index not in vert_uv:
            vert_uv[loop.vertex_index] = uv_data[loop.index].uv.copy()

    def tex_rgb(uv):
        x = min(IW - 1, max(0, int((uv.x % 1.0) * IW)))
        y = min(IH - 1, max(0, int((uv.y % 1.0) * IH)))
        o = (y * IW + x) * 4
        return px[o], px[o + 1], px[o + 2]

    for i, v in enumerate(dog.data.vertices):
        uv = vert_uv.get(i)
        if uv is None:
            continue
        if not (0.0 < v.co.y and BODY_Z - 0.2 < v.co.z < HEAD_BASE_Z + 0.15):
            continue
        r, g, b = tex_rgb(uv)
        is_blue = b > 0.28 and b > r * 1.35 and b > g * 1.2
        is_gold = r > 0.5 and b < 0.45 and (r - b) > 0.25
        if is_blue or is_gold:
            COLLAR.add(i)
print('[collar] color seeds:', len(COLLAR))
assert len(COLLAR) > 200, 'ошейник по цвету не нашёлся — проверь пороги'

# У жетона есть белёсые участки (блик, окантовка) — цветом их не поймать.
# Разрастаем захват от цветовых семян по пространственной близости, чтобы
# вся деталь целиком стала жёсткой.
from mathutils.kdtree import KDTree as _KD
band = [i for i, v in enumerate(dog.data.vertices)
        if v.co.y > 0.0 and BODY_Z - 0.2 < v.co.z < HEAD_BASE_Z + 0.15]
kd_band = _KD(len(band))
for i in band:
    kd_band.insert(VS[i], i)
kd_band.balance()
frontier = set(COLLAR)
for _round in range(2):
    new = set()
    for i in frontier:
        for (_co, j, _d) in kd_band.find_range(VS[i], 0.022):
            if j not in COLLAR:
                new.add(j)
    COLLAR |= new
    frontier = new
print('[collar] rigid verts after growth:', len(COLLAR))

# ------------------------------------------------------------------ скин
# Ручной скиннинг: расстояние до сегмента кости, топ-3, жёсткие зоны.
for vg in list(dog.vertex_groups):
    dog.vertex_groups.remove(vg)

segments = []  # (name, head, tail)
for b in arm.data.bones:
    if b.name == 'root':
        continue
    segments.append((b.name, b.head_local.copy(), b.tail_local.copy()))
groups = {name: dog.vertex_groups.new(name=name) for name, *_ in segments}
groups['root'] = dog.vertex_groups.new(name='root')

def seg_dist(p, a, b):
    _, frac = intersect_point_line(p, a, b)
    frac = max(0.0, min(1.0, frac))
    return (p - a.lerp(b, frac)).length

LEG_R = 0.30        # радиус колонны лапы
EAR_X = 0.34        # дальше по |x| в зоне головы = ухо
HEAD_Z = HEAD_BASE_Z + 0.03

def leg_zone(co):
    """Ключ кластера, если вершина внутри колонны лапы, иначе None."""
    if co.z > max(LEG_TOP.values()) + 0.05:
        return None
    best, bd = None, 1e9
    for k, c in LEGS.items():
        d = (co.xy - c.xy).length
        if d < bd:
            best, bd = k, d
    if bd < LEG_R and co.z < LEG_TOP[best] + 0.04:
        return best
    return None

RAW = []  # per-vertex dict: bone name -> вес (до сглаживания)
for i, v in enumerate(dog.data.vertices):
    co = v.co
    lz = leg_zone(co)
    cands = []
    for name, h, t in segments:
        d = seg_dist(co, h, t)
        is_leg = name[:-1] in ('frontA', 'frontB', 'rearA', 'rearB')
        is_headish = name in ('head', 'snout', 'earA', 'earB')
        is_ear = name in ('earA', 'earB')
        in_tail = (co.y < BACK_Y - 0.1 and co.z > BODY_Z - 0.05
                   and lz is None)
        if lz is not None:
            # внутри колонны: только кости этой лапы + низ корпуса
            if is_leg and LEG_BONE[name] != lz:
                continue
            if not is_leg and name not in ('hip', 'chest'):
                continue
            if not is_leg:
                d *= 2.2  # корпус подмешивается только у верха колонны
        elif in_tail:
            # зона плюмажа: только хвост (+таз чуть-чуть у основания)
            if name not in ('tail1', 'tail2', 'hip'):
                continue
            if name == 'hip':
                d *= 2.5
        else:
            if is_leg:
                continue  # вне колонн лапы не тянут
            # Голова = купол СВЕРХУ + выступ морды/подбородка СПЕРЕДИ:
            # рот ниже купола, но он часть головы, иначе его рвёт на
            # границе голова/шея при поворотах.
            in_head = ((co.z > HEAD_Z and co.y > FRONT_Y - 0.1)
                       or (co.y > HEAD_C.y + 0.15 and co.z > BODY_Z + 0.1))
            if in_head:
                if name in ('hip', 'chest', 'tail1', 'tail2'):
                    continue
                # уши не трогают лицо (глаза!): только боковины и затылок
                if is_ear and abs(co.x) < 0.30 and co.y > HEAD_C.y:
                    continue
                if is_ear and abs(co.x) < EAR_X:
                    d *= 2.5
                if not is_headish and name != 'neck2':
                    continue
                # шея подмешивается только узкой полосой у основания
                if name == 'neck2':
                    d *= 2.8
            else:
                if is_ear:
                    continue
                if name == 'snout':
                    d *= 1.8
                # хвост не хватает корпус
                if name in ('tail1', 'tail2') and co.y > BACK_Y - 0.02:
                    d *= 2.4
        cands.append((d, name))
    cands.sort()
    top = cands[:3]
    ws = [(1.0 / (d + 0.03)) ** 2 for d, _ in top]
    total = sum(ws)
    RAW.append({name: w / total for (d, name), w in zip(top, ws)})

# --- пространственное сглаживание весов -----------------------------------
# Шерсть Meshy — отдельные лоскуты-шеллы: соседние по пространству вершины
# не связаны рёбрами и могут прицепиться к разным костям -> рваные клочья
# при анимации. Усредняем веса по соседям в радиусе (KD-дерево), 2 прохода.
from mathutils.kdtree import KDTree

size = len(dog.data.vertices)
kd = KDTree(size)
for i, v in enumerate(dog.data.vertices):
    kd.insert(v.co, i)
kd.balance()
SMOOTH_R = 0.05
for _pass in range(2):
    NEW = []
    for i, v in enumerate(dog.data.vertices):
        acc = {}
        tot = 0.0
        for (_co, j, d) in kd.find_range(v.co, SMOOTH_R):
            wt = 1.0 / (d + 0.012)
            for name, w in RAW[j].items():
                acc[name] = acc.get(name, 0.0) + w * wt
            tot += wt
        NEW.append({n: w / tot for n, w in acc.items()})
    RAW = NEW
    print(f'[skin] smoothing pass {_pass + 1} done')

# жёсткая привязка ошейника/жетона — после сглаживания, чтобы не размыло.
# К ГРУДИ, не к шее: при поклонах головы (Sniff/Sad) ошейник остаётся
# лежать на корпусе, как настоящий, и жетон не въезжает в грудь.
for i in COLLAR:
    RAW[i] = {'chest': 1.0}

for i, wmap in enumerate(RAW):
    top = sorted(wmap.items(), key=lambda kv: -kv[1])[:4]
    total = sum(w for _, w in top)
    for name, w in top:
        wn = w / total
        if wn > 0.04:
            groups[name].add([i], wn, 'REPLACE')

mod = dog.modifiers.new('Armature', 'ARMATURE')
mod.object = arm
dog.parent = arm

_totals = {}
for v in dog.data.vertices:
    for gr in v.groups:
        nm = dog.vertex_groups[gr.group].name
        _totals[nm] = _totals.get(nm, 0.0) + gr.weight
_top = sorted(_totals.items(), key=lambda kv: -kv[1])[:8]
print('[skin] groups:', len(_totals), 'top:',
      ', '.join(f'{n}={t:.0f}' for n, t in _top))
assert len(_totals) > 12, 'скин не удался'

for pb in arm.pose.bones:
    pb.rotation_mode = 'XYZ'

# ---------------------------------------------- автоподбор осей per-bone
def reset_pose():
    for pb in arm.pose.bones:
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)

def tail_world_pose(key):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    eo = arm.evaluated_get(dg)
    return (eo.matrix_world @ eo.pose.bones[BONES[key]].tail).copy()

def _probe(key, axis, amount=0.35):
    reset_pose()
    rest = tail_world_pose(key)
    e = [0.0, 0.0, 0.0]
    e[axis] = amount
    arm.pose.bones[BONES[key]].rotation_euler = e
    moved = tail_world_pose(key)
    reset_pose()
    return moved - rest

def axes_for(key):
    # Оси per-bone. Важно: 'fwd' и 'side' — всегда РАЗНЫЕ оси, иначе
    # кейфреймы затирают друг друга (у вертикальных костей обе метрики
    # сваливались на одну ось X).
    b = arm.data.bones[BONES[key]]
    bd = (b.tail_local - b.head_local).normalized()
    dx = _probe(key, 0)
    dz = _probe(key, 2)
    down = Vector((0, 0, -1))
    side = Vector((1, 0, 0))
    fwd = Vector((0, 1, 0))
    if abs(bd.z) > 0.6:
        # вертикальная кость (шея/голова/лапы): главное — наклон вперёд
        if abs(dx.dot(fwd)) >= abs(dz.dot(fwd)):
            fa, oa, fd, od = 0, 2, dx, dz
        else:
            fa, oa, fd, od = 2, 0, dz, dx
        fwd_ax = (fa, 1.0 if fd.dot(fwd) > 0 else -1.0)
        side_ax = (oa, 1.0 if od.dot(side) >= 0 else -1.0)
        return {'pitch': fwd_ax, 'side': side_ax, 'fwd': fwd_ax}
    # горизонтальная кость (уши/хвост/корпус): главное — вниз
    if abs(dx.dot(down)) >= abs(dz.dot(down)):
        pa, oa, pd, od = 0, 2, dx, dz
    else:
        pa, oa, pd, od = 2, 0, dz, dx
    pitch = (pa, 1.0 if pd.dot(down) > 0 else -1.0)
    side_ax = (oa, 1.0 if od.dot(side) >= 0 else -1.0)
    if abs(pd.dot(fwd)) >= abs(od.dot(fwd)):
        fwd_ax = (pa, 1.0 if pd.dot(fwd) > 0 else -1.0)
    else:
        fwd_ax = (oa, 1.0 if od.dot(fwd) > 0 else -1.0)
    return {'pitch': pitch, 'side': side_ax, 'fwd': fwd_ax}

AX = {}
for _k in BONES:
    if _k != 'root':
        AX[_k] = axes_for(_k)
print('[axes] head:', AX['head'], 'frontA0:', AX['frontA0'])

# ------------------------------------------------------------------ клипы
arm.animation_data_create()

def kf(key, frame, x=None, y=None, z=None, loc=None):
    pb = arm.pose.bones[BONES[key]]
    if x is not None or y is not None or z is not None:
        e = pb.rotation_euler
        pb.rotation_euler = (x if x is not None else e.x,
                             y if y is not None else e.y,
                             z if z is not None else e.z)
        pb.keyframe_insert('rotation_euler', frame=frame)
    if loc is not None:
        pb.location = loc
        pb.keyframe_insert('location', frame=frame)

def kfa(key, frame, angle, mode='pitch'):
    axis, s = AX[key][mode]
    kf(key, frame, **{('x', 'y', 'z')[axis]: angle * s})

def begin(last):
    reset_pose()
    arm.animation_data.action = None
    scene.frame_start = 1
    scene.frame_end = last

def end(name):
    act = arm.animation_data.action
    assert act is not None, f'no action for {name}'
    act.name = f'SM_{name}'
    act.use_fake_user = True
    track = arm.animation_data.nla_tracks.new()
    track.name = name
    strip = track.strips.new(name, 1, act)
    if hasattr(strip, 'action_slot') and getattr(strip, 'action_slot', None) is None:
        try:
            strip.action_slot = act.slots[0]
        except Exception:
            pass
    arm.animation_data.action = None

def tail_wag(f0, f1, period=8, amp=0.45):
    f = f0
    s = 1
    while f <= f1:
        kfa('tail1', f, amp * s, 'side')
        kfa('tail2', f, amp * 0.7 * s, 'side')
        s = -s
        f += period

# --- Idle: дыхание, медленный хвост, лёгкое ухо (72f loop)
begin(72)
for f, z in ((1, 0.0), (36, 0.012), (72, 0.0)):
    kf('root', f, loc=(0, 0, z))
for f, p in ((1, 0.0), (36, 0.05), (72, 0.0)):
    kfa('neck2', f, p, 'fwd')
tail_wag(1, 72, period=18, amp=0.22)
for f, p in ((1, 0.0), (36, 0.07), (72, 0.0)):
    kfa('earA', f, p)
end('Idle')

# --- Walk: диагональная походка (24f loop)
begin(24)
for f, a in ((1, 0.35), (13, -0.35), (24, 0.35)):
    kfa('frontA0', f, a, 'fwd')
    kfa('rearB0', f, a, 'fwd')
    kfa('frontB0', f, -a, 'fwd')
    kfa('rearA0', f, -a, 'fwd')
    kfa('frontA1', f, -a * 0.5, 'fwd')
    kfa('frontB1', f, a * 0.5, 'fwd')
for f, z in ((1, -0.008), (7, 0.012), (13, -0.008), (19, 0.012), (24, -0.008)):
    kf('root', f, loc=(0, 0, z))
tail_wag(1, 24, period=12, amp=0.2)
for f, p in ((1, 0.04), (13, -0.03), (24, 0.04)):
    kfa('head', f, p, 'fwd')
end('Walk')

# --- Run: лёгкий галоп (16f loop)
begin(16)
for f, a in ((1, 0.55), (9, -0.55), (16, 0.55)):
    kfa('frontA0', f, a, 'fwd')
    kfa('frontB0', f, a * 0.85, 'fwd')
    kfa('rearA0', f, -a, 'fwd')
    kfa('rearB0', f, -a * 0.85, 'fwd')
for f, z in ((1, -0.02), (5, 0.045), (9, -0.02), (13, 0.045), (16, -0.02)):
    kf('root', f, loc=(0, 0, z))
for f, p in ((1, 0.06), (9, -0.05), (16, 0.06)):
    kfa('hip', f, p)
tail_wag(1, 16, period=8, amp=0.18)
end('Run')

# --- Sit: попа вниз, задние лапы складываются, передние стоят (60f)
begin(60)
# задние лапы: небольшой вынос бедра вперёд + глубокий сгиб колена,
# чтобы голень уходила под корпус, а не болталась в воздухе
for k in ('rearA0', 'rearB0'):
    kfa(k, 1, 0.0, 'fwd')
    kfa(k, 16, 0.85, 'fwd')
    kfa(k, 60, 0.85, 'fwd')
for k in ('rearA1', 'rearB1'):
    kfa(k, 1, 0.0, 'fwd')
    kfa(k, 16, -1.5, 'fwd')
    kfa(k, 60, -1.5, 'fwd')
# Настоящая посадка: попа опускается ДО ЗЕМЛИ. Меряем низ попы по мешу
# (центральная полоса без лап), угол наклона корпуса выводим из этого.
SIT_T = 0.75                     # ~43 град — вертикальная посадка как в арте
# −0.085: поправка дуги плеча на большом угле (по замеру лапы о землю)
SIT_DROP = 0.92 * math.sin(SIT_T) - 0.085
print(f'[sit] drop={SIT_DROP:.2f} tilt={math.degrees(SIT_T):.0f}deg')
kf('root', 1, loc=(0, 0, 0))
kf('root', 16, loc=(0, 0, -SIT_DROP))
kf('root', 60, loc=(0, 0, -SIT_DROP))
kfa('hip', 1, 0.0)
kfa('hip', 16, -SIT_T)
kfa('hip', 60, -SIT_T)
# передние лапы контрятся на тот же угол назад — остаются вертикальными
for k in ('frontA0', 'frontB0'):
    kfa(k, 1, 0.0, 'fwd')
    kfa(k, 16, -SIT_T, 'fwd')
    kfa(k, 60, -SIT_T, 'fwd')
# взгляд ровно: голова компенсирует наклон корпуса
kfa('neck2', 1, 0.0, 'fwd')
kfa('neck2', 16, SIT_T * 0.5, 'fwd')
kfa('neck2', 60, SIT_T * 0.5, 'fwd')
kfa('head', 1, 0.0, 'fwd')
kfa('head', 16, SIT_T * 0.75, 'fwd')
kfa('head', 60, SIT_T * 0.75, 'fwd')
kf('head', 16, **{('x', 'y', 'z')[AX['head']['side'][0]]:
                  0.12 * AX['head']['side'][1]})
kf('head', 60, **{('x', 'y', 'z')[AX['head']['side'][0]]:
                  0.12 * AX['head']['side'][1]})
tail_wag(20, 60, period=14, amp=0.3)
end('Sit')

# --- Happy: подпрыгивания + быстрый хвост + уши (48f loop)
begin(48)
for f, z in ((1, 0.0), (8, 0.05), (14, 0.0), (22, 0.05), (28, 0.0),
             (36, 0.03), (48, 0.0)):
    kf('root', f, loc=(0, 0, z))
kfa('neck2', 1, -0.14, 'fwd')
kfa('neck2', 48, -0.14, 'fwd')
tail_wag(1, 48, period=6, amp=0.5)
for f, p in ((1, 0.0), (8, -0.18), (14, 0.06), (22, -0.18), (28, 0.0), (48, 0.0)):
    kfa('earA', f, p)
    kfa('earB', f, p)
end('Happy')

# --- Sad: голова вниз, уши повисли, хвост опущен (72f loop)
begin(72)
for f in (1, 72):
    kfa('neck2', f, 0.35, 'fwd')
    kfa('head', f, 0.45, 'fwd')
    kfa('earA', f, 0.4)
    kfa('earB', f, 0.4)
    kfa('tail1', f, 0.85)  # pitch+ = вниз (probe): хвост повисает
    kfa('tail2', f, 0.55)
    kf('root', f, loc=(0, 0, -0.015))
kfa('head', 36, 0.52, 'fwd')
end('Sad')

# --- Curious: наклон головы, ухо торчком, хвост медленный (60f loop)
begin(60)
kfa('head', 1, 0.0, 'side')
kfa('head', 18, 0.3, 'side')
kfa('head', 42, -0.24, 'side')
kfa('head', 60, 0.0, 'side')
kfa('earA', 1, 0.0)
kfa('earA', 18, -0.28)
kfa('earA', 60, 0.0)
kfa('neck2', 1, -0.06, 'fwd')
kfa('neck2', 60, -0.06, 'fwd')
tail_wag(1, 60, period=16, amp=0.25)
end('Curious')

# --- Sniff: нос к земле, мелкие принюхивания (60f)
begin(60)
kfa('neck2', 1, 0.0, 'fwd')
kfa('neck2', 14, 0.6, 'fwd')
kfa('neck2', 50, 0.6, 'fwd')
kfa('neck2', 60, 0.1, 'fwd')
kfa('head', 1, 0.0, 'fwd')
kfa('head', 14, 0.45, 'fwd')
for f, p in ((20, 0.34), (25, 0.5), (30, 0.34), (35, 0.5), (40, 0.34)):
    kfa('head', f, p, 'fwd')
kfa('head', 60, 0.05, 'fwd')
tail_wag(1, 60, period=12, amp=0.2)
end('Sniff')

# --- Bark: мягкое "гав" — без агрессии (48f)
begin(48)
for f, p in ((1, 0.0), (10, -0.2), (14, 0.12), (18, -0.16), (22, 0.1),
             (30, 0.0), (48, 0.0)):
    kfa('head', f, p, 'fwd')
for f, z in ((1, 0.0), (10, -0.012), (14, 0.008), (22, 0.0)):
    kf('root', f, loc=(0, 0, z))
tail_wag(1, 48, period=10, amp=0.3)
end('Bark')

# --- TailWag: активное виляние + покачивание попы (48f loop)
begin(48)
tail_wag(1, 48, period=5, amp=0.6)
f = 1
s = 1
while f <= 48:
    kfa('hip', f, 0.05 * s, 'side')
    s = -s
    f += 10
kfa('neck2', 1, -0.07, 'fwd')
kfa('neck2', 48, -0.07, 'fwd')
end('TailWag')

# --- Jump: мягкий прыжок на месте (36f): присед -> взлёт -> приземление
begin(36)
for f, z in ((1, 0.0), (8, -0.05), (14, 0.14), (20, 0.16), (26, 0.0),
             (30, -0.02), (36, 0.0)):
    kf('root', f, loc=(0, 0, z))
for k in ('frontA0', 'frontB0'):
    kfa(k, 1, 0.0, 'fwd')
    kfa(k, 8, -0.2, 'fwd')
    kfa(k, 16, 0.45, 'fwd')
    kfa(k, 26, 0.0, 'fwd')
    kfa(k, 36, 0.0, 'fwd')
for k in ('rearA0', 'rearB0'):
    kfa(k, 1, 0.0, 'fwd')
    kfa(k, 8, 0.25, 'fwd')
    kfa(k, 16, -0.35, 'fwd')
    kfa(k, 26, 0.0, 'fwd')
    kfa(k, 36, 0.0, 'fwd')
kfa('neck2', 8, 0.1, 'fwd')
kfa('neck2', 16, -0.12, 'fwd')
kfa('neck2', 26, 0.0, 'fwd')
tail_wag(1, 36, period=9, amp=0.3)
for f, p in ((1, 0.0), (14, -0.15), (26, 0.0)):
    kfa('earA', f, p)
    kfa('earB', f, p)
end('Jump')

reset_pose()

# ------------------------------------------------------------- верификация
def clip_probe(clip, frame, key):
    act = bpy.data.actions[clip]
    arm.animation_data.action = act
    if hasattr(arm.animation_data, 'action_slot'):
        try:
            arm.animation_data.action_slot = act.slots[0]
        except Exception:
            pass
    scene.frame_set(frame)
    p = tail_world_pose(key)
    arm.animation_data.action = None
    reset_pose()
    scene.frame_set(1)
    return p

rest_head = tail_world_pose('head')
sad_head = clip_probe('SM_Sad', 36, 'head')
sad_move = (sad_head - rest_head).length
print(f'[verify] Sad head bow: {sad_move:.3f} -> '
      f'{"OK" if sad_move > 0.08 and sad_head.z <= rest_head.z else "FAIL"}')
rest_foot = tail_world_pose('frontA1')
walk_foot = clip_probe('SM_Walk', 13, 'frontA1')
print(f'[verify] Walk foot swing: {(walk_foot - rest_foot).length:.3f} -> '
      f'{"OK" if (walk_foot - rest_foot).length > 0.05 else "FAIL"}')

def mesh_leg_disp(clip, frame):
    def sample():
        dg = bpy.context.evaluated_depsgraph_get()
        ev = dog.evaluated_get(dg).to_mesh()
        pts = [(i, v.co.copy()) for i, v in enumerate(ev.vertices)
               if v.co.z < GROUND + 0.25 * H]
        dog.evaluated_get(dg).to_mesh_clear()
        return dict(pts)

    reset_pose()
    scene.frame_set(1)
    rest = sample()
    act = bpy.data.actions[clip]
    arm.animation_data.action = act
    if hasattr(arm.animation_data, 'action_slot'):
        try:
            arm.animation_data.action_slot = act.slots[0]
        except Exception:
            pass
    scene.frame_set(frame)
    posed = sample()
    arm.animation_data.action = None
    reset_pose()
    scene.frame_set(1)
    return max((posed[i] - rest[i]).length for i in rest if i in posed)

leg_disp = mesh_leg_disp('SM_Walk', 13)
print(f'[verify] Walk MESH leg displacement: {leg_disp:.3f} -> '
      f'{"OK" if leg_disp > 0.05 else "FAIL"}')

rest_tail = tail_world_pose('tail2')
sad_tail = clip_probe('SM_Sad', 36, 'tail2')
print(f'[verify] Sad tail droop dz={rest_tail.z - sad_tail.z:.3f} -> '
      f'{"OK" if rest_tail.z - sad_tail.z > 0.15 else "FAIL"}')
sit_paw = clip_probe('SM_Sit', 40, 'frontA1')
print(f'[verify] Sit front paw ground dz={sit_paw.z - rest_foot.z:+.3f} -> '
      f'{"OK" if abs(sit_paw.z - rest_foot.z) < 0.07 else "FAIL"}')
wag_tail = clip_probe('SM_TailWag', 6, 'tail2')
print(f'[verify] TailWag side swing dx={abs(wag_tail.x - rest_tail.x):.3f} -> '
      f'{"OK" if abs(wag_tail.x - rest_tail.x) > 0.1 else "FAIL"}')

# ------------------------------------------- текстуры: вес файла для веба
for img in bpy.data.images:
    if max(img.size) > 2048:
        img.scale(2048, 2048)
        print('[tex] downscaled', img.name, '-> 2048')

if HEADLESS:
    for o in bpy.data.objects:
        o.select_set(o in (arm, dog))
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.gltf(
        filepath=OUT,
        export_format='GLB',
        use_selection=True,
        export_apply=False,
        export_animation_mode='NLA_TRACKS',
        export_skins=True,
        export_image_format='AUTO',
        export_jpeg_quality=85,
    )
    print('[export] wrote', OUT, os.path.getsize(OUT), 'bytes')
    with open(OUT, 'rb') as fh:
        buf = fh.read()
    json_len = struct.unpack_from('<I', buf, 12)[0]
    gltf = jsonlib.loads(buf[20:20 + json_len].decode())
    anims = [a.get('name') for a in gltf.get('animations', [])]
    print('[glb] animations:', ', '.join(anims))
    print('[glb] missing:', [c for c in CLIP_NAMES if c not in anims] or 'none')

    # ------------------------------------------------------------ превью
    for track in arm.animation_data.nla_tracks:
        track.mute = True
    bpy.ops.object.light_add(type='SUN', location=(2, -3, 4))
    bpy.context.active_object.data.energy = 3
    world = bpy.data.worlds.new('W') if not bpy.data.worlds else bpy.data.worlds[0]
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (0.88, 0.90, 0.94, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = 0.9
    bpy.ops.object.empty_add(location=(0, 0, 0.0))
    target = bpy.context.active_object
    scene.camera = None
    # морда в +Y -> камера спереди-справа
    bpy.ops.object.camera_add(location=(1.7, 2.3, 0.8))
    cam = bpy.context.active_object
    cam.constraints.new('TRACK_TO').target = target
    try:
        scene.view_settings.view_transform = 'Standard'
    except Exception:
        pass
    scene.camera = cam
    for engine in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH'):
        try:
            scene.render.engine = engine
            break
        except Exception:
            continue
    scene.render.resolution_x = 700
    scene.render.resolution_y = 700
    scene.render.image_settings.file_format = 'PNG'

    def render_pose(label, clip, frame):
        if clip:
            act = bpy.data.actions[clip]
            arm.animation_data.action = act
            if hasattr(arm.animation_data, 'action_slot'):
                try:
                    arm.animation_data.action_slot = act.slots[0]
                except Exception:
                    pass
        scene.frame_set(frame)
        scene.render.filepath = OUT_PREVIEW.replace('.png', f'_{label}.png')
        bpy.ops.render.render(write_still=True)
        arm.animation_data.action = None
        reset_pose()

    for label, clip, frame in (('rest', None, 1), ('walk', 'SM_Walk', 13),
                               ('sit', 'SM_Sit', 40), ('sad', 'SM_Sad', 36),
                               ('jump', 'SM_Jump', 16),
                               ('wag', 'SM_TailWag', 6)):
        render_pose(label, clip, frame)
    # Ключевые позы строго сбоку — силуэт головы, спины и хвоста
    cam.location = (2.6, -0.2, 0.15)
    render_pose('sad_side', 'SM_Sad', 36)
    render_pose('sit_side', 'SM_Sit', 40)
    render_pose('sniff_side', 'SM_Sniff', 30)
    render_pose('walk_side', 'SM_Walk', 7)
    print('[preview] wrote', OUT_PREVIEW.replace('.png', '_*.png'))
else:
    for track in arm.animation_data.nla_tracks:
        track.mute = True
    reset_pose()
    print('Клипы готовы: выбери арматуру -> NLA -> solo -> Play.')
