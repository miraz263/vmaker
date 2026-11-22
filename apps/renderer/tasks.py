import os
import uuid
from datetime import datetime
from pathlib import Path
from celery import shared_task

try:
    from django.conf import settings
except ImportError:
    settings = None


def get_media_root():
    if settings and hasattr(settings, "MEDIA_ROOT"):
        return Path(settings.MEDIA_ROOT)
    return Path(__file__).resolve().parent.parent.parent / "media"


def get_media_url():
    if settings and hasattr(settings, "MEDIA_URL"):
        return settings.MEDIA_URL
    return "/media/"


@shared_task(bind=True)
def render_project_video_task(self, job_id: str):
    """
    Celery task: Compiles all project scenes, audio narration, and visual assets into a full MP4.
    Updates RenderJob status and progress (0% -> 100%).
    """
    from .models import RenderJob
    from apps.scenes.models import Scene
    from apps.audio.services import create_scene_audio

    try:
        job = RenderJob.objects.get(id=job_id)
    except RenderJob.DoesNotExist:
        return f"Error: RenderJob {job_id} not found."

    media_root = get_media_root()
    media_url = get_media_url()

    try:
        # 1. Fetch scenes (10%)
        job.status = "QUEUED"
        job.progress = 10
        job.save(update_fields=["status", "progress"])

        scenes = list(Scene.objects.filter(project=job.project).order_by("order"))
        if not scenes:
            job.status = "FAILED"
            job.error_message = "No scenes found for this project."
            job.save(update_fields=["status", "error_message"])
            return

        # 2. Audio Verification & Generation (30%)
        job.status = "AUDIO_GENERATING"
        job.progress = 25
        job.save(update_fields=["status", "progress"])

        for idx, sc in enumerate(scenes):
            if not sc.data.get("audio") or not sc.data["audio"].get("url"):
                create_scene_audio(sc)
            job.progress = int(25 + (20 * ((idx + 1) / len(scenes))))
            job.save(update_fields=["progress"])

        # 3. Scene Assembly & Video Clips (50% - 80%)
        job.status = "SCENE_COMPILING"
        job.progress = 50
        job.save(update_fields=["status", "progress"])

        from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip, ColorClip

        clips = []
        for idx, sc in enumerate(scenes):
            sc_data = sc.data or {}
            duration = float(sc_data.get("duration", 6.0))

            # Resolve background visual
            bg_rel = sc_data.get("background", {}).get("asset", "backgrounds/default.jpg")
            bg_abs = media_root / bg_rel

            if bg_abs.exists():
                clip = ImageClip(str(bg_abs)).set_duration(duration)
            else:
                # Fallback to elegant slate color if background file is missing
                clip = ColorClip(size=(1920, 1080), color=(15, 23, 42)).set_duration(duration)

            # Attach Audio Narration if present
            audio_info = sc_data.get("audio", {})
            audio_rel = audio_info.get("url", "")
            if audio_rel:
                # strip leading /media/
                clean_audio_rel = audio_rel.replace(media_url, "").lstrip("/")
                audio_abs = media_root / clean_audio_rel
                if audio_abs.exists():
                    try:
                        audio_clip = AudioFileClip(str(audio_abs))
                        clip = clip.set_audio(audio_clip)
                    except Exception as e:
                        print(f"Warning: could not attach audio for scene {sc.id}: {e}")

            clips.append(clip)
            job.progress = int(50 + (30 * ((idx + 1) / len(scenes))))
            job.save(update_fields=["progress"])

        # 4. Encoding final MP4 (80% - 100%)
        job.status = "ENCODING"
        job.progress = 85
        job.save(update_fields=["status", "progress"])

        rel_out_dir = "videos/renders"
        abs_out_dir = media_root / rel_out_dir
        os.makedirs(abs_out_dir, exist_ok=True)

        filename = f"project_{job.project_id}_{uuid.uuid4().hex[:8]}.mp4"
        rel_output_path = f"{rel_out_dir}/{filename}"
        abs_output_path = abs_out_dir / filename

        final_video = concatenate_videoclips(clips, method="compose")
        final_video.write_videofile(
            str(abs_output_path),
            fps=job.fps,
            codec="libx264",
            audio_codec="aac",
            preset="fast",
            logger=None
        )

        # 5. Job Complete
        job.status = "COMPLETED"
        job.progress = 100
        job.output_file = rel_output_path
        job.video_url = media_url.rstrip("/") + "/" + rel_output_path
        job.completed_at = datetime.now()
        job.save(update_fields=["status", "progress", "output_file", "video_url", "completed_at"])

        return f"Success: Video rendered to {rel_output_path}"

    except Exception as e:
        job.status = "FAILED"
        job.error_message = str(e)
        job.save(update_fields=["status", "error_message"])
        print(f"RenderJob {job_id} failed: {e}")
        return f"Error: {e}"


# Legacy backward-compatible function
@shared_task
def render_video(scenes):
    from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
    clips = []
    for scene in scenes:
        clip = ImageClip(scene['image']).set_duration(scene['duration'])
        if scene.get('audio'):
            clip = clip.set_audio(AudioFileClip(scene['audio']))
        clips.append(clip)

    final = concatenate_videoclips(clips)
    output = 'media/videos/output.mp4'
    os.makedirs(os.path.dirname(output), exist_ok=True)
    final.write_videofile(output, fps=24)
    return output
