"""Sophie v2 — родной риг Meshy (квадрупед, 27 костей) + наши 11 клипов.

Вход:  sophie_rig_meshy.glb (корень; риг+скин Meshy, клип Walking)
Выход: public/assets/sophie_meshy2.glb (Idle, Walk, Run, Sit, Happy, Sad,
       Curious, Sniff, Bark, TailWag, Jump)

Запуск:
  /Applications/Blender.app/Contents/MacOS/Blender --background \
      --python tools/blender/build_sophie_meshy2.py

Скин Meshy не трогаем (он гладкий), кроме ошейника с жетоном — их вершины
жёстко привязываются к chest (иначе жёсткие предметы "плывут"). Walking
Meshy становится Walk и Run (Run — ускоренная копия). Остальные клипы
авторские, на пробах осей (rest-позу не вращаем — ориентацию решает движок).
Все повороты пишутся кватернионами: исходный Walking тоже кватернионный,
режимы вращения костей смешивать нельзя.
"""

import math
import os
import struct
import json as jsonlib

import bpy
from mathutils import Euler, Matrix, Vector
from mathutils.kdtree import KDTree

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'sophie_rig_meshy.glb')
OUT = os.path.join(ROOT, 'public', 'assets', 'sophie_meshy2.glb')
OUT_PREVIEW = os.path.join(ROOT, 'tools', 'blender', 'preview_sophie_m2.png')
HEADLESS = bpy.app.background

CLIP_NAMES = ['Idle', 'Walk', 'Run', 'Sit', 'Happy', 'Sad', 'Curious',
              'Sniff', 'Bark', 'TailWag', 'Jump']

if HEADLESS:
    bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 24

bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
dog = max(meshes, key=lambda o: len(o.data.vertices))
for o in meshes:
    if o is not dog:
        print('[clean] removing stray mesh:', o.name)
        bpy.data.objects.remove(o, do_unlink=True)
assert len(dog.vertex_groups) > 20, 'нет весов рига Meshy'

walk_src = next(a for a in bpy.data.actions if 'Walk' in a.name or 'Take' in a.name)
print('[src] walk action:', walk_src.name)

BONES = {
    'root': 'Hips', 'hips': 'Hips', 'chest': 'chest', 'head': 'head',
    'earA': 'earend', 'earB': 'R_earend',
    'tail1': 'tailstart', 'tail2': 'tail1', 'tail3': 'tail2',
    'fA': 'frontleg', 'fA0': 'frontleg0', 'fA1': 'frontleg1',
    'fB': 'R_frontleg', 'fB0': 'R_frontleg0', 'fB1': 'R_frontleg1',
    'rA': 'backleg', 'rA0': 'backleg0', 'rA1': 'backleg1',
    'rB': 'R_backleg', 'rB0': 'R_backleg0', 'rB1': 'R_backleg1',
}
for k, n in BONES.items():
    assert n in arm.data.bones, f'нет кости {n} ({k})'

# --------------------------------------------------- габариты (локальные)
# У Meshy армейчер со scale 0.01 и поворотом: все размеры и location-ключи
# считаем в ЛОКАЛЬНЫХ единицах скелета (up = local Y, вперёд = local Z).
bpy.context.view_layer.update()
_heads = [b.head_local for b in arm.data.bones]
S = max(h.y for h in _heads) - min(h.y for h in _heads)      # рост, локально
BODY_LEN = abs(arm.data.bones[BONES['fA']].head_local.z
               - arm.data.bones[BONES['hips']].head_local.z)
# мировой рост — для верификаций через world-пробы
_wz = [(arm.matrix_world @ h).z for h in _heads]
S_W = max(_wz) - min(_wz)
# куда смотрит морда в мире (для критерия 'fwd' в пробах осей)
_face_w = (arm.matrix_world @ arm.data.bones['head'].head_local
           - arm.matrix_world @ arm.data.bones['Hips'].head_local)
FACE = 1.0 if _face_w.y >= 0 else -1.0
print(f'[size] S_local={S:.3f} body_len={BODY_LEN:.3f} S_world={S_W:.4f} '
      f'face_y={"+" if FACE > 0 else "-"}Y')

# --------------------------------------------- ошейник + жетон -> rigid
uv_data = dog.data.uv_layers.active.data if dog.data.uv_layers.active else None
base_img_guess = None
for m in dog.data.materials:
    if not m or not m.use_nodes:
        continue
    for n in m.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image is not None:
            if base_img_guess is None or (n.image.size[0] > base_img_guess.size[0]):
                base_img_guess = n.image
