"""Build environment.glb — quiet playground ~20x20 for Sophie & Friends:

/Applications/Blender.app/Contents/MacOS/Blender --background --python tools/blender/build_environment.py

Soft pastel low-poly, colored materials only (no textures): slide, swings,
sandbox, trees, edge bushes. Story props are separate named objects the
engine looks up: Ball, Chalk, Blocks, Tree. Ground mesh is named Ground
(movement raycast target).

Blender +Y here becomes engine -Z (glTF): a Blender position (x, y) maps to
engine (x, -y). Prop placements mirror the current grey-box layout.
"""

import math
import os
import struct
import json as jsonlib

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_GLB = os.path.join(ROOT, 'public', 'assets', 'environment.glb')
OUT_PREVIEW = os.path.join(ROOT, 'tools', 'blender', 'preview_environment.png')


def srgb(r, g, b):
    return tuple((c / 255.0) ** 2.2 for c in (r, g, b)) + (1.0,)


COLORS = {
    'grass': srgb(168, 198, 159),
    'sand': srgb(228, 208, 168),
    'sand_border': srgb(196, 168, 130),
    'coral': srgb(232, 158, 138),
    'sun_yellow': srgb(238, 210, 138),
    'dusty_blue': srgb(148, 178, 208),
    'rope': srgb(214, 202, 178),
    'trunk': srgb(160, 130, 104),
    'leaf_a': srgb(143, 179, 122),
    'leaf_b': srgb(122, 162, 112),
    'ball_orange': srgb(232, 168, 124),
    'block_green': srgb(201, 217, 140),
    'block_blue': srgb(163, 196, 217),
    'block_peach': srgb(217, 184, 163),
    'chalk_pink': srgb(217, 140, 163),
    'chalk_blue': srgb(140, 184, 217),
    'chalk_yellow': srgb(217, 201, 140),
}

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

_materials = {}


def mat(name):
    if name not in _materials:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = m.node_tree.nodes['Principled BSDF']
        bsdf.inputs['Base Color'].default_value = COLORS[name]
        bsdf.inputs['Roughness'].default_value = 0.92
        _materials[name] = m
    return _materials[name]


def smooth(obj):
    for p in obj.data.polygons:
        p.use_smooth = True


def box(name, size, loc, color, rot=(0, 0, 0), bevel=0.04):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    o.data.materials.append(mat(color))
    if bevel:
        b = o.modifiers.new('Bevel', 'BEVEL')
        b.width = bevel
        b.segments = 2
    return o


def cyl(name, radius, depth, loc, color, rot=(0, 0, 0), verts=16):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=loc,
                                        rotation=rot, vertices=verts)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat(color))
    smooth(o)
    return o


def ico(name, radius, loc, color, scale=(1, 1, 1), subdiv=2):
    bpy.ops.mesh.primitive_ico_sphere_add(radius=radius, location=loc,
                                          subdivisions=subdiv)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    o.data.materials.append(mat(color))
    smooth(o)
    return o


