"""Sophie (Tripo) — анимация на родном риге + экспорт sophie.glb.

Вход:  public/assets/sophie_tripo.glb (стоячая, с ригом Tripo, без анимаций)
Выход: public/assets/sophie.glb (та же модель + 10 клипов: Idle, Walk, Run,
       Sit, Happy, Sad, Curious, Sniff, Bark, TailWag)

Запуск (headless, экспорт + превью):
  /Applications/Blender.app/Contents/MacOS/Blender --background --python tools/blender/build_sophie_anim.py

В GUI (посмотреть клипы): Text -> Open -> Run Script; затем выбрать
арматуру -> NLA -> solo трека -> Play.

Оси у костей рига Tripo с произвольными ролами, поэтому для каждой кости
автоматически подбирается ось (X или Z), реально дающая наклон вниз /
вбок / вперёд (_probe + axes_for). Все движения намеренно мягкие и
медленные (safety-правила игры).
"""

import math
import os
import struct
import json as jsonlib

import bpy
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'public', 'assets', 'sophie_tripo.glb')
OUT = os.path.join(ROOT, 'public', 'assets', 'sophie.glb')
OUT_PREVIEW = os.path.join(ROOT, 'tools', 'blender', 'preview_sophie_anim.png')
HEADLESS = bpy.app.background

CLIP_NAMES = ['Idle', 'Walk', 'Run', 'Sit', 'Happy', 'Sad', 'Curious',
              'Sniff', 'Bark', 'TailWag']

if HEADLESS:
    bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 24

bpy.ops.import_scene.gltf(filepath=SRC)

arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
dog = max(meshes, key=lambda o: len(o.data.vertices))
for o in meshes:
    if o is not dog:  # мусорный Icosphere из экспорта Tripo
        print('[clean] removing stray mesh:', o.name)
        bpy.data.objects.remove(o, do_unlink=True)
assert len(dog.vertex_groups) > 10, 'у меша нет весов рига Tripo'

# ------------------------------------------------- нормализация ориентации
# transform_apply в headless тихо фейлится -> запекаем матрицы напрямую
# через data API (Mesh.transform / Armature.transform), без ops.
from mathutils import Matrix


def bake_world_transform(obj):
    mw = obj.matrix_world.copy()
    obj.data.transform(mw)
    obj.matrix_world = Matrix.Identity(4)


_mw = dog.matrix_world.copy()
dog.parent = None
dog.matrix_world = _mw
for o in (arm, dog):
    bake_world_transform(o)
bpy.context.view_layer.update()

BONES = {
    'root': 'tripo::Root',
    'hip': 'tripo::0_Right_Limb_0',
    'chest': 'tripo::Head_0',
    'neck': 'tripo::Spine_0',
    'neck2': 'bone_14',
    'head': 'bone_15',
    'earA': 'bone_16',
    'earB': 'bone_17',
    'snout': 'bone_18',
    'tail1': 'bone_10',
    'tail2': 'tripo::Tail_0',
    'frontA0': 'tripo::1_Left_Limb_0', 'frontA1': 'tripo::1_Left_Limb_1',
    'frontB0': 'tripo::0_Left_Limb_0', 'frontB1': 'tripo::0_Left_Limb_1',
    'rearA0': 'tripo::0_Right_Limb_1', 'rearA1': 'tripo::0_Right_Limb_2',
    'rearB0': 'bone_6', 'rearB1': 'bone_7',
}
for key, name in BONES.items():
    assert name in arm.data.bones, f'нет кости {name} ({key}) — риг Tripo изменился'


def bone_world(key, point='head'):
    b = arm.data.bones[BONES[key]]
    v = b.head_local if point == 'head' else b.tail_local
    return (arm.matrix_world @ v).copy()


# Морду в +Y (наша конвенция; движок делает финальный флип на 180°).
# Поворачиваем ОБА объекта согласованно и запекаем через data API.
face_dir = (bone_world('snout') - bone_world('tail1'))
face_dir.z = 0
face_dir.normalize()
angle = math.atan2(face_dir.x, face_dir.y)
# Rz(theta) сводит азимут theta к нулю (+Y); знак БЕЗ минуса.
rot = Matrix.Rotation(angle, 4, 'Z')
for o in (arm, dog):
    o.data.transform(rot)
bpy.context.view_layer.update()
front_y = bone_world('snout').y
tail_y = bone_world('tail1').y
print(f'[orient] повернул на {math.degrees(angle):.0f}°; '
      f'front y={front_y:.2f} tail y={tail_y:.2f} -> '
      f'{"OK (морда в +Y)" if front_y > tail_y else "FAIL"}')

# ------------------------------------------------------- перевес скина
# Авто-скин Tripo фиктивный: ~100% весов на Root (кости машут — шкура
# стоит). Bone-heat в headless тихо фейлится, поэтому вешаем сами:
# расстояние вершины до сегмента кости, топ-3 кости, штраф за
# "чужую сторону" для костей лап (чтобы лапы не перехватывали
# веса друг друга).
from mathutils.geometry import intersect_point_line