COLLAR = set()
if uv_data is not None and base_img_guess is not None:
    IW, IH = base_img_guess.size
    px = list(base_img_guess.pixels)
    vert_uv = {}
    for loop in dog.data.loops:
        if loop.vertex_index not in vert_uv:
            vert_uv[loop.vertex_index] = uv_data[loop.index].uv.copy()
    chest_l = arm.data.bones[BONES['chest']].head_local
    head_y = arm.data.bones[BONES['head']].head_local.y
    for i, v in enumerate(dog.data.vertices):
        uv = vert_uv.get(i)
        if uv is None:
            continue
        # пояс ошейника: ниже головы (глаза тоже синие!), выше лап
        if not (0.25 * head_y < v.co.y < head_y - 0.1 * S):
            continue
        if (v.co - chest_l).length > 0.6 * S:
            continue
        x = min(IW - 1, max(0, int((uv.x % 1.0) * IW)))
        y = min(IH - 1, max(0, int((uv.y % 1.0) * IH)))
        o4 = (y * IW + x) * 4
        r, g, b = px[o4], px[o4 + 1], px[o4 + 2]
        if (b > 0.28 and b > r * 1.35 and b > g * 1.2) or \
           (r > 0.5 and b < 0.45 and (r - b) > 0.25):
            COLLAR.add(i)
    if len(COLLAR) > 100:
        vs_l = [v.co.copy() for v in dog.data.vertices]
        kd = KDTree(len(vs_l))
        for i, co in enumerate(vs_l):
            kd.insert(co, i)
        kd.balance()
        frontier = set(COLLAR)
        for _ in range(1):
            new = set()
            for i in frontier:
                for (_c, j, _d) in kd.find_range(vs_l[i], 0.035 * S):
                    if j not in COLLAR:
                        new.add(j)
            COLLAR |= new
            frontier = new
        assert len(COLLAR) < 12000, f'захват ошейника разросся: {len(COLLAR)}'
        cg = dog.vertex_groups.get('chest')
        for i in COLLAR:
            gidxs = [g.group for g in dog.data.vertices[i].groups]
            for gi in gidxs:
                dog.vertex_groups[gi].remove([i])
            cg.add([i], 1.0, 'REPLACE')
print('[collar] rigid verts:', len(COLLAR))

# --------------------------------------------------------- пробы осей
for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'

SHADOW = {}  # key -> [x,y,z] эйлер-теневик текущего клипа

def reset_pose():
    SHADOW.clear()
    for pb in arm.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
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
    arm.pose.bones[BONES[key]].rotation_quaternion = Euler(e, 'XYZ').to_quaternion()
    moved = tail_world_pose(key)
    reset_pose()
    return moved - rest

def axes_for(key):
    b = arm.data.bones[BONES[key]]
    bd = ((arm.matrix_world.to_3x3() @ (b.tail_local - b.head_local))).normalized()
    dx = _probe(key, 0)
    dz = _probe(key, 2)
    down = Vector((0, 0, -1))
    side = Vector((1, 0, 0))
    fwd = Vector((0, FACE, 0))
    if abs(bd.z) > 0.6:
        if abs(dx.dot(fwd)) >= abs(dz.dot(fwd)):
            fa, oa, fd, od = 0, 2, dx, dz
        else:
            fa, oa, fd, od = 2, 0, dz, dx
        fwd_ax = (fa, 1.0 if fd.dot(fwd) > 0 else -1.0)
        side_ax = (oa, 1.0 if od.dot(side) >= 0 else -1.0)
        return {'pitch': fwd_ax, 'side': side_ax, 'fwd': fwd_ax}
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

AX = {k: axes_for(k) for k in BONES if k != 'root'}
print('[axes] head:', AX['head'], 'fA0:', AX['fA0'])

def _probe_loc(axis, amount=0.1):
    reset_pose()
    rest = tail_world_pose('root')
    v = [0.0, 0.0, 0.0]
    v[axis] = amount
    arm.pose.bones[BONES['root']].location = v
    moved = tail_world_pose('root')
    reset_pose()
    return moved - rest

_best = None
for _ax in range(3):
    d = _probe_loc(_ax)
    if _best is None or abs(d.z) > abs(_best[1].z):
        _best = (_ax, d)
ROOT_UP_AX = _best[0]
ROOT_UP_SIGN = 1.0 if _best[1].z > 0 else -1.0
print(f'[axes] root up: axis={ROOT_UP_AX} sign={ROOT_UP_SIGN}')

