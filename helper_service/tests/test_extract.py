import io, tarfile, pytest
from helper_service.extract import extract_project, ExtractError

def make_tar(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, content in files.items():
            ti = tarfile.TarInfo(name); ti.size = len(content)
            tf.addfile(ti, io.BytesIO(content))
    return buf.getvalue()

def test_extracts_files_into_workdir(tmp_path):
    tar = make_tar({"config.py": b"X = 1\n", "scenes/a.py": b"# a\n"})
    extract_project(tar, tmp_path)
    assert (tmp_path / "config.py").read_text() == "X = 1\n"
    assert (tmp_path / "scenes" / "a.py").read_text() == "# a\n"

def test_rejects_path_traversal(tmp_path):
    tar = make_tar({"..\\escape.py": b"x"})
    with pytest.raises(ExtractError):
        extract_project(tar, tmp_path)

def test_rejects_absolute_paths(tmp_path):
    tar = make_tar({"\\etc\\passwd": b"x"})
    with pytest.raises(ExtractError):
        extract_project(tar, tmp_path)