for vg in list(dog.vertex_groups):
    dog.vertex_groups.remove(vg)
for m in list(dog.modifiers):
    if m.type == 'ARMATURE':
        dog.modifiers.remove(m)

segments = []  # (bone_name, head, tail, is_leg, side_sign)
for b in arm.data.bones:
    if b.name == 'tripo::Root':
        continue
    h = b.head_local.copy()
    t = b.tail_local.copy()
    is_leg = max(h.z, t.z) < 0.45 and abs((h.x + t.x) / 2) > 0.04
    side = 1.0 if (h.x + t.x) / 2 >= 0 else -1.0
    segments.append((b.name, h, t, is_leg, side))

groups = {name: dog.vertex_groups.new(name=name) for name, *_ in segments}


def seg_dist(p, a, b):
    pt, frac = intersect_point_line(p, a, b)
    frac = max(0.0, min(1.0, frac))
    closest = a.lerp(b, frac)
    return (p - closest).length


for i, v in enumerate(dog.data.vertices):
    co = v.co
    cands = []
    for name, h, t, is_leg, side in segments:
        d = seg_dist(co, h, t)
        if is_leg and co.x * side < -0.01:
            d *= 1.9  # чужая сторона
        cands.append((d, name))
    cands.sort()
    top = cands[:3]
    ws = [(1.0 / (d + 0.025)) ** 2 for d, _ in top]
    total = sum(ws)
    for (d, name), w in zip(top, ws):
        wn = w / total
        if wn > 0.06:
            groups[name].add([i], wn, 'REPLACE')

mod = dog.modifiers.new('Armature', 'ARMATURE')
mod.object = arm
dog.parent = arm

_totals = {}
for v in dog.data.vertices:
    for gr in v.groups:
        nm = dog.vertex_groups[gr.group].name
        _totals[nm] = _totals.get(nm, 0.0) + gr.weight
_top = sorted(_totals.items(), key=lambda kv: -kv[1])[:6]
print('[skin] groups:', len(_totals), 'top:',
      ', '.join(f'{n}={t:.0f}' for n, t in _top))
assert len(_totals) > 12, 'перевес скина не удался'

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
    """Какая локальная ось кости (X=0 / Z=2) реально качает её вниз (pitch),
    вбок (side), вперёд (fwd) — ролы у рига Tripo произвольные."""
    dx = _probe(key, 0)
    dz = _probe(key, 2)
    down = Vector((0, 0, -1))
    side = Vector((1, 0, 0))
    fwd = Vector((0, 1, 0))
    if abs(dx.dot(down)) >= abs(dz.dot(down)):
        pitch = (0, 1.0 if dx.dot(down) > 0 else -1.0)
        side_ax = (2, 1.0 if dz.dot(side) > 0 else -1.0)
    else:
        pitch = (2, 1.0 if dz.dot(down) > 0 else -1.0)
        side_ax = (0, 1.0 if dx.dot(side) > 0 else -1.0)
    if abs(dx.dot(fwd)) >= abs(dz.dot(fwd)):
        fwd_ax = (0, 1.0 if dx.dot(fwd) > 0 else -1.0)
    else:
        fwd_ax = (2, 1.0 if dz.dot(fwd) > 0 else -1.0)
    return {'pitch': pitch, 'side': side_ax, 'fwd': fwd_ax}


AX = {}
for _k in ('head', 'neck2', 'earA', 'earB', 'tail1', 'tail2', 'hip',
           'frontA0', 'frontA1', 'frontB0', 'frontB1',
           'rearA0', 'rearA1', 'rearB0', 'rearB1'):
    AX[_k] = axes_for(_k)
print('[axes] head:', AX['head'], 'tail1:', AX['tail1'],
      'frontA0:', AX['frontA0'])

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
    """Кейфрейм по автоопределённой оси (pitch=вниз+, side=вбок+, fwd=вперёд+)."""
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
    act.name = f'SP_{name}'
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
    kfa('neck2', f, p)
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
    kfa('head', f, p)
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

# --- Sit: садится и сидит, хвост медленно (60f)
begin(60)
for k in ('rearA0', 'rearB0'):
    kfa(k, 1, 0.0, 'fwd')
    kfa(k, 16, 1.15, 'fwd')
    kfa(k, 60, 1.15, 'fwd')
for k in ('rearA1', 'rearB1'):
    kfa(k, 1, 0.0, 'fwd')
    kfa(k, 16, -0.9, 'fwd')
    kfa(k, 60, -0.9, 'fwd')
kf('root', 1, loc=(0, 0, 0))
kf('root', 16, loc=(0, 0, -0.09))
kf('root', 60, loc=(0, 0, -0.09))
kfa('hip', 1, 0.0)
kfa('hip', 16, -0.35)
kfa('hip', 60, -0.35)
kfa('neck2', 1, 0.0)
kfa('neck2', 16, -0.12)
kfa('neck2', 60, -0.12)
tail_wag(20, 60, period=14, amp=0.3)
end('Sit')

