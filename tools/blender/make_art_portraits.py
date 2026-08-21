"""Круглые портреты для диалоговых плашек из 2D-артов Артура.

blender -b -P tools/blender/make_art_portraits.py
Кроп круга (cx, cy, r в пикселях исходника), мягкое перо края 3px,
прозрачный фон, даунскейл до 512.
"""
import os
import numpy as np
import bpy

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
JOBS = [
    # (источник, cx, cy, r, выход)
    ('Freinds fotos/image_1 (2).png', 590, 365, 265, 'public/ui/portrait_sophie.png'),
    ('Freinds fotos/image.png', 490, 240, 215, 'public/ui/portrait_bruno.png'),
]

for src_rel, cx, cy, r, out_rel in JOBS:
    img = bpy.data.images.load(os.path.join(ROOT, src_rel))
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    px = px[::-1]  # blender хранит снизу вверх
    size = 2 * r
    y0, x0 = cy - r, cx - r
    crop = np.zeros((size, size, 4), dtype=np.float32)
    ys = slice(max(0, y0), min(h, y0 + size))
    xs = slice(max(0, x0), min(w, x0 + size))
    crop[ys.start - y0:ys.stop - y0, xs.start - x0:xs.stop - x0] = px[ys, xs]
    yy, xx = np.mgrid[0:size, 0:size]
    dist = np.hypot(yy - r + 0.5, xx - r + 0.5)
    feather = np.clip((r - dist) / 3.0, 0.0, 1.0)  # мягкий край
    crop[..., 3] *= feather
    out = bpy.data.images.new('portrait', width=size, height=size, alpha=True)
    out.pixels = crop[::-1].reshape(-1).tolist()
    out.scale(512, 512)
    out.filepath_raw = os.path.join(ROOT, out_rel)
    out.file_format = 'PNG'
    out.save()
    print(f'[portrait] {out_rel} <- {src_rel} ({cx},{cy},r{r})')
print('DONE')
