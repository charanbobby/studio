import io
from pathlib import Path
from unittest.mock import patch

import pytest

from reel_gen.media.replicate_flux import generate_image


def _png_bytes() -> bytes:
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f"
        "15c4890000000d49444154789c63000100000005000100"
        "5db4e8910000000049454e44ae426082"
    )


def test_generate_image_writes_png(tmp_path, monkeypatch):
    monkeypatch.setenv("REPLICATE_API_TOKEN", "r8_test")
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    monkeypatch.setenv("DAILY_COST_CAP_USD", "100")

    class FakeFile:
        def read(self) -> bytes:
            return _png_bytes()

    with patch("reel_gen.media.replicate_flux.replicate.run", return_value=[FakeFile()]):
        path, cost = generate_image(prompt="x", out_dir=tmp_path, scene_idx=0)
    assert path.exists()
    assert path.suffix == ".png"
    assert cost.cost_usd > 0
