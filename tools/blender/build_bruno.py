"""Bruno для Sophie & Friends — генератор модели + рига + 9 клипов.

КАК СМОТРЕТЬ САМОМУ (GUI):
    /Applications/Blender.app/Contents/MacOS/Blender --python "tools/blender/build_bruno.py"
  Откроется Blender с собранным Бруно (rest pose).
  Анимации: выбери Bruno_Rig -> редактор NLA -> включи "солнышко" (solo)
  на нужном треке (IdleSad, Walk, ...) -> пробел = play.

ЭКСПОРТ В GLB + ПРЕВЬЮ (headless, запускаю я после одобрения):
    /Applications/Blender.app/Contents/MacOS/Blender --background --python "tools/blender/build_bruno.py"

Референс: docs/01 + арт заказчика — высокий светло-голубой блоб: голова и
тело одним куском (шире сверху), одно большое веко-око с бликом, кремовые
веснушки на щеках, мягкий рот с одним клыком вниз, уши-рожки по бокам,
розовая кепка с козырьком, длинные висячие руки с ладошками, короткие ноги
в массивных зелёных кедах. Морда в +Y (как у Софи; движок разворачивает).

Клипы: IdleSad, IdleOpen, Walk, HandToChest, SmallWave, SitAlone,
TryJoinClumsy, TryAgainSucceed, PlayIncluded
"""

import math
import os
import struct
import json as jsonlib

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_GLB = os.path.join(ROOT, 'public', 'assets', 'bruno.glb')
OUT_PREVIEW = os.path.join(ROOT, 'tools', 'blender', 'preview_bruno.png')
HEADLESS = bpy.app.background

FPS = 24


def srgb(r, g, b):
    return tuple((c / 255.0) ** 2.2 for c in (r, g, b)) + (1.0,)


COL = {
    'body': srgb(126, 188, 230),     # яркий небесно-голубой (как в арте)
    'freckle': srgb(246, 233, 183),  # кремовые веснушки
    'cap': srgb(228, 138, 190),      # розовая кепка
    'shoe': srgb(52, 150, 84),       # зелёные кеды
    'shoe_trim': srgb(240, 244, 240),
    'eye': srgb(244, 244, 240),
    'pupil': srgb(30, 34, 44),
    'highlight': srgb(255, 255, 255),
    'mouth': srgb(38, 48, 72),
    'fang': srgb(248, 246, 238),
}

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = FPS

_mats = {}


def mat(key, roughness=0.9):
    if key not in _mats:
        m = bpy.data.materials.new(f'Bruno_{key}')
        m.use_nodes = True
        bsdf = m.node_tree.nodes['Principled BSDF']
        bsdf.inputs['Base Color'].default_value = COL[key]
        bsdf.inputs['Roughness'].default_value = roughness
        _mats[key] = m
    return _mats[key]


def smooth(obj):
    for p in obj.data.polygons:
        p.use_smooth = True


def sphere(name, r, loc, scale=(1, 1, 1), key='body', rot=(0, 0, 0), seg=28):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, rotation=rot,
                                         segments=seg, ring_count=seg // 2)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    o.data.materials.append(mat(key))
    smooth(o)
    return o


def rbox(name, size, loc, key, rot=(0, 0, 0), bevel=0.03):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    o.data.materials.append(mat(key))
    b = o.modifiers.new('Bevel', 'BEVEL')
    b.width = bevel
    b.segments = 3
    smooth(o)
    return o


parts = []  # (объект, кость) — жёсткая привязка

# ---------------------------------------------------------- тело-голова блоб
# Metaball даёт цельный "мармеладный" силуэт: широкая голова, плавное
# сужение вниз (без "талии" — элементы сильно перекрываются).
bpy.ops.object.metaball_add(type='BALL', location=(0, 0, 0))
mball = bpy.context.active_object
mball.data.resolution = 0.05
els = [((0, 0, 1.62), 0.64), ((0, 0, 1.25), 0.52),
       ((0, 0, 0.92), 0.47), ((0, 0, 0.68), 0.43)]
el0 = mball.data.elements[0]
el0.co, el0.radius = els[0]
for co, r in els[1:]:
    e = mball.data.elements.new()
    e.co = co
    e.radius = r
bpy.ops.object.convert(target='MESH')
blob = bpy.context.active_object
blob.name = 'Body'
blob.data.materials.append(mat('body'))
smooth(blob)


