import base64
import json

import respx
from httpx import Response

from reel_gen.media.elevenlabs_tts import generate_voiceover


@respx.mock
def test_generate_voiceover_writes_mp3_and_alignment(tmp_path, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "v")
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    monkeypatch.setenv("DAILY_COST_CAP_USD", "100")

    fake_mp3 = b"\xff\xfb\x90\x44\x00" + b"\0" * 200
    payload = {
        "audio_base64": base64.b64encode(fake_mp3).decode(),
        "alignment": {
            "characters": list("Hello"),
            "character_start_times_seconds": [0, 0.1, 0.2, 0.3, 0.4],
            "character_end_times_seconds": [0.1, 0.2, 0.3, 0.4, 0.5],
        },
    }
    respx.post(
        "https://api.elevenlabs.io/v1/text-to-speech/v/with-timestamps"
    ).mock(return_value=Response(200, json=payload))

    out_mp3, words, cost = generate_voiceover(text="Hello", out_dir=tmp_path)
    assert out_mp3.exists()
    assert out_mp3.read_bytes() == fake_mp3
    assert words[0].text and words[0].end_s > words[0].start_s
    assert cost.cost_usd > 0
