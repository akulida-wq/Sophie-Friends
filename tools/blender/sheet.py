import bpy, sys, os, glob, numpy as np
d, out = sys.argv[-2], sys.argv[-1]
files = sorted(glob.glob(os.path.join(d, '*.png')))
clips = {}
for f in files:
    base = os.path.basename(f)[:-4]; name, k = base.rsplit('_', 1); clips.setdefault(name, {})[int(k)] = f
W, H = 220, 300; rows = list(clips)
sheet = np.ones((H * len(rows), W * 5, 4), dtype=np.float32)
for r, name in enumerate(rows):
    for k in range(5):
        f = clips[name].get(k)
        if not f: continue
        img = bpy.data.images.load(f)
        px = np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], 4)
        y0 = (len(rows) - 1 - r) * H
        sheet[y0:y0 + H, k * W:(k + 1) * W] = px[:H, :W]
        bpy.data.images.remove(img)
o = bpy.data.images.new('sheet', width=W * 5, height=H * len(rows), alpha=True)
o.pixels = sheet.reshape(-1).tolist(); o.filepath_raw = out; o.file_format = 'PNG'; o.save()
print('[sheet]', out, 'rows:', rows)
