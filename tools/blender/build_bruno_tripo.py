"""Эксперимент: Tripo-меш Бруно + мой риг + мои клипы.

Вход:  public/assets/bruno_tripo.glb (статичный меш из Tripo)
Выход: public/assets/bruno_tripo_rigged.glb + превью-рендеры ключевых поз
       tools/blender/preview_btr_*.png (позы ставятся напрямую, минуя
       анимационную систему — чтобы честно увидеть растяжения скина).

Запуск: /Applications/Blender.app/Contents/MacOS/Blender --background --python tools/blender/build_bruno_tripo.py
"""

import math
import os
import struct
import json as jsonlib

import bpy
from mathutils import Matrix, Vector
from mathutils.geometry import intersect_point_line

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'public', 'assets', 'bruno_tripo.glb')
OUT = os.path.join(ROOT, 'public', 'assets', 'bruno_tripo_rigged.glb')
PREVIEW = os.path.join(ROOT, 'tools', 'blender', 'preview_btr.png')

CLIP_NAMES = ['IdleSad', 'IdleOpen', 'Walk', 'HandToChest', 'SmallWave',
              'SitAlone', 'TryJoinClumsy', 'TryAgainSucceed', 'PlayIncluded']

# Морда Tripo-персонажей обычно в glTF +Z -> Blender -Y; наша конвенция +Y.
# Если на превью окажется затылком — поменять на 0.0 и перезапустить.
YAW_FIX = math.pi

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 24

bpy.ops.import_scene.gltf(filepath=SRC)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
body = max(meshes, key=lambda o: len(o.data.vertices))
for o in list(bpy.data.objects):
    if o is not body:
        bpy.data.objects.remove(o, do_unlink=True)


def bake(obj, extra=None):
    mw = obj.matrix_world.copy()
    if extra is not None:
        mw = extra @ mw
    obj.data.transform(mw)
    obj.matrix_world = Matrix.Identity(4)


bake(body, Matrix.Rotation(YAW_FIX, 4, 'Z'))
bpy.context.view_layer.update()

# ------------------------------------------------ обмер меша под скелет
xs = [v.co.x for v in body.data.vertices]
zs = [v.co.z for v in body.data.vertices]
H = max(zs)
low_x = [abs(v.co.x) for v in body.data.vertices if v.co.z < 0.15 * H]
leg_x = (sum(low_x) / len(low_x)) if low_x else 0.1
mid_x = max(abs(v.co.x) for v in body.data.vertices
            if 0.45 * H < v.co.z < 0.65 * H)
print(f'[measure] H={H:.2f} leg_x~{leg_x:.2f} shoulder_span~{mid_x:.2f}')

# островки (для оценки гибридного пути)
_islands_probe = body.copy()
_islands_probe.data = body.data.copy()
bpy.context.scene.collection.objects.link(_islands_probe)
bpy.ops.object.select_all(action='DESELECT')
_islands_probe.select_set(True)
bpy.context.view_layer.objects.active = _islands_probe
bpy.ops.mesh.separate(type='LOOSE')
parts = [o for o in bpy.data.objects if o.name.startswith(_islands_probe.name)]
print(f'[islands] loose parts: {len(parts)} '
      f'({", ".join(str(len(p.data.vertices)) for p in parts[:8])})')
for p in parts:
    bpy.data.objects.remove(p, do_unlink=True)

