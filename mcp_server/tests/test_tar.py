import io, tarfile, pytest
from pathlib import Path
from mcp_server.tar_project import tar_dir, TooLargeError

FIX = Path(__file__).parent / "fixtures" / "tiny_project"

def test_tar_dir_returns_gzip_bytes():
    out = tar_dir(FIX)
    assert out.startswith(b"\x1f\x8b")  # gzip magic

def test_tar_contains_expected_entries():
    out = tar_dir(FIX)
    with tarfile.open(fileobj=io.BytesIO(out), mode="r:gz") as tf:
        names = {m.name for m in tf.getmembers()}
    assert "./config.py" in names
    assert "./captions.py" in names

def test_size_guard_refuses_oversize(tmp_path):
    big = tmp_path / "big.bin"
    big.write_bytes(b"\x00" * (26 * 1024 * 1024))
    with pytest.raises(TooLargeError):
        tar_dir(tmp_path, max_bytes=25 * 1024 * 1024)