def surf_y(x, z):
    """Y поверхности блоба (морда, +Y) в точке (x, z) — рейкаст внутрь."""
    hit, loc, _n, _i = blob.ray_cast((x, 3.0, z), (0, -1, 0))
    return loc.y if hit else 0.45


def surf_x(z, y=0.0):
    hit, loc, _n, _i = blob.ray_cast((3.0, y, z), (-1, 0, 0))
    return loc.x if hit else 0.5


def top_z():
    hit, loc, _n, _i = blob.ray_cast((0, 0, 4.0), (0, 0, -1))
    return loc.z if hit else 2.2

# ------------------------------------------------------------------- детали
Z_TOP = top_z()

# Уши-рожки по бокам, ниже кепки, торчат заметно наружу-вверх.
for side, sx in (('L', 1), ('R', -1)):
    ex = surf_x(1.88, y=-0.03)
    ear = sphere(f'Ear.{side}', 1.0, (sx * (ex + 0.04), -0.03, 1.90),
                 scale=(0.15, 0.11, 0.26), rot=(0, sx * 1.25, 0))
    parts.append((ear, 'head'))

# Один большой глаз (утоплен в поверхность, чуть выпуклый) + зрачок + блик.
EYE_Z = 1.66
eye_y = surf_y(0, EYE_Z) - 0.075
eye = sphere('Eye', 0.21, (0, eye_y, EYE_Z), scale=(1, 0.55, 1))
eye.data.materials.clear()
eye.data.materials.append(mat('eye', roughness=0.3))
parts.append((eye, 'head'))
pupil_y = eye_y + 0.21 * 0.55 - 0.030
pupil = sphere('Pupil', 0.095, (0, pupil_y, EYE_Z), scale=(1, 0.45, 1))
pupil.data.materials.clear()
pupil.data.materials.append(mat('pupil', roughness=0.35))
parts.append((pupil, 'head'))
gleam = sphere('Gleam', 0.026, (0.042, pupil_y + 0.036, EYE_Z + 0.045), seg=12)
gleam.data.materials.clear()
gleam.data.materials.append(mat('highlight', roughness=0.2))
parts.append((gleam, 'head'))

# Кремовые веснушки — по 4 на щёку, лежат на поверхности.
freckles = [(0.24, 1.57, 0.046), (0.32, 1.62, 0.037),
            (0.28, 1.49, 0.031), (0.36, 1.53, 0.041)]
for i, (fx, fz, fr) in enumerate(freckles):
    for sx in (1, -1):
        fy = surf_y(sx * fx, fz) - fr * 0.35
        f = sphere(f'Freckle{i}{"LR"[sx < 0]}', fr, (sx * fx, fy, fz), seg=12)
        f.data.materials.clear()
        f.data.materials.append(mat('freckle'))
        parts.append((f, 'head'))

# Мягкий рот-линия + один клык вниз — на поверхности мордочки.
MOUTH_Z = 1.44
mouth_y = surf_y(0, MOUTH_Z) - 0.006
mouth = sphere('Mouth', 1.0, (0, mouth_y, MOUTH_Z), scale=(0.15, 0.028, 0.022))
mouth.data.materials.clear()
mouth.data.materials.append(mat('mouth'))
parts.append((mouth, 'head'))
fang_y = surf_y(0.06, 1.37) - 0.01
bpy.ops.mesh.primitive_cone_add(radius1=0.036, radius2=0.008, depth=0.10,
                                location=(0.06, fang_y, 1.365),
                                rotation=(math.pi, 0, 0), vertices=10)
fang = bpy.context.active_object
fang.name = 'Fang'
fang.data.materials.append(mat('fang'))
smooth(fang)
parts.append((fang, 'head'))

# Розовая кепка — облегает макушку, лёгкий наклон, скромный козырёк.
cap = sphere('Cap', 0.48, (0, 0.02, Z_TOP - 0.02),
             scale=(0.95, 0.95, 0.50), rot=(-0.05, 0.08, 0))
cap.data.materials.clear()
cap.data.materials.append(mat('cap'))
parts.append((cap, 'head'))
brim_y = surf_y(0, Z_TOP - 0.12) + 0.10
bpy.ops.mesh.primitive_cylinder_add(radius=0.20, depth=0.04,
                                    location=(0, brim_y, Z_TOP - 0.10),
                                    rotation=(0.13, 0, 0), vertices=20)