# ------------------------------------------------------------------- риг
SH_X = mid_x * 0.62         # плечо
SH_Z = 0.60 * H
HAND_Z = 0.16 * H
LEG_X = max(leg_x, 0.06)
bpy.ops.object.armature_add(location=(0, 0, 0))
arm = bpy.context.active_object
arm.name = 'BrunoTripo_Rig'
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones
eb.remove(eb[0])
BONES = {
    'root': ((0, 0, 0.02 * H), (0, 0, 0.22 * H), None),
    'spine': ((0, 0, 0.22 * H), (0, 0, 0.58 * H), 'root'),
    'head': ((0, 0, 0.58 * H), (0, 0, 0.96 * H), 'spine'),
    'arm.L': ((SH_X, 0, SH_Z), (SH_X + 0.07 * H, 0, HAND_Z), 'spine'),
    'arm.R': ((-SH_X, 0, SH_Z), (-SH_X - 0.07 * H, 0, HAND_Z), 'spine'),
    'leg.L': ((LEG_X, 0, 0.22 * H), (LEG_X, 0, 0.02 * H), 'root'),
    'leg.R': ((-LEG_X, 0, 0.22 * H), (-LEG_X, 0, 0.02 * H), 'root'),
}
created = {}
for name, (h, t, parent) in BONES.items():
    b = eb.new(name)
    b.head = h
    b.tail = t
    b.roll = 0
    if parent:
        b.parent = created[parent]
    created[name] = b
bpy.ops.object.mode_set(mode='OBJECT')

# ------------------------------------------------------ дистанционный скин
segments = []
for b in arm.data.bones:
    h = b.head_local.copy()
    t = b.tail_local.copy()
    kind = ('arm' if b.name.startswith('arm') else
            'leg' if b.name.startswith('leg') else 'core')
    side = 1.0 if (h.x + t.x) / 2 >= 0 else -1.0
    segments.append((b.name, h, t, kind, side))
groups = {name: body.vertex_groups.new(name=name) for name, *_ in segments}


def seg_dist(p, a, b):
    _pt, frac = intersect_point_line(p, a, b)
    frac = max(0.0, min(1.0, frac))
    return (p - a.lerp(b, frac)).length


HEAD_Z = 0.64 * H    # выше — только голова (кепка целиком, уши, глаз)
SHOE_Z = 0.13 * H    # ниже — только ноги (кеды)
ARM_TUBE = 0.062 * H  # радиус "трубки" руки: внутри — рука, снаружи — нет
ARM_BAN = 0.105 * H

for i, v in enumerate(body.data.vertices):
    co = v.co
    if co.z > HEAD_Z:
        groups['head'].add([i], 1.0, 'REPLACE')
        continue
    if co.z < SHOE_Z:
        groups['leg.L' if co.x >= 0 else 'leg.R'].add([i], 1.0, 'REPLACE')
        continue
    cands = []
    for name, h, t, kind, side in segments:
        d = seg_dist(co, h, t)
        if kind == 'arm':
            if co.x * side < -0.005 or co.z < SHOE_Z + 0.05 * H:
                d *= 8.0
            elif d < ARM_TUBE:
                d *= 0.3          # внутри трубки рука доминирует
            elif d > ARM_BAN:
                d *= 8.0          # снаружи — тело не утаскивается
        if kind == 'leg':
            if co.x * side < -0.005:
                d *= 2.2
            if co.z > 0.35 * H:
                d *= 6.0
        cands.append((d, name))
    cands.sort()
    top = cands[:3]
    ws = [(1.0 / (d + 0.02 * H)) ** 2 for d, _ in top]
    total = sum(ws)
    for (d, name), w in zip(top, ws):
        wn = w / total
        if wn > 0.05:
            groups[name].add([i], wn, 'REPLACE')

mod = body.modifiers.new('Armature', 'ARMATURE')
mod.object = arm
body.parent = arm

for pb in arm.pose.bones:
    pb.rotation_mode = 'XYZ'

# ------------------------------------------------ оси/знаки и хелперы клипов
def reset_pose():
    for pb in arm.pose.bones:
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)


def tail_world_pose(key):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    eo = arm.evaluated_get(dg)
    return (eo.matrix_world @ eo.pose.bones[key].tail).copy()


def _probe(key, axis, amount=0.35):
    reset_pose()
    rest = tail_world_pose(key)
    e = [0.0, 0.0, 0.0]
    e[axis] = amount
    arm.pose.bones[key].rotation_euler = e
    moved = tail_world_pose(key)
    reset_pose()
    return moved - rest


def axes_for(key):
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


AX = {k: axes_for(k) for k in BONES}

arm.animation_data_create()


