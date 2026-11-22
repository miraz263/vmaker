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


def build_camera_filter(move: str, total_frames: int, fps: int, duration: float) -> str:
    """
    Smooth eased camera move over a still picture.
    The picture is upscaled first so zoompan doesn't wobble from integer rounding.
    """
    n = max(total_frames - 1, 1)
    t = f"(on/{n})"
    ease = f"({t}*{t}*(3-2*{t}))"          # smoothstep: slow start, slow end
    center_x = "(iw-iw/zoom)/2"
    center_y = "(ih-ih/zoom)/2"

    moves = {
        "push_in":   (f"1+0.18*{ease}", center_x, center_y),
        "pull_out":  (f"1.18-0.18*{ease}", center_x, center_y),
        "pan_left":  ("1.15", f"(iw-iw/zoom)*(1-{ease})", center_y),
        "pan_right": ("1.15", f"(iw-iw/zoom)*{ease}", center_y),
        "tilt_up":   ("1.15", center_x, f"(ih-ih/zoom)*(1-{ease})"),
    }
    z, x, y = moves.get(move, moves["push_in"])
    fade_out_start = max(duration - 0.35, 0)
    return (
        "scale=3840:2160:force_original_aspect_ratio=increase,crop=3840:2160,"
        f"zoompan=z='{z}':x='{x}':y='{y}':d={total_frames}:s=1920x1080:fps={fps},"
        f"fade=t=in:st=0:d=0.35,fade=t=out:st={fade_out_start:.2f}:d=0.35,"
        "format=yuv420p"
    )


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

        import hashlib
        import subprocess
        from apps.ai_engine.storyboard import attach_visual_plan
        from apps.ai_engine.web_assets import generate_scene_image

        temp_clips_dir = media_root / "videos" / "temp" / str(job.id)
        temp_clips_dir.mkdir(parents=True, exist_ok=True)

        # Older projects were saved before the storyboard existed: plan them now.
        if any(not (sc.data or {}).get("visual") for sc in scenes):
            story = getattr(job.project, "story", None)
            story_text = getattr(story, "text", "") if story else ""
            datas = [sc.data or {} for sc in scenes]
            attach_visual_plan(story_text or " ".join(
                (d.get("narration") or {}).get("text", "") for d in datas), datas)
            for sc, d in zip(scenes, datas):
                sc.data = d
                sc.save(update_fields=["data"])

        clip_paths = []

        for idx, sc in enumerate(scenes):
            sc_data = sc.data or {}
            visual = sc_data.get("visual") or {}

            # 1. Scene picture (regenerated only when the prompt changes)
            scenes_dir = media_root / "scenes"
            scenes_dir.mkdir(parents=True, exist_ok=True)
            prompt_hash = hashlib.sha1(
                f"{visual.get('prompt', '')}|{visual.get('seed', 42)}".encode("utf-8")
            ).hexdigest()[:10]
            scene_img_path = scenes_dir / f"scene_{sc.id}_{prompt_hash}.jpg"

            if not scene_img_path.exists() or scene_img_path.stat().st_size < 5000:
                used = generate_scene_image(
                    prompt=visual.get("prompt", ""),
                    save_path=scene_img_path,
                    seed=int(visual.get("seed", 42)),
                )
                visual["image_source"] = used
                visual["image"] = f"scenes/{scene_img_path.name}"
                sc_data["visual"] = visual
                sc.data = sc_data
                sc.save(update_fields=["data"])

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
            hold = 0.6  # breathing room after each narration line
            duration += hold
            total_frames = int(duration * fps)
            vf = build_camera_filter(visual.get("camera", "push_in"), total_frames, fps, duration)

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
                "-af", "apad,aresample=44100",
                "-t", str(duration),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-r", str(fps),
                "-c:a", "aac",
                "-ar", "44100",
                "-ac", "2",
                "-b:a", "192k",
                "-preset", "fast",
                str(clip_out)
            ]
            subprocess.run(cmd_clip, check=True, capture_output=True)
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
                "-stream_loop", "-1", "-i", str(bgm_path),
                "-filter_complex",
                "[1:a]volume=0.12[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[aout]",
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
        subprocess.run(cmd_final, check=True, capture_output=True)

        # 5. Job Complete
        job.status = "COMPLETED"
        job.progress = 100
        job.output_file = rel_output_path
        job.video_url = media_url.rstrip("/") + "/" + rel_output_path
        job.completed_at = datetime.now()
        job.save(update_fields=["status", "progress", "output_file", "video_url", "completed_at"])

        return f"Success: Video rendered to {rel_output_path}"

    except Exception as e:
        import subprocess
        detail = str(e)
        if isinstance(e, subprocess.CalledProcessError) and e.stderr:
            stderr = e.stderr.decode("utf-8", "ignore") if isinstance(e.stderr, bytes) else e.stderr
            detail += "\n" + stderr[-1500:]
        job.status = "FAILED"
        job.error_message = detail
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
