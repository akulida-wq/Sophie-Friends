"""Bruno (Meshy, merged animations) — переупаковка под игру.

Вход:  bruno_meshy_anims.glb (корень; риг 24 кости + 12 анимаций Meshy)
Выход: public/assets/bruno_meshy.glb (клипы переименованы под bruno.json)

Запуск:
  /Applications/Blender.app/Contents/MacOS/Blender --background \
      --python tools/blender/build_bruno_meshy.py

Что делает: убирает мусорный Icosphere, ужимает текстуры 8192->2048,
разворачивает мордой в +Y (конвенция проекта, движок делает флип 180),
раскладывает 12 анимаций Meshy на 15 клипов игры (некоторые
переиспользуются), экспортирует + рендерит превью.
"""

import math
import os
import struct
import json as jsonlib

import bpy
from mathutils import Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'bruno_meshy_anims.glb')
OUT = os.path.join(ROOT, 'public', 'assets', 'bruno_meshy.glb')
OUT_PREVIEW = os.path.join(ROOT, 'tools', 'blender', 'preview_bruno_meshy.png')
HEADLESS = bpy.app.background

# игровой клип <- анимация Meshy (переиспользование — это ок)
CLIP_MAP = {
    'IdleSad': 'Look_Around_Dumbfounded',
    'IdleOpen': 'Idle_3',
    'Walk': 'Walking',
    'SitAlone': 'Look_Back_and_Sit',
    'NoticeSmile': 'Stand_and_Chat',
    'SmallWave': 'Wave_for_Help_4',
    'WelcomeGesture': 'Jump_with_Arms_Open',
    'HandToChest': 'Talk_Passionately',
    'BrightenMakeRoom': 'Stand_and_Chat',
    'TryJoinClumsy': 'Hip_Hop_Dance_2',
    'RollOffCourse': 'Backflip_Jump',
    'TryAgainSucceed': 'Jump_with_Arms_Open',
    'PlayQuiet': 'Stand_and_Chat',
    'PlayIncluded': 'Hip_Hop_Dance_2',
    'TailWag': 'Hip_Hop_Dance_2',
}

if HEADLESS:
    bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 24

bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
char = max(meshes, key=lambda o: len(o.data.vertices))
for o in meshes:
    if o is not char:
        print('[clean] removing stray mesh:', o.name)
        bpy.data.objects.remove(o, do_unlink=True)

src_actions = {a.name: a for a in bpy.data.actions}
missing = [m for m in CLIP_MAP.values() if m not in src_actions]
assert not missing, f'нет анимаций Meshy: {missing}'

# Ориентацию НЕ трогаем: разворот rest-позы ломает пространство
# анимационных кривых Hips при реэкспорте (модель взлетает на свой рост).
# Модель Meshy смотрит в -Y Blender (= +Z glTF); в движке BrunoView
# для этого ассета ставится yaw 0 вместо PI.
hf = arm.data.bones.get('headfront') or arm.data.bones['Head']
face_y = (hf.head_local - arm.data.bones['Hips'].head_local).y
print(f'[orient] headfront y-offset from hips: {face_y:+.2f} (ожидаем < 0)')

# ------------------------------------------------------------- NLA под игру
arm.animation_data_create()
if arm.animation_data.action:
    arm.animation_data.action = None
for tr in list(arm.animation_data.nla_tracks):
    arm.animation_data.nla_tracks.remove(tr)

for clip, src_name in CLIP_MAP.items():
    act = src_actions[src_name].copy()
    act.name = f'BM_{clip}'
    act.use_fake_user = True
    track = arm.animation_data.nla_tracks.new()
    track.name = clip
    strip = track.strips.new(clip, 1, act)
    if hasattr(strip, 'action_slot') and getattr(strip, 'action_slot', None) is None:
        try:
            strip.action_slot = act.slots[0]
        except Exception:
            pass
print('[nla] tracks:', ', '.join(t.name for t in arm.animation_data.nla_tracks))

# исходные экшены Meshy в экспорт не нужны
for a in list(bpy.data.actions):
    if not a.name.startswith('BM_'):
        a.use_fake_user = False

# ------------------------------------------------- материал: чистый PBR
# У Meshy-экспорта мусорный материал (эмиссив-дубль текстуры, спекуляр x2,
# alpha BLEND) — в движке выглядит чёрным металлом. Берём картинку из
# Base Color и собираем простой Principled: цвет + матовость.
mat = char.data.materials[0]
pr = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')

def linked_image(inp_name):
    inp = pr.inputs.get(inp_name)
    if not inp or not inp.links:
        return None
    node = inp.links[0].from_node
    for _ in range(4):
        if node.type == 'TEX_IMAGE':
            return node.image
        if node.inputs and node.inputs[0].links:
            node = node.inputs[0].links[0].from_node
        else:
            return None
    return None

base_img = linked_image('Base Color')
assert base_img is not None, 'не нашёл текстуру Base Color'
print('[mat] base color image:', base_img.name)
clean = bpy.data.materials.new('BrunoMat')
clean.use_nodes = True
cpr = next(n for n in clean.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
cpr.inputs['Roughness'].default_value = 0.65
tex = clean.node_tree.nodes.new('ShaderNodeTexImage')
tex.image = base_img
clean.node_tree.links.new(tex.outputs['Color'], cpr.inputs['Base Color'])
char.data.materials.clear()
char.data.materials.append(clean)

# ------------------------------------------------------------- текстуры
for img in bpy.data.images:
    if img is base_img and max(img.size) > 2048:
        img.scale(2048, 2048)
        print('[tex] downscaled', img.name, '-> 2048')

if HEADLESS:
    for o in bpy.data.objects:
        o.select_set(o in (arm, char))
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
    print('[glb] missing:', [c for c in CLIP_MAP if c not in anims] or 'none')

    # ------------------------------------------------------------- превью
    for tr in arm.animation_data.nla_tracks:
        tr.mute = True
    bpy.ops.object.light_add(type='SUN', location=(2, -3, 4))
    bpy.context.active_object.data.energy = 3
    world = bpy.data.worlds.new('W') if not bpy.data.worlds else bpy.data.worlds[0]
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (0.88, 0.9, 0.93, 1)
    bpy.ops.object.empty_add(location=(0, 0, 0.8))
    target = bpy.context.active_object
    bpy.ops.object.camera_add(location=(1.8, 2.6, 1.3))
    cam = bpy.context.active_object
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
            act = bpy.data.actions[f'BM_{clip}']
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
        for pb in arm.pose.bones:
            pb.rotation_euler = (0, 0, 0)
            pb.location = (0, 0, 0)
            pb.rotation_quaternion = (1, 0, 0, 0)

    for label, clip, frame in (('rest', None, 1), ('idlesad', 'IdleSad', 60),
                               ('wave', 'SmallWave', 50),
                               ('sit', 'SitAlone', 50),
                               ('play', 'PlayIncluded', 60)):
        render_pose(label, clip, frame)
    print('[preview] wrote', OUT_PREVIEW.replace('.png', '_*.png'))