def set_axis(key, angle, mode='pitch'):
    axis, s = AX[key][mode]
    e = list(arm.pose.bones[key].rotation_euler)
    e[axis] = angle * s
    arm.pose.bones[key].rotation_euler = e


def kfa(key, frame, angle, mode='pitch'):
    set_axis(key, angle, mode)
    arm.pose.bones[key].keyframe_insert('rotation_euler', frame=frame)


def kfloc(key, frame, dz):
    pb = arm.pose.bones[key]
    pb.location = (0, dz, 0) if key == 'root' else (0, 0, dz)
    pb.keyframe_insert('location', frame=frame)


def begin(last):
    reset_pose()
    arm.animation_data.action = None
    scene.frame_start = 1
    scene.frame_end = last


def end(name):
    act = arm.animation_data.action
    act.name = f'BT_{name}'
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


S = H / 2.5  # масштаб смещений (мой процедурный был высотой ~2.5)

begin(72)
for f in (1, 72):
    kfa('spine', f, 0.16)
    kfloc('root', f, -0.03 * S)
    kfa('arm.L', f, -0.10, 'side')
    kfa('arm.R', f, 0.10, 'side')
kfa('head', 1, 0.38)
kfa('head', 36, 0.44)
kfa('head', 72, 0.38)
end('IdleSad')

begin(72)
kfa('head', 1, -0.06)
kfa('head', 72, -0.06)
kfa('spine', 1, -0.04)
kfa('spine', 36, -0.04)
kfa('spine', 72, -0.04)
kfa('arm.L', 1, 0.10, 'side')
kfa('arm.R', 1, -0.10, 'side')
kfa('arm.L', 72, 0.10, 'side')
kfa('arm.R', 72, -0.10, 'side')
end('IdleOpen')

begin(24)
for f, a in ((1, 0.45), (13, -0.45), (24, 0.45)):
    kfa('leg.L', f, a, 'fwd')
    kfa('leg.R', f, -a, 'fwd')
    kfa('arm.L', f, -a * 0.35, 'fwd')
    kfa('arm.R', f, a * 0.35, 'fwd')
for f, z in ((1, -0.015), (7, 0.02), (13, -0.015), (19, 0.02), (24, -0.015)):
    kfloc('root', f, z * S)
kfa('spine', 1, 0.05)
kfa('spine', 24, 0.05)
end('Walk')

begin(48)
kfa('arm.R', 1, 0.0, 'fwd')
kfa('arm.R', 16, 0.85, 'fwd')
kfa('arm.R', 48, 0.85, 'fwd')
kfa('head', 1, 0.30)
kfa('head', 28, 0.10)
kfa('head', 48, 0.10)
kfa('spine', 1, 0.12)
kfa('spine', 48, 0.10)
end('HandToChest')

begin(48)
kfa('arm.R', 1, 0.0, 'fwd')
kfa('arm.R', 10, 0.9, 'fwd')
for f, r in ((16, 0.25), (24, -0.25), (32, 0.25), (40, 0.0)):
    set_axis('arm.R', 0.9, 'fwd')
    kfa('arm.R', f, r, 'side')
kfa('arm.R', 48, 0.5, 'fwd')
kfa('head', 1, 0.05)
kfa('head', 20, -0.05)
kfa('head', 48, 0.0)
end('SmallWave')

begin(60)
for f in (1, 60):
    kfloc('root', f, -0.32 * S)
    kfa('leg.L', f, 1.4, 'fwd')
    kfa('leg.R', f, 1.4, 'fwd')
    kfa('spine', f, 0.22)
kfa('head', 1, 0.34)
kfa('head', 30, 0.40)
kfa('head', 60, 0.34)
end('SitAlone')

begin(60)
kfa('spine', 1, 0.10)
kfa('spine', 16, 0.22)
for f, r in ((24, 0.12), (32, -0.12), (40, 0.06)):
    set_axis('spine', 0.18)
    kfa('spine', f, r, 'side')