def kfl(key, frame, up):
    # вертикальный location-ключ в локальных единицах (up>0 = вверх)
    v = [0.0, 0.0, 0.0]
    v[ROOT_UP_AX] = up * ROOT_UP_SIGN
    kf(key, frame, loc=tuple(v))

# ------------------------------------------------------------------ клипы
arm.animation_data_create()
for _tr in list(arm.animation_data.nla_tracks):
    arm.animation_data.nla_tracks.remove(_tr)
if arm.animation_data.action:
    arm.animation_data.action = None

def kf(key, frame, axis=None, angle=0.0, loc=None):
    pb = arm.pose.bones[BONES[key]]
    if axis is not None:
        e = SHADOW.setdefault(key, [0.0, 0.0, 0.0])
        e[axis] = angle
        pb.rotation_quaternion = Euler(e, 'XYZ').to_quaternion()
        pb.keyframe_insert('rotation_quaternion', frame=frame)
    if loc is not None:
        pb.location = loc
        pb.keyframe_insert('location', frame=frame)

def kfa(key, frame, angle, mode='pitch'):
    axis, s = AX[key][mode]
    kf(key, frame, axis=axis, angle=angle * s)

def begin(last):
    reset_pose()
    arm.animation_data.action = None
    scene.frame_start = 1
    scene.frame_end = last

def end(name):
    act = arm.animation_data.action
    assert act is not None, f'no action for {name}'
    act.name = f'S2_{name}'
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
        kfa('tail2', f, amp * 0.8 * s, 'side')
        kfa('tail3', f, amp * 0.6 * s, 'side')
        s = -s
        f += period

L = S  # масштаб для location-амплитуд (рост модели)


def strip_scale_curves(act):
    """Blender 5: кривые в channelbags слоёв. Убираем scale-треки."""
    removed = 0
    try:
        fcs = act.fcurves
        for fc in list(fcs):
            if fc.data_path.endswith('.scale'):
                fcs.remove(fc)
                removed += 1
        return removed
    except AttributeError:
        pass
    for layer in act.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                for fc in list(cb.fcurves):
                    if fc.data_path.endswith('.scale'):
                        cb.fcurves.remove(fc)
                        removed += 1
    return removed

# --- Walk / Run: цикл Meshy как есть (Run — ускоренная копия).
# ВАЖНО: у Meshy в кривых есть scale-треки (сжимают скелет до ~0.68 в
# движении) — вырезаем, масштаб костей анимировать нельзя.
for clip, scale in (('Walk', 1.0), ('Run', 0.55)):
    act = walk_src.copy()
    act.name = f'S2_{clip}'
    print(f'[scale-strip] {clip}:', strip_scale_curves(act), 'curves removed')
    act.use_fake_user = True
    track = arm.animation_data.nla_tracks.new()
    track.name = clip
    strip = track.strips.new(clip, 1, act)
    if hasattr(strip, 'action_slot') and getattr(strip, 'action_slot', None) is None:
        try:
            strip.action_slot = act.slots[0]
        except Exception:
            pass
    if scale != 1.0:
        strip.scale = scale
walk_src.use_fake_user = False

# --- Idle: дыхание, медленный хвост, ушко (72f loop)
begin(72)
for f, z in ((1, 0.0), (36, 0.008 * L), (72, 0.0)):
    kfl('root', f, z)
for f, p in ((1, 0.0), (36, 0.05), (72, 0.0)):
    kfa('chest', f, p, 'fwd')
tail_wag(1, 72, period=18, amp=0.22)
for f, p in ((1, 0.0), (36, 0.09), (72, 0.0)):
    kfa('earA', f, p)
end('Idle')

# --- Sit: попа на землю, корпус вверх, взгляд ровный (60f)
# Пивот (Hips) в центре тела: перед поднимается на BODY_LEN*sin(T),
# попа сама не опускается — её сажает root-drop. Drop чуть больше подъёма
# плеч, чтобы попа дошла до земли, а лапы остались на месте.
SIT_T = 0.55
SIT_DROP = BODY_LEN * math.sin(SIT_T) + 0.012  # по замеру лапы
begin(60)
for k in ('rA0', 'rB0'):
    kfa(k, 1, 0.0, 'fwd')
    kfa(k, 16, 0.7, 'fwd')
    kfa(k, 60, 0.7, 'fwd')
for k in ('rA1', 'rB1'):
    kfa(k, 1, 0.0, 'fwd')
    kfa(k, 16, -1.2, 'fwd')
    kfa(k, 60, -1.2, 'fwd')