def join(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    joined = bpy.context.active_object
    joined.name = name
    return joined


# ------------------------------------------------------------------ ground
bpy.ops.mesh.primitive_plane_add(size=26, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = 'Ground'
ground.data.materials.append(mat('grass'))

# ------------------------------------------------------------------- slide
# Platform on four legs, ramp descending toward the player (-Y), back ladder.
SLX, SLY = -6.5, 6.3
slide_parts = [
    box('S_platform', (0.9, 0.7, 0.08), (SLX, SLY, 1.1), 'sun_yellow'),
    box('S_ramp', (0.55, 2.3, 0.07), (SLX, SLY - 1.4, 0.57), 'coral',
        rot=(math.radians(25.5), 0, 0)),
    box('S_rail1', (0.06, 2.3, 0.12), (SLX - 0.26, SLY - 1.4, 0.68), 'coral',
        rot=(math.radians(25.5), 0, 0)),
    box('S_rail2', (0.06, 2.3, 0.12), (SLX + 0.26, SLY - 1.4, 0.68), 'coral',
        rot=(math.radians(25.5), 0, 0)),
]
for dx in (-0.38, 0.38):
    for dy in (-0.28, 0.28):
        slide_parts.append(box(f'S_leg{dx}{dy}', (0.09, 0.09, 1.06),
                               (SLX + dx, SLY + dy, 0.53), 'dusty_blue'))
for i, (rot_x, name) in enumerate([(math.radians(-14), 'S_lrail1'),
                                   (math.radians(-14), 'S_lrail2')]):
    slide_parts.append(box(name, (0.06, 0.06, 1.25),
                           (SLX - 0.28 + i * 0.56, SLY + 0.62, 0.6), 'dusty_blue',
                           rot=(rot_x, 0, 0)))
for rung_z in (0.35, 0.65, 0.95):
    slide_parts.append(box(f'S_rung{rung_z}', (0.56, 0.05, 0.05),
                           (SLX, SLY + 0.47 + rung_z * 0.25, rung_z), 'sun_yellow'))
join(slide_parts, 'Slide')

# ------------------------------------------------------------------- swing
# A-frames at both ends, top bar, two seats on ropes.
SWX, SWY = 8.0, 9.3
swing_parts = []
for sx in (-1.45, 1.45):
    swing_parts.append(cyl(f'W_a1_{sx}', 0.07, 2.3, (SWX + sx, SWY + 0.55, 1.0),
                           'dusty_blue', rot=(math.radians(26), 0, 0)))
    swing_parts.append(cyl(f'W_a2_{sx}', 0.07, 2.3, (SWX + sx, SWY - 0.55, 1.0),
                           'dusty_blue', rot=(math.radians(-26), 0, 0)))
swing_parts.append(cyl('W_bar', 0.06, 3.2, (SWX, SWY, 2.02), 'coral',
                       rot=(0, math.radians(90), 0)))
for sx in (-0.65, 0.65):
    for dy in (-0.16, 0.16):
        swing_parts.append(cyl(f'W_rope{sx}{dy}', 0.03, 1.4, (SWX + sx, SWY + dy, 1.3),
                               'rope', verts=8))
    swing_parts.append(box(f'W_seat{sx}', (0.32, 0.17, 0.035), (SWX + sx, SWY, 0.58),
                           'sun_yellow'))
join(swing_parts, 'Swing')

# ----------------------------------------------------------------- sandbox
SBX, SBY = 0.5, 10.5
sandbox_parts = []
for i, (dx, dy, sx, sy) in enumerate([(0, 1.8, 1.95, 0.12), (0, -1.8, 1.95, 0.12),
                                      (1.8, 0, 0.12, 1.95), (-1.8, 0, 0.12, 1.95)]):
    sandbox_parts.append(box(f'SB_{i}', (sx, sy, 0.15), (SBX + dx, SBY + dy, 0.15),
                             'sand_border'))
bpy.ops.mesh.primitive_plane_add(size=3.45, location=(SBX, SBY, 0.08))
sand = bpy.context.active_object
sand.name = 'SB_sand'
sand.data.materials.append(mat('sand'))
sandbox_parts.append(sand)
join(sandbox_parts, 'Sandbox')

# ------------------------------------------------- decorative trees, bushes
def make_tree(name, loc, crown_color, trunk_h=1.5, crown_r=1.25):
    trunk = cyl(f'{name}_trunk', 0.22, trunk_h, (loc[0], loc[1], trunk_h / 2),
                'trunk', verts=10)
    crown = ico(f'{name}_crown', crown_r, (loc[0], loc[1], trunk_h + crown_r * 0.7),
                crown_color, scale=(1, 1, 1.1))
    return join([trunk, crown], name)


make_tree('TreeDeco1', (-9.5, 1.5), 'leaf_b', trunk_h=1.7, crown_r=1.4)
make_tree('TreeDeco2', (9.5, 3.0), 'leaf_a', trunk_h=1.3, crown_r=1.1)

bush_spots = [(-11, -4), (-10.5, 9.5), (-4.5, 12), (4.5, 12.3), (11.5, 1),
              (11, -6.5), (-7.5, -11), (0.5, -11.8), (7.5, -11.2), (11.2, 6.5)]
bushes = []
for i, (bx, by) in enumerate(bush_spots):
    color = 'leaf_a' if i % 2 == 0 else 'leaf_b'
    bushes.append(ico(f'B_{i}', 0.75, (bx, by, 0.45), color, scale=(1.25, 1, 0.75)))
join(bushes, 'Bushes')

# ------------------------------------------------- named gameplay props
# Engine positions (x, z): Ball (3.5, 1.5), Chalk (1.5, -4),
# Blocks (-4, -2.5), Tree (5.5, -6)  ->  Blender y = -z.
ball = ico('Ball', 0.4, (3.5, -1.5, 0.4), 'ball_orange', subdiv=3)

chalk_parts = []
for i, (color, dx, dy, rz) in enumerate([('chalk_pink', -0.18, 0, 0),
                                         ('chalk_blue', 0.0, 0.1, 0.6),
                                         ('chalk_yellow', 0.16, -0.06, 1.1)]):
    chalk_parts.append(cyl(f'C_{i}', 0.06, 0.5, (1.5 + dx, 4 + dy, 0.06), color,
                           rot=(0, math.radians(90), rz), verts=10))
join(chalk_parts, 'Chalk')

block_parts = []
for i, (color, dx, dy, dz) in enumerate([('block_green', 0, 0, 0.25),
                                         ('block_blue', 0.6, 0.15, 0.25),
                                         ('block_peach', 0.28, 0.05, 0.75)]):
    block_parts.append(box(f'BL_{i}', (0.5, 0.5, 0.5), (-4 + dx, 2.5 + dy, dz), color))
join(block_parts, 'Blocks')

make_tree('Tree', (5.5, 6), 'leaf_a', trunk_h=1.6, crown_r=1.3)

# ------------------------------------------------------------------- export
os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)
for obj in bpy.data.objects:
    obj.select_set(obj.type == 'MESH')
bpy.ops.export_scene.gltf(
    filepath=OUT_GLB,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
    export_animation_mode='NLA_TRACKS',
)
print('[export] wrote', OUT_GLB, os.path.getsize(OUT_GLB), 'bytes')

with open(OUT_GLB, 'rb') as fh:
    buf = fh.read()
json_len = struct.unpack_from('<I', buf, 12)[0]
gltf = jsonlib.loads(buf[20:20 + json_len].decode())
node_names = [n.get('name') for n in gltf.get('nodes', [])]
required = ['Ground', 'Ball', 'Chalk', 'Blocks', 'Tree', 'Slide', 'Swing', 'Sandbox']
missing = [r for r in required if r not in node_names]
print('[glb] nodes:', ', '.join(
    f"{n.get('name')}@{[round(v, 1) for v in n.get('translation', [0, 0, 0])]}"
    for n in gltf.get('nodes', [])))
print('[glb] missing required:', missing if missing else 'none')

# ------------------------------------------------------------------ preview
bpy.ops.object.camera_add(location=(11, -15, 12))
cam = bpy.context.active_object
cam.data.lens = 26
bpy.ops.object.empty_add(location=(0, 3.5, 0))
target = bpy.context.active_object
con = cam.constraints.new('TRACK_TO')
con.target = target
scene.camera = cam

bpy.ops.object.light_add(type='SUN', location=(6, 2, 12))
sun = bpy.context.active_object
sun.data.energy = 3.2
sun.rotation_euler = (math.radians(35), math.radians(-15), math.radians(40))

world = bpy.data.worlds.new('W') if not bpy.data.worlds else bpy.data.worlds[0]
scene.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (0.82, 0.90, 0.96, 1)
world.node_tree.nodes['Background'].inputs[1].default_value = 0.75

for engine in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH'):
    try:
        scene.render.engine = engine
        break
    except Exception:
        continue
scene.render.resolution_x = 1200
scene.render.resolution_y = 850
scene.render.filepath = OUT_PREVIEW
bpy.ops.render.render(write_still=True)
print('[preview] wrote', OUT_PREVIEW)
