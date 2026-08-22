import bpy, sys, os, math
from mathutils import Vector
src, out, names = sys.argv[-3], sys.argv[-2], sys.argv[-1].split(',')
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
sc = bpy.context.scene
sc.render.resolution_x = 220; sc.render.resolution_y = 300
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
bpy.context.view_layer.update()
mins = Vector((1e9,)*3); maxs = Vector((-1e9,)*3)
for o in bpy.data.objects:
    if o.type == 'MESH':
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            mins = Vector(map(min, mins, w)); maxs = Vector(map(max, maxs, w))
ctr = (mins + maxs) / 2; h = maxs.z - mins.z
cam.location = (ctr.x + h*1.2, ctr.y - h * 2.2, ctr.z + h * 0.15)
cam.rotation_euler = (math.radians(86), 0, math.radians(28))
cam.data.lens = 45
arm.animation_data_create()
for a in bpy.data.actions:
    if a.name not in names: continue
    arm.animation_data.action = a
    try: arm.animation_data.action_slot = a.slots[0]
    except Exception: pass
    f0, f1 = a.frame_range
    for k in range(5):
        sc.frame_set(int(f0 + (f1 - f0) * k / 4.0))
        sc.render.filepath = os.path.join(out, f'{a.name}_{k}.png')
        bpy.ops.render.render(write_still=True)
    print('[idle]', a.name, 'frames', int(f1 - f0))
