# Bruno patch v4 — руки-«ласты» как на арте (сплошные, шире книзу, до земли),
# ноги длиннее и видимые, кеды крупнее, кепка меньше, акварельная
# пятнистость тела (вершинные цвета — переживают экспорт в GLB).
# Применять к сцене, где Бруно уже собран через build_bruno.py.
# Вставь в Text Editor -> Run Script. Повторный запуск безопасен.
import bpy
from mathutils import Vector, noise

D = bpy.data
col = D.collections.get("Bruno")
rig = D.objects.get("Bruno_Rig")
assert col and rig, "Сначала собери Бруно: build_bruno.py"

def link_to_bruno(o):
    for c in list(o.users_collection):
        c.objects.unlink(o)
    col.objects.link(o)

def bind(o, bone):
    vg = o.vertex_groups.new(name=bone)
    vg.add(list(range(len(o.data.vertices))), 1.0, "REPLACE")
    o.modifiers.new("Armature", "ARMATURE").object = rig
    o.parent = rig

def smooth(o):
    for p in o.data.polygons:
        p.use_smooth = True

# ---------- 1. убрать старые руки/кисти/стопы/ноги и детали кед ----------
removed = 0
for o in list(D.objects):
    if any(o.name.startswith("BR_" + p) for p in
           ("Arm.", "Hand.", "Ankle.", "Leg.", "Shoe.", "Sole.", "Toe.", "Stripe")):
        D.objects.remove(o, do_unlink=True)
        removed += 1

# ---------- 2. акварельная пятнистость (вершинные цвета + нода) ----------
BASE, DARK, LIGHT = (118, 182, 228), (96, 158, 210), (152, 206, 240)
def mottle(o):
    me = o.data
    if me.color_attributes.get("Col"):
        me.color_attributes.remove(me.color_attributes.get("Col"))
    attr = me.color_attributes.new(name="Col", type="BYTE_COLOR", domain="POINT")
    base = Vector([c / 255 for c in BASE])
    dark = Vector([c / 255 for c in DARK])
    light = Vector([c / 255 for c in LIGHT])
    for i, v in enumerate(me.vertices):
        co = o.matrix_world @ v.co
        n = noise.noise(co * 2.4) * 0.65 + noise.noise(co * 6.0) * 0.35
        c = base.lerp(light, min(1, n * 1.1)) if n >= 0 else base.lerp(dark, min(1, -n * 1.3))
        attr.data[i].color = tuple(x ** 2.2 for x in c) + (1.0,)

m = D.materials.get("Bruno_body")
if m and m.use_nodes and not any(n.type == "VERTEX_COLOR" for n in m.node_tree.nodes):
    b = m.node_tree.nodes.get("Principled BSDF")
    vc = m.node_tree.nodes.new("ShaderNodeVertexColor")
    vc.layer_name = "Col"
    m.node_tree.links.new(vc.outputs["Color"], b.inputs["Base Color"])
for name in ["BR_Body", "BR_Ear.L", "BR_Ear.R"]:
    o = D.objects.get(name)
    if o:
        mottle(o)

# ---------- 3. руки-«ласты»: плотная metaball-цепочка, шире книзу ----------
for side, sx in (("L", 1), ("R", -1)):
    bpy.ops.object.metaball_add(type="BALL", location=(0, 0, 0))
    mb = bpy.context.active_object
    mb.data.resolution = 0.045
    steps = 9
    for i in range(steps):
        t = i / (steps - 1)
        el = mb.data.elements[0] if i == 0 else mb.data.elements.new()
        el.co = (sx * (0.50 + 0.13 * t), 0.02 * t, 1.42 - 1.04 * t)
        el.radius = 0.13 + 0.06 * t
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.active_object
    o.name = f"BR_Arm.{side}"
    o.data.materials.append(D.materials["Bruno_body"])
    smooth(o); mottle(o); link_to_bruno(o); bind(o, f"arm.{side}")

# ---------- 4. видимые ноги + кеды покрупнее ----------
def sphere(name, loc, scale, mat_name):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=loc, segments=24, ring_count=12)
    o = bpy.context.active_object
    o.name = name; o.scale = scale
    o.data.materials.append(D.materials[mat_name])
    smooth(o); link_to_bruno(o)
    return o

def box(name, size, loc, mat_name, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name; o.scale = size
    o.data.materials.append(D.materials[mat_name])
    bv = o.modifiers.new("Bevel", "BEVEL"); bv.width = 0.25; bv.segments = 3
    smooth(o); link_to_bruno(o)
    return o

for side, sx in (("L", 1), ("R", -1)):
    leg = sphere(f"BR_Leg.{side}", (sx * 0.17, 0, 0.32), (0.085, 0.085, 0.24), "Bruno_body")
    mottle(leg); bind(leg, f"leg.{side}")
    for o in (
        box(f"BR_Shoe.{side}", (0.18, 0.34, 0.12), (sx * 0.17, 0.06, 0.115), "Bruno_shoe"),
        box(f"BR_Sole.{side}", (0.19, 0.36, 0.042), (sx * 0.17, 0.06, 0.032), "Bruno_shoe_trim"),
        sphere(f"BR_Toe.{side}", (sx * 0.17, 0.245, 0.11), (0.14, 0.11, 0.09), "Bruno_shoe_trim"),
        *[box(f"BR_Stripe{i}.{side}", (0.015, 0.05, 0.09),
              (sx * 0.256, 0.10 - i * 0.075, 0.115), "Bruno_shoe_trim",
              rot=(0, 0, sx * 0.3)) for i in range(3)],
    ):
        bind(o, f"leg.{side}")

# ---------- 5. кепка меньше ----------
cap = D.objects.get("BR_Cap")
if cap:
    cap.scale = tuple(s * 0.83 for s in cap.scale)
    cap.location.z += 0.03
brim = D.objects.get("BR_CapBrim")
if brim:
    brim.scale = tuple(s * 0.85 for s in brim.scale)
    brim.location.z += 0.04
    brim.location.y -= 0.04

print(f"Patch v4: удалено {removed} старых частей; руки-ласты, ноги+кеды XL, "
      f"кепка -17%, пятнистость на теле/ушах/руках/ногах")