kfloc('root', 1, 0.0)
kfloc('root', 30, -0.06 * S)
kfloc('root', 46, 0.0)
kfa('spine', 60, 0.08)
kfa('head', 1, 0.0)
kfa('head', 30, 0.15)
kfa('head', 60, 0.05)
end('TryJoinClumsy')

begin(60)
kfa('spine', 1, 0.15)
kfa('spine', 30, 0.05)
kfa('spine', 60, 0.02)
kfa('arm.L', 40, 0.35, 'side')
kfa('arm.R', 40, -0.35, 'side')
kfa('arm.L', 60, 0.30, 'side')
kfa('arm.R', 60, -0.30, 'side')
kfa('head', 1, 0.15)
kfa('head', 45, -0.10)
kfa('head', 60, -0.10)
end('TryAgainSucceed')

begin(48)
for f, z in ((1, 0.0), (12, 0.06), (24, 0.0), (36, 0.06), (48, 0.0)):
    kfloc('root', f, z * S)
for f, a in ((1, 0.25), (24, -0.25), (48, 0.25)):
    kfa('arm.L', f, a, 'fwd')
    kfa('arm.R', f, -a, 'fwd')
for f, r in ((1, 0.06), (24, -0.06), (48, 0.06)):
    kfa('head', f, r, 'side')
kfa('spine', 1, -0.03)
kfa('spine', 48, -0.03)
end('PlayIncluded')

reset_pose()

# --------------------------------------------------------------- экспорт
for o in bpy.data.objects:
    o.select_set(o in (arm, body))
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.gltf(
    filepath=OUT,
    export_format='GLB',
    use_selection=True,
    export_apply=False,
    export_animation_mode='NLA_TRACKS',
    export_skins=True,
)
print('[export]', OUT, os.path.getsize(OUT), 'bytes')
with open(OUT, 'rb') as fh:
    buf = fh.read()
json_len = struct.unpack_from('<I', buf, 12)[0]
gltf = jsonlib.loads(buf[20:20 + json_len].decode())
anims = [a.get('name') for a in gltf.get('animations', [])]
print('[glb] animations:', ', '.join(anims))
print('[glb] missing:', [c for c in CLIP_NAMES if c not in anims] or 'none')

# ------------------------------------------ превью поз (напрямую, без анимации)
for track in arm.animation_data.nla_tracks:
    track.mute = True

bpy.ops.object.light_add(type='SUN', location=(2, -3, 4))
bpy.context.active_object.data.energy = 3
world = bpy.data.worlds.new('W') if not bpy.data.worlds else bpy.data.worlds[0]
scene.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (0.88, 0.90, 0.94, 1)
world.node_tree.nodes['Background'].inputs[1].default_value = 0.85
bpy.ops.object.empty_add(location=(0, 0, 0.5 * H))
target = bpy.context.active_object
bpy.ops.object.camera_add(location=(1.4 * H, 1.9 * H, 1.1 * H))
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
scene.render.resolution_y = 900
scene.render.image_settings.file_format = 'PNG'


def render_pose(label, setup):
    reset_pose()
    setup()
    bpy.context.view_layer.update()
    scene.render.filepath = PREVIEW.replace('.png', f'_{label}.png')
    bpy.ops.render.render(write_still=True)


render_pose('rest', lambda: None)
render_pose('idlesad', lambda: (set_axis('spine', 0.19), set_axis('head', 0.44),
                                set_axis('arm.L', -0.10, 'side'),
                                set_axis('arm.R', 0.10, 'side')))
render_pose('wave', lambda: set_axis('arm.R', 0.9, 'fwd'))
render_pose('walk', lambda: (set_axis('leg.L', 0.45, 'fwd'),
                             set_axis('leg.R', -0.45, 'fwd'),
                             set_axis('arm.L', -0.16, 'fwd'),
                             set_axis('arm.R', 0.16, 'fwd')))
render_pose('sit', lambda: (set_axis('leg.L', 1.4, 'fwd'),
                            set_axis('leg.R', 1.4, 'fwd'),
                            set_axis('spine', 0.22), set_axis('head', 0.38)))
reset_pose()
print('[preview] wrote', PREVIEW.replace('.png', '_*.png'))
