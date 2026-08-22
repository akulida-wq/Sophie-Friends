import bpy, sys
src, dst = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.sequence_editor_create()
strip = sc.sequence_editor.strips.new_sound('s', src, 1, 1)
sc.frame_end = strip.frame_final_end
sc.render.ffmpeg.audio_codec = 'MP3'
sc.render.ffmpeg.audio_bitrate = 160
bpy.ops.sound.mixdown(filepath=dst, container='MP3', codec='MP3', bitrate=160)
print('[mp3] wrote', dst)
