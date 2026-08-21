"""Друзья-монстрики (3 шт., риги Meshy) — переупаковка под игру.

Вход:  Friends (riggs + animation)/{yellow,pink,red}_merged.glb
Выход: public/assets/friend_{yellow,pink,red}.glb

Клипы стандартизированы: Idle (главный цикл), Look (озирается),
Chat (общается, у pink — второй айдл), Trick (только yellow: танец,
red: бокс). Материал — виниловый глянец (roughness 0.4), базовый цвет
родной. Rest-позу не вращаем (yaw в движке), scale-треки вырезаем.

Запуск:
  /Applications/Blender.app/Contents/MacOS/Blender --background \
      --python tools/blender/build_friends.py
"""

import os
import struct
import json as jsonlib

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DIR = os.path.join(ROOT, 'Friends (riggs + animation)')
OUT_DIR = os.path.join(ROOT, 'public', 'assets')

FRIENDS = {
    'yellow': {
        'file': 'yellow_merged.glb',
        'clips': {
            'Idle': 'Idle_7',
            'Look': 'Short_Breathe_and_Look_Around',
            'Chat': 'Stand_and_Chat',
            'Trick': 'Hip_Hop_Dance_2',
        },
        'polys': 26000,
    },
    'pink': {
        'file': 'pink_merged.glb',
        'clips': {
            'Idle': 'Idle_3',
            'Look': 'Long_Breathe_and_Look_Around',
            'Chat': 'Idle_9',
        },
        'polys': 26000,
    },
    'red': {
        'file': 'red_merged.glb',
        'clips': {
            'Idle': 'Idle_15',
            'Look': 'Short_Breathe_and_Look_Around',
            'Chat': 'Stand_and_Chat',
            'Trick': 'Boxing_Guard_Prep_Straight_Punch',
        },
        'polys': 24000,
    },
}


def strip_scale_curves(act):
    removed = 0
    try:
        for fc in list(act.fcurves):
            if fc.data_path.endswith('.scale'):
                act.fcurves.remove(fc)
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


def build(name, spec):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 24
    bpy.ops.import_scene.gltf(filepath=os.path.join(SRC_DIR, spec['file']))
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    char = max(meshes, key=lambda o: len(o.data.vertices))
    for o in meshes:
        if o is not char:
            bpy.data.objects.remove(o, do_unlink=True)

    src_actions = {a.name: a for a in bpy.data.actions}
    missing = [m for m in spec['clips'].values() if m not in src_actions]
    assert not missing, f'{name}: нет клипов {missing}'

    # NLA под игру
    arm.animation_data_create()
    if arm.animation_data.action:
        arm.animation_data.action = None
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)
    for clip, src_name in spec['clips'].items():
        act = src_actions[src_name].copy()
        act.name = f'F_{clip}'
        strip_scale_curves(act)
        act.use_fake_user = True
        track = arm.animation_data.nla_tracks.new()
        track.name = clip
        strip = track.strips.new(clip, 1, act)
        if hasattr(strip, 'action_slot') and getattr(strip, 'action_slot', None) is None:
            try:
                strip.action_slot = act.slots[0]
            except Exception:
                pass
    for a in list(bpy.data.actions):
        if not a.name.startswith('F_'):
            a.use_fake_user = False

    # материал: базовый цвет родной + виниловый глянец
    mat = char.data.materials[0]
    pr = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
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
    assert base_img is not None, f'{name}: нет basecolor'
    clean = bpy.data.materials.new(f'Friend{name}Mat')
    clean.use_nodes = True
    cpr = next(n for n in clean.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    cpr.inputs['Roughness'].default_value = 0.4  # виниловая игрушка
    tex = clean.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = base_img
    clean.node_tree.links.new(tex.outputs['Color'], cpr.inputs['Base Color'])
    if 'Emission Color' in cpr.inputs:
        clean.node_tree.links.new(tex.outputs['Color'], cpr.inputs['Emission Color'])
        cpr.inputs['Emission Strength'].default_value = 0.07
    char.data.materials.clear()
    char.data.materials.append(clean)
    if max(base_img.size) > 1024:
        base_img.scale(1024, 1024)

    # дециматизация
    n = len(char.data.polygons)
    if n > spec['polys']:
        mod = char.modifiers.new('dec', 'DECIMATE')
        mod.ratio = spec['polys'] / n
        dg = bpy.context.evaluated_depsgraph_get()
        newmesh = bpy.data.meshes.new_from_object(char.evaluated_get(dg))
        char.modifiers.remove(mod)
        old = char.data
        char.data = newmesh
        if old.users == 0:
            bpy.data.meshes.remove(old)
    print(f'[{name}] polys {n} -> {len(char.data.polygons)}')

    out = os.path.join(OUT_DIR, f'friend_{name}.glb')
    for o in bpy.data.objects:
        o.select_set(o in (arm, char))
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.gltf(
        filepath=out,
        export_format='GLB',
        use_selection=True,
        export_apply=False,
        export_animation_mode='NLA_TRACKS',
        export_skins=True,
    )
    with open(out, 'rb') as fh:
        buf = fh.read()
    jl = struct.unpack_from('<I', buf, 12)[0]
    g = jsonlib.loads(buf[20:20 + jl].decode())
    anims = [a.get('name') for a in g.get('animations', [])]
    print(f'[{name}] wrote {out} ({os.path.getsize(out)} bytes) clips: {anims}')


for fname, fspec in FRIENDS.items():
    build(fname, fspec)