brim = bpy.context.active_object
brim.name = 'CapBrim'
brim.scale = (1.35, 1.0, 1.0)
brim.data.materials.append(mat('cap'))
smooth(brim)
parts.append((brim, 'head'))

# Длинные висячие руки, прижаты к телу, ладошки перекрываются с рукой.
for side, sx in (('L', 1), ('R', -1)):
    ax = surf_x(1.20) + 0.015
    armo = sphere(f'Arm.{side}', 1.0, (sx * ax, 0, 1.00),
                  scale=(0.085, 0.085, 0.52), rot=(0, sx * 0.05, 0))
    parts.append((armo, f'arm.{side}'))
    hand = sphere(f'Hand.{side}', 1.0, (sx * (ax + 0.03), 0.02, 0.54),
                  scale=(0.105, 0.085, 0.145))
    parts.append((hand, f'arm.{side}'))

# Короткие ноги + массивные кеды (подошва + белый носок).
for side, sx in (('L', 1), ('R', -1)):
    leg = sphere(f'Leg.{side}', 1.0, (sx * 0.17, 0, 0.38),
                 scale=(0.10, 0.10, 0.23))
    parts.append((leg, f'leg.{side}'))
    shoe = rbox(f'Shoe.{side}', (0.15, 0.28, 0.105), (sx * 0.17, 0.07, 0.10),
                'shoe')
    parts.append((shoe, f'leg.{side}'))
    sole = rbox(f'Sole.{side}', (0.16, 0.30, 0.035), (sx * 0.17, 0.07, 0.028),
                'shoe_trim', bevel=0.015)
    parts.append((sole, f'leg.{side}'))
    toe = sphere(f'Toe.{side}', 1.0, (sx * 0.17, 0.22, 0.095),
                 scale=(0.115, 0.09, 0.075))
    toe.data.materials.clear()
    toe.data.materials.append(mat('shoe_trim'))
    parts.append((toe, f'leg.{side}'))

