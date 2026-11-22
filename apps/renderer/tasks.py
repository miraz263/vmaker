import os
import uuid
from datetime import datetime
from pathlib import Path
from celery import shared_task

# Ensure Pillow 10+ compatibility with MoviePy
try:
    import PIL.Image
    if not hasattr(PIL.Image, 'ANTIALIAS'):
        PIL.Image.ANTIALIAS = getattr(PIL.Image.Resampling, 'LANCZOS', None)
except Exception:
    pass

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

        import subprocess
        from apps.ai_engine.web_assets import generate_pixar_scene_visual

        temp_clips_dir = media_root / "videos" / "temp" / str(job.id)
        temp_clips_dir.mkdir(parents=True, exist_ok=True)

        clip_paths = []

        for idx, sc in enumerate(scenes):
            sc_data = sc.data or {}
            narration_text = sc_data.get("narration", {}).get("text", "")
            characters = sc_data.get("characters", [])
            char_name = characters[0].get("key", "panda") if characters else "panda"
            if char_name in ["warina", "human", "character", "default"] or any(w in narration_text for w in ["পিকু", "পান্ডা", "জঙ্গল", "বন"]):
                char_name = "panda"

            # 1. Resolve 3D Pixar Scene Visual
            scenes_dir = media_root / "scenes"
            scenes_dir.mkdir(parents=True, exist_ok=True)
            scene_img_path = scenes_dir / f"scene_{sc.id}_pixar.jpg"

            if not scene_img_path.exists() or scene_img_path.stat().st_size < 5000:
                shot_type = "wide" if idx == 0 else ("close_up" if idx % 2 == 1 else "medium")
                generate_pixar_scene_visual(
                    scene_desc=narration_text,
                    char_name=char_name,
                    shot_type=shot_type,
                    save_path=scene_img_path,
                    seed=idx * 29 + 42,
                    scene_index=idx
                )

            if not scene_img_path.exists() or scene_img_path.stat().st_size < 5000:
                pixar_fallback = media_root / "scenes" / "pixar" / f"panda_scene_{(idx % 5) + 1}.jpg"
                if pixar_fallback.exists():
                    scene_img_path = pixar_fallback
                else:
                    scene_img_path = media_root / "test_sana_panda.jpg"

            # 2. Resolve Narration Audio
            audio_info = sc_data.get("audio", {})
            audio_rel = audio_info.get("url", "")
            clean_audio_rel = audio_rel.replace(media_url, "").lstrip("/") if audio_rel else ""
            audio_abs = media_root / clean_audio_rel if clean_audio_rel else None

            # Get duration
            duration = float(sc_data.get("duration", 5.0))
            if audio_abs and audio_abs.exists():
                try:
                    cmd_dur = [
                        "ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
                        str(audio_abs)
                    ]
                    res = subprocess.run(cmd_dur, capture_output=True, text=True, check=True)
                    duration = max(float(res.stdout.strip()), 2.5)
                except Exception:
                    duration = 5.0

            fps = 25
            total_frames = int(duration * fps)

            # 3. Cinematic Camera Movement Filter
            motion_type = idx % 4
            if motion_type == 0:
                vf = (
                    f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
                    f"zoompan=z='min(zoom+0.0012,1.20)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps={fps}"
                )
            elif motion_type == 1:
                vf = (
                    f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
                    f"zoompan=z=1.12:x='if(lte(on,1),(iw-iw/zoom)/3,x+0.8)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps={fps}"
                )
            elif motion_type == 2:
                vf = (
                    f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
                    f"zoompan=z='min(zoom+0.0015,1.25)':x='iw/2-(iw/zoom/2)':y='ih/3-(ih/zoom/3)':d={total_frames}:s=1920x1080:fps={fps}"
                )
            else:
                vf = (
                    f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
                    f"zoompan=z='max(1.18-0.0012*on,1.0)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps={fps}"
                )

            clip_out = temp_clips_dir / f"clip_{idx}.mp4"
            cmd_clip = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", str(scene_img_path)
            ]
            if audio_abs and audio_abs.exists():
                cmd_clip += ["-i", str(audio_abs)]
            else:
                cmd_clip += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]

            cmd_clip += [
                "-vf", vf,
                "-t", str(duration),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                "-preset", "fast",
                str(clip_out)
            ]
            subprocess.run(cmd_clip, check=True)
            clip_paths.append(clip_out)

            job.progress = int(50 + (30 * ((idx + 1) / len(scenes))))
            job.save(update_fields=["progress"])

        # 4. Concatenation and BGM Mixing (80% - 100%)
        job.status = "ENCODING"
        job.progress = 85
        job.save(update_fields=["status", "progress"])

        concat_list_file = temp_clips_dir / "concat_list.txt"
        with open(concat_list_file, "w") as f:
            for cp in clip_paths:
                f.write(f"file '{cp}'\n")

        rel_out_dir = "videos/renders"
        abs_out_dir = media_root / rel_out_dir
        abs_out_dir.mkdir(parents=True, exist_ok=True)

        filename = f"project_{job.project_id}_{uuid.uuid4().hex[:8]}.mp4"
        rel_output_path = f"{rel_out_dir}/{filename}"
        abs_output_path = abs_out_dir / filename

        bgm_path = media_root / "audio" / "storybook_bgm.mp3"
        if bgm_path.exists():
            cmd_final = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", str(concat_list_file),
                "-i", str(bgm_path),
                "-filter_complex", "[1:a]volume=0.15[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
                "-map", "0:v", "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                str(abs_output_path)
            ]
        else:
            cmd_final = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", str(concat_list_file),
                "-c", "copy",
                str(abs_output_path)
            ]
        subprocess.run(cmd_final, check=True)

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
