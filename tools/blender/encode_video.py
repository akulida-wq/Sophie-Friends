"""Пережатие mp4 через Blender VSE (в системе нет ffmpeg).
blender -b -P tools/blender/encode_video.py -- <in.mp4> <out.mp4> [height]
"""
import bpy, sys
src, dst = sys.argv[-3], sys.argv[-2]
height = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 720
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.sequence_editor_create()
v = sc.sequence_editor.strips.new_movie('v', src, 2, 1)
a = sc.sequence_editor.strips.new_sound('a', src, 1, 1)
sc.frame_start = 1
sc.frame_end = v.frame_final_end - 1
sc.render.fps = 24
sc.render.resolution_x = height * 16 // 9
sc.render.resolution_y = height
sc.render.resolution_percentage = 100
sc.render.image_settings.media_type = 'VIDEO'  # Blender 5: сначала тип
sc.render.image_settings.file_format = 'FFMPEG'
f = sc.render.ffmpeg
f.format = 'MPEG4'
f.codec = 'H264'
f.constant_rate_factor = 'HIGH'   # ~ crf 23
f.ffmpeg_preset = 'GOOD'
f.audio_codec = 'AAC'
f.audio_bitrate = 160
sc.render.filepath = dst
bpy.ops.render.render(animation=True)
print('[video] wrote', dst)
