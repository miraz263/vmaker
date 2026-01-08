from celery import shared_task
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip


@shared_task
def render_video(scenes):
clips = []
for scene in scenes:
clip = ImageClip(scene['image']).set_duration(scene['duration'])
if scene.get('audio'):
clip = clip.set_audio(AudioFileClip(scene['audio']))
clips.append(clip)


final = concatenate_videoclips(clips)
output = 'media/videos/output.mp4'
final.write_videofile(output, fps=24)
return output