kfl('root', 1, 0.0)
kfl('root', 16, -SIT_DROP)
kfl('root', 60, -SIT_DROP)
kfa('hips', 1, 0.0)
kfa('hips', 16, -SIT_T)
kfa('hips', 60, -SIT_T)
for k in ('fA0', 'fB0'):
    kfa(k, 1, 0.0, 'fwd')
    kfa(k, 16, -SIT_T, 'fwd')
    kfa(k, 60, -SIT_T, 'fwd')
kfa('head', 1, 0.0, 'fwd')
kfa('head', 16, SIT_T * 0.8, 'fwd')
kfa('head', 60, SIT_T * 0.8, 'fwd')
kf('head', 16, axis=AX['head']['side'][0],
   angle=0.12 * AX['head']['side'][1])
tail_wag(20, 60, period=14, amp=0.3)
end('Sit')

# --- Happy: подпрыгивания + быстрый хвост + уши (48f loop)
begin(48)
for f, z in ((1, 0.0), (8, 0.035 * L), (14, 0.0), (22, 0.035 * L), (28, 0.0),
             (36, 0.02 * L), (48, 0.0)):
    kfl('root', f, z)
kfa('head', 1, -0.12, 'fwd')
kfa('head', 48, -0.12, 'fwd')
tail_wag(1, 48, period=6, amp=0.5)
for f, p in ((1, 0.0), (8, -0.2), (14, 0.06), (22, -0.2), (28, 0.0), (48, 0.0)):
    kfa('earA', f, p)
    kfa('earB', f, p)
end('Happy')

# --- Sad: голова вниз, уши повисли, хвост опущен (72f loop)
begin(72)
for f in (1, 72):
    kfa('chest', f, 0.12, 'fwd')
    kfa('head', f, 0.5, 'fwd')
    kfa('earA', f, 0.45)
    kfa('earB', f, 0.45)
    kfa('tail1', f, 0.5)
    kfa('tail2', f, 0.35)
    kfl('root', f, -0.01 * L)
kfa('head', 36, 0.56, 'fwd')
end('Sad')

# --- Curious: наклон головы вбок, ухо торчком (60f loop)
begin(60)
kfa('head', 1, 0.0, 'side')
kfa('head', 18, 0.32, 'side')
kfa('head', 42, -0.26, 'side')
kfa('head', 60, 0.0, 'side')
kfa('earA', 1, 0.0)
kfa('earA', 18, -0.3)
kfa('earA', 60, 0.0)
tail_wag(1, 60, period=16, amp=0.25)
end('Curious')

# --- Sniff: нос к земле, принюхивается (60f)
begin(60)
kfa('chest', 1, 0.0, 'fwd')
kfa('chest', 14, 0.22, 'fwd')
kfa('chest', 50, 0.22, 'fwd')
kfa('chest', 60, 0.03, 'fwd')
kfa('head', 1, 0.0, 'fwd')
kfa('head', 14, 0.62, 'fwd')
for f, p in ((20, 0.5), (25, 0.68), (30, 0.5), (35, 0.68), (40, 0.5)):
    kfa('head', f, p, 'fwd')
kfa('head', 60, 0.05, 'fwd')
tail_wag(1, 60, period=12, amp=0.2)
end('Sniff')

# --- Bark: мягкое "гав" (48f)
begin(48)
for f, p in ((1, 0.0), (10, -0.22), (14, 0.14), (18, -0.18), (22, 0.1),
             (30, 0.0), (48, 0.0)):
    kfa('head', f, p, 'fwd')
for f, z in ((1, 0.0), (10, -0.008 * L), (14, 0.005 * L), (22, 0.0)):
    kfl('root', f, z)
tail_wag(1, 48, period=10, amp=0.3)
end('Bark')

# --- TailWag: активное виляние + попа (48f loop)
begin(48)
tail_wag(1, 48, period=5, amp=0.6)
f = 1
s = 1
while f <= 48:
    kfa('hips', f, 0.06 * s, 'side')
    s = -s
    f += 10
end('TailWag')

# --- Jump: присед -> прыжок -> приземление (36f)
begin(36)
for f, z in ((1, 0.0), (8, -0.03 * L), (14, 0.09 * L), (20, 0.1 * L),
             (26, 0.0), (30, -0.012 * L), (36, 0.0)):
    kfl('root', f, z)
for k in ('fA0', 'fB0'):
    kfa(k, 1, 0.0, 'fwd')
    kfa(k, 8, -0.2, 'fwd')
    kfa(k, 16, 0.45, 'fwd')
    kfa(k, 26, 0.0, 'fwd')
for k in ('rA0', 'rB0'):
    kfa(k, 1, 0.0, 'fwd')
    kfa(k, 8, 0.25, 'fwd')
    kfa(k, 16, -0.35, 'fwd')
    kfa(k, 26, 0.0, 'fwd')
