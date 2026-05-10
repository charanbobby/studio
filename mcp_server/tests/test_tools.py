import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from mcp_server.tools import (helper_render_silent, helper_render_voice,
                              helper_render_full, helper_skill)

FIX = Path(__file__).parent / "fixtures" / "tiny_project"

@patch("mcp_server.tools.HelperClient")
def test_render_silent_passes_tar_to_client(MockClient, tmp_path):
    inst = MockClient.return_value
    inst.post_silent.return_value = {"job_id": "j", "preview_url": "/p",
                                       "estimate_usd": 0.05, "status": "awaiting_review"}
    out = helper_render_silent({"project_dir": str(FIX)})
    assert out["job_id"] == "j"
    args, kwargs = inst.post_silent.call_args
    assert isinstance(args[0], bytes)

@patch("mcp_server.tools.HelperClient")
def test_render_voice_returns_final_url(MockClient):
    MockClient.return_value.post_voice.return_value = {"final_url": "/f", "status": "done"}
    out = helper_render_voice({"job_id": "abc"})
    assert out == {"final_url": "/f", "status": "done"}

@patch("mcp_server.tools.HelperClient")
def test_skill_returns_markdown(MockClient):
    MockClient.return_value.get_skill.return_value = "# SKILL"
    out = helper_skill({})
    assert "SKILL" in out

def test_render_silent_returns_error_when_dir_missing():
    out = helper_render_silent({"project_dir": "/nonexistent"})
    assert "error" in out and out["error"] == "project_dir_not_found"