# ------------------------------------------------------------------- риг
bpy.ops.object.armature_add(location=(0, 0, 0))
arm_obj = bpy.context.active_object
arm_obj.name = 'Bruno_Rig'
bpy.ops.object.mode_set(mode='EDIT')
eb = arm_obj.data.edit_bones
eb.remove(eb[0])
BONES = {
    'root': ((0, 0, 0.05), (0, 0, 0.55), None),
    'spine': ((0, 0, 0.55), (0, 0, 1.45), 'root'),
    'head': ((0, 0, 1.45), (0, 0, 2.30), 'spine'),
    'arm.L': ((0.50, 0, 1.48), (0.56, 0, 0.50), 'spine'),
    'arm.R': ((-0.50, 0, 1.48), (-0.56, 0, 0.50), 'spine'),
    'leg.L': ((0.17, 0, 0.50), (0.17, 0, 0.05), 'root'),
    'leg.R': ((-0.17, 0, 0.50), (-0.17, 0, 0.05), 'root'),
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

# Блоб: плавный градиент spine->head по высоте, чтобы наклон головы
# органично гнул верх тела (а не отрывал детали от туловища).
vg_spine = blob.vertex_groups.new(name='spine')
vg_head = blob.vertex_groups.new(name='head')
for v in blob.data.vertices:
    t = (v.co.z - 1.15) / (1.75 - 1.15)
    t = max(0.0, min(1.0, t))
    if t < 1.0:
        vg_spine.add([v.index], 1.0 - t, 'REPLACE')
    if t > 0.0:
        vg_head.add([v.index], t, 'REPLACE')
mod = blob.modifiers.new('Armature', 'ARMATURE')
mod.object = arm_obj
blob.parent = arm_obj

for obj, bone in parts:
    vg = obj.vertex_groups.new(name=bone)
    vg.add(list(range(len(obj.data.vertices))), 1.0, 'REPLACE')
    m = obj.modifiers.new('Armature', 'ARMATURE')
    m.object = arm_obj
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

# ------------------------------------------------------------------ клипы
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


CLIPS = {}


def begin_clip(name, last):
    reset_pose()
    arm_obj.animation_data.action = None
    scene.frame_start = 1
    scene.frame_end = last
    CLIPS[name] = last


def end_clip(name):
    act = arm_obj.animation_data.action
    assert act is not None, f'no action for {name}'
    act.name = name
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


begin_clip('IdleSad', 72)
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

begin_clip('IdleOpen', 72)
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

begin_clip('Walk', 24)
for f, a in ((1, 0.45), (13, -0.45), (24, 0.45)):
    kf('leg.L', f, pitch=a * S_LEG)
    kf('leg.R', f, pitch=-a * S_LEG)
    kf('arm.L', f, pitch=-a * 0.45 * S_ARM)
    kf('arm.R', f, pitch=a * 0.45 * S_ARM)
for f, z in ((1, -0.015), (7, 0.02), (13, -0.015), (19, 0.02), (24, -0.015)):
    kf('root', f, loc_z=z)
kf('spine', 1, pitch=0.05 * S_SPINE)
kf('spine', 24, pitch=0.05 * S_SPINE)
end_clip('Walk')

begin_clip('HandToChest', 48)
kf('arm.R', 1, pitch=0.0)
kf('arm.R', 16, pitch=1.35 * S_ARM, roll=0.55)
kf('arm.R', 48, pitch=1.35 * S_ARM, roll=0.55)
kf('head', 1, pitch=0.30 * S_HEAD)
kf('head', 28, pitch=0.10 * S_HEAD)
kf('head', 48, pitch=0.10 * S_HEAD)
kf('spine', 1, pitch=0.12 * S_SPINE)
kf('spine', 48, pitch=0.10 * S_SPINE)
end_clip('HandToChest')

begin_clip('SmallWave', 48)
kf('arm.R', 1, pitch=0.0, roll=0.0)
kf('arm.R', 10, pitch=2.4 * S_ARM, roll=0.0)
for f, r in ((16, 0.3), (24, -0.3), (32, 0.3), (40, 0.0)):
    kf('arm.R', f, pitch=2.4 * S_ARM, roll=r)
kf('arm.R', 48, pitch=1.2 * S_ARM, roll=0.0)
kf('head', 1, pitch=0.05 * S_HEAD)
kf('head', 20, pitch=-0.05 * S_HEAD)
kf('head', 48, pitch=0.0)
end_clip('SmallWave')

begin_clip('SitAlone', 60)
for f in (1, 60):
    kf('root', f, loc_z=-0.40)
    kf('leg.L', f, pitch=1.5 * S_LEG)
    kf('leg.R', f, pitch=1.5 * S_LEG)
    kf('spine', f, pitch=0.22 * S_SPINE)
kf('head', 1, pitch=0.34 * S_HEAD)
kf('head', 30, pitch=0.40 * S_HEAD)
kf('head', 60, pitch=0.34 * S_HEAD)
end_clip('SitAlone')

begin_clip('TryJoinClumsy', 60)
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

begin_clip('TryAgainSucceed', 60)
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

begin_clip('PlayIncluded', 48)
for f, z in ((1, 0.0), (12, 0.06), (24, 0.0), (36, 0.06), (48, 0.0)):
    kf('root', f, loc_z=z)
for f, a in ((1, 0.3), (24, -0.3), (48, 0.3)):
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
act = bpy.data.actions['IdleSad']
arm_obj.animation_data.action = act
scene.frame_set(36)
sad_head_z = tail_world('head').z
arm_obj.animation_data.action = None
reset_pose()
scene.frame_set(1)
print(f'[verify] head z rest={rest_head_z:.3f} IdleSad@36={sad_head_z:.3f} -> '
      f'{"OK" if sad_head_z < rest_head_z - 0.05 else "FAIL"}')
print('[clips]', ', '.join(sorted(CLIPS.keys())))

if HEADLESS:
    # ----------------------------------------------------------- экспорт
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
    print('[glb] missing clips:', [c for c in CLIPS if c not in anims] or 'none')

    # ----------------------------------------------------------- превью
    for track in arm_obj.animation_data.nla_tracks:
        track.mute = True
    reset_pose()
    scene.frame_set(1)
    bpy.ops.object.camera_add(location=(2.3, 3.2, 2.3))
    cam = bpy.context.active_object
    bpy.ops.object.empty_add(location=(0, 0, 1.25))
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
    # GUI: rest pose, приятный фон; смотри NLA для клипов.
    for track in arm_obj.animation_data.nla_tracks:
        track.mute = True
    reset_pose()
    scene.frame_set(1)
    print('GUI mode: модель собрана. NLA -> solo нужного трека -> Play.')