kfa('head', 8, 0.1, 'fwd')
kfa('head', 16, -0.14, 'fwd')
kfa('head', 26, 0.0, 'fwd')
tail_wag(1, 36, period=9, amp=0.3)
end('Jump')

reset_pose()

# ------------------------------------------------------------- верификация
def clip_probe(clip, frame, key):
    act = bpy.data.actions[f'S2_{clip}']
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
sad_head = clip_probe('Sad', 36, 'head')
print(f'[verify] Sad head bow: {(sad_head - rest_head).length / S_W:.3f}S -> '
      f'{"OK" if (sad_head - rest_head).length > 0.1 * S_W and sad_head.z < rest_head.z else "FAIL"}')
rest_paw = tail_world_pose('fA1')
walk_paw = clip_probe('Walk', 7, 'fA1')
print(f'[verify] Walk paw swing: {(walk_paw - rest_paw).length / S_W:.3f}S -> '
      f'{"OK" if (walk_paw - rest_paw).length > 0.03 * S_W else "FAIL"}')
sit_paw = clip_probe('Sit', 40, 'fA1')
print(f'[verify] Sit front paw dz: {(sit_paw.z - rest_paw.z) / S_W:+.3f}S -> '
      f'{"OK" if abs(sit_paw.z - rest_paw.z) < 0.06 * S_W else "FAIL"}')
rest_tail = tail_world_pose('tail3')
wag_tail = clip_probe('TailWag', 6, 'tail3')
print(f'[verify] TailWag swing dx: {abs(wag_tail.x - rest_tail.x) / S_W:.3f}S -> '
      f'{"OK" if abs(wag_tail.x - rest_tail.x) > 0.05 * S_W else "FAIL"}')

# --------------------------------------- материал: чуть светящийся, тёплый
for mat in dog.data.materials:
    if not mat or not mat.use_nodes:
        continue
    pr = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if pr is None:
        continue
    pr.inputs['Roughness'].default_value = 0.7
    if 'Metallic' in pr.inputs:
        pr.inputs['Metallic'].default_value = 0.0
    base_link = pr.inputs['Base Color'].links
    if base_link and 'Emission Color' in pr.inputs:
        src_sock = base_link[0].from_socket
        mat.node_tree.links.new(src_sock, pr.inputs['Emission Color'])
        pr.inputs['Emission Strength'].default_value = 0.07
        print('[mat] emissive lift 0.07 on', mat.name)

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
    )
    print('[export] wrote', OUT, os.path.getsize(OUT), 'bytes')
    with open(OUT, 'rb') as fh:
        buf = fh.read()
    json_len = struct.unpack_from('<I', buf, 12)[0]
    gltf = jsonlib.loads(buf[20:20 + json_len].decode())
    anims = [a.get('name') for a in gltf.get('animations', [])]
    print('[glb] animations:', ', '.join(anims))
    print('[glb] missing:', [c for c in CLIP_NAMES if c not in anims] or 'none')

    for tr in arm.animation_data.nla_tracks:
        tr.mute = True
    bpy.ops.object.light_add(type='SUN', location=(2, -3, 4))
    bpy.context.active_object.data.energy = 3
    world = bpy.data.worlds.new('W') if not bpy.data.worlds else bpy.data.worlds[0]
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (0.88, 0.9, 0.93, 1)
    center = Vector((0, 0, S_W * 0.45))
    bpy.ops.object.empty_add(location=center)
    target = bpy.context.active_object
    bpy.ops.object.camera_add(
        location=(2.2 * S_W, FACE * 2.6 * S_W, 0.8 * S_W))
    cam = bpy.context.active_object
    cam.data.clip_start = S_W * 0.01
    cam.constraints.new('TRACK_TO').target = target
    scene.camera = cam
    for engine in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH'):
        try:
            scene.render.engine = engine
            break
        except Exception:
            continue
    try:
        scene.view_settings.view_transform = 'Standard'
    except Exception:
        pass
    scene.render.resolution_x = 700
    scene.render.resolution_y = 700
    scene.render.image_settings.file_format = 'PNG'

    def render_pose(label, clip, frame):
        if clip:
            act = bpy.data.actions[f'S2_{clip}']
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

    for label, clip, frame in (('rest', None, 1), ('walk', 'Walk', 7),
                               ('sit', 'Sit', 40), ('sad', 'Sad', 36)):
        render_pose(label, clip, frame)
    print('[preview] wrote', OUT_PREVIEW.replace('.png', '_*.png'))
