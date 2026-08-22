import bpy, sys, os, math
from mathutils import Vector
src = sys.argv[-2]; out_dir = sys.argv[-1]
os.makedirs(out_dir, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
sc = bpy.context.scene
sc.render.resolution_x = 320; sc.render.resolution_y = 400
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
# границы модели
bpy.context.view_layer.update()
mins = Vector((1e9,)*3); maxs = Vector((-1e9,)*3)
for o in bpy.data.objects:
    if o.type == 'MESH':
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            mins = Vector(map(min, mins, w)); maxs = Vector(map(max, maxs, w))
ctr = (mins + maxs) / 2; h = maxs.z - mins.z
cam.location = (ctr.x, ctr.y - h * 2.6, ctr.z + h * 0.15)
cam.rotation_euler = (math.radians(86), 0, 0)
cam.data.lens = 45
names = [a.name for a in bpy.data.actions]
print('[clips]', names)
arm.animation_data_create()
for a in bpy.data.actions:
    arm.animation_data.action = a
    try: arm.animation_data.action_slot = a.slots[0]
    except Exception: pass
    f0, f1 = a.frame_range
    for tag, fr in (('a', f0 + (f1 - f0) * 0.35), ('b', f0 + (f1 - f0) * 0.75)):
        sc.frame_set(int(fr))
        sc.render.filepath = os.path.join(out_dir, f'{a.name}_{tag}.png')
        bpy.ops.render.render(write_still=True)
print('[done]')
