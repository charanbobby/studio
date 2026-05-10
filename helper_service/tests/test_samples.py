import pytest, json
from helper_service.samples import save_sample, list_samples, _sample_dir

@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("HELPER_DATA_DIR", str(tmp_path))

def test_save_sample_writes_manifest_and_copies_final(tmp_path):
    workdir = tmp_path / "workdir"; workdir.mkdir()
    (workdir / "final.mp4").write_bytes(b"fake-mp4")
    save_sample("job123", workdir, goal="demo X", target_url="https://x.example",
                beats_summary=["intro", "x"])
    assert (_sample_dir("job123") / "final.mp4").read_bytes() == b"fake-mp4"
    manifest = json.loads((_sample_dir("job123") / "manifest.json").read_text())
    assert manifest["goal"] == "demo X"

def test_list_samples_returns_each_manifest():
    save_sample("a", _make_workdir(b"a"), goal="A", target_url="u", beats_summary=[])
    save_sample("b", _make_workdir(b"b"), goal="B", target_url="u", beats_summary=[])
    out = list_samples()
    assert {s["job_id"] for s in out} == {"a", "b"}

def _make_workdir(content):
    import tempfile, pathlib
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "final.mp4").write_bytes(content)
    return d