# --- Happy: подпрыгивания + быстрый хвост + уши (48f loop)
begin(48)
for f, z in ((1, 0.0), (8, 0.05), (14, 0.0), (22, 0.05), (28, 0.0),
             (36, 0.03), (48, 0.0)):
    kf('root', f, loc=(0, 0, z))
kfa('neck2', 1, -0.14)
kfa('neck2', 48, -0.14)
tail_wag(1, 48, period=6, amp=0.5)
for f, p in ((1, 0.0), (8, -0.18), (14, 0.06), (22, -0.18), (28, 0.0), (48, 0.0)):
    kfa('earA', f, p)
    kfa('earB', f, p)
end('Happy')

# --- Sad: голова вниз, уши повисли, хвост опущен (72f loop)
begin(72)
for f in (1, 72):
    kfa('neck2', f, 0.35)
    kfa('head', f, 0.38)
    kfa('earA', f, 0.4)
    kfa('earB', f, 0.4)
    kfa('tail1', f, -0.35)
    kf('root', f, loc=(0, 0, -0.015))
kfa('head', 36, 0.43)
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
kfa('neck2', 1, -0.06)
kfa('neck2', 60, -0.06)
tail_wag(1, 60, period=16, amp=0.25)
end('Curious')

# --- Sniff: нос к земле, мелкие принюхивания (60f)
begin(60)
kfa('neck2', 1, 0.0)
kfa('neck2', 14, 0.55)
kfa('neck2', 50, 0.55)
kfa('neck2', 60, 0.1)
kfa('head', 1, 0.0)
kfa('head', 14, 0.4)
for f, p in ((20, 0.3), (25, 0.45), (30, 0.3), (35, 0.45), (40, 0.3)):
    kfa('head', f, p)
kfa('head', 60, 0.05)
tail_wag(1, 60, period=12, amp=0.2)
end('Sniff')

# --- Bark: мягкое "гав" — без агрессии (48f)
begin(48)
for f, p in ((1, 0.0), (10, -0.2), (14, 0.12), (18, -0.16), (22, 0.1),
             (30, 0.0), (48, 0.0)):
    kfa('head', f, p)
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
kfa('neck2', 1, -0.07)
kfa('neck2', 48, -0.07)
end('TailWag')

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
sad_head = clip_probe('SP_Sad', 36, 'head')
sad_move = (sad_head - rest_head).length  # поклон = вперёд-вниз, мерим модуль
print(f'[verify] Sad head bow: {sad_move:.3f} '
      f'(dz={rest_head.z - sad_head.z:.3f}) -> '
      f'{"OK" if sad_move > 0.08 and sad_head.z <= rest_head.z else "FAIL"}')
rest_foot = tail_world_pose('frontA1')
walk_foot = clip_probe('SP_Walk', 13, 'frontA1')
print(f'[verify] Walk foot swing: {(walk_foot - rest_foot).length:.3f} -> '
      f'{"OK" if (walk_foot - rest_foot).length > 0.05 else "FAIL"}')


def mesh_leg_disp(clip, frame):
    """Максимальное смещение вершин МЕША в зоне лап (низ) — истинная
    проверка, что шкура следует за костями."""
    def sample():
        dg = bpy.context.evaluated_depsgraph_get()
        ev = dog.evaluated_get(dg).to_mesh()
        pts = [(i, v.co.copy()) for i, v in enumerate(ev.data.vertices)
               if v.co.z < 0.30] if hasattr(ev, 'data') else \
              [(i, v.co.copy()) for i, v in enumerate(ev.vertices)
               if v.co.z < 0.30]
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


leg_disp = mesh_leg_disp('SP_Walk', 13)
print(f'[verify] Walk MESH leg displacement: {leg_disp:.3f} -> '
      f'{"OK" if leg_disp > 0.05 else "FAIL"}')

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

    for track in arm.animation_data.nla_tracks:
        track.mute = True
    bpy.ops.object.light_add(type='SUN', location=(2, -3, 4))
    bpy.context.active_object.data.energy = 3
    world = bpy.data.worlds.new('W') if not bpy.data.worlds else bpy.data.worlds[0]
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (0.88, 0.90, 0.94, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = 0.9
    bpy.ops.object.empty_add(location=(0, 0, 0.45))
    target = bpy.context.active_object
    bpy.ops.object.camera_add(location=(1.5, -1.7, 1.1))
    cam = bpy.context.active_object
    cam.constraints.new('TRACK_TO').target = target
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

    for label, clip, frame in (('rest', None, 1), ('sad', 'SP_Sad', 36),
                               ('sit', 'SP_Sit', 40), ('walk', 'SP_Walk', 13)):
        render_pose(label, clip, frame)
    print('[preview] wrote', OUT_PREVIEW.replace('.png', '_*.png'))
else:
    for track in arm.animation_data.nla_tracks:
        track.mute = True
    reset_pose()
    print('Клипы готовы: выбери арматуру -> NLA -> solo -> Play.')
