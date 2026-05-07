import subprocess
from pathlib import Path

from reel_gen.media.ffmpeg_stitch import stitch_reel
from reel_gen.state import CaptionWord, Scene, ScriptPlan


def test_stitch_produces_1080x1920_mp4(tmp_path):
    img1 = tmp_path / "scene_00.png"
    img2 = tmp_path / "scene_01.png"
    for img, color in [(img1, "teal"), (img2, "salmon")]:
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={color}:s=1080x1920:d=1",
            "-frames:v", "1", str(img)
        ], check=True)
    voice = tmp_path / "voiceover.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
        "-t", "5", "-q:a", "9", str(voice)
    ], check=True)

    plan = ScriptPlan(
        hook="hi", scenes=[
            Scene(scene_idx=0, duration_s=2.5, visual_prompt="x", voiceover_excerpt="hi", motion="zoom_in"),
            Scene(scene_idx=1, duration_s=2.5, visual_prompt="x", voiceover_excerpt="bye", motion="zoom_out"),
        ],
        voiceover_text="hi bye", voice_style="warm", music_mood=None, aspect_ratio="9:16",
    )
    captions = [
        CaptionWord(text="hi", start_s=0.0, end_s=2.0),
        CaptionWord(text="bye", start_s=2.5, end_s=4.5),
    ]
    out = tmp_path / "reel.mp4"
    stitch_reel(plan=plan, image_paths=[img1, img2], voiceover=voice,
                music=None, captions=captions, out=out)
    assert out.exists()

    info = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", str(out)
    ]).decode().strip()
    assert info == "1080x1920"
