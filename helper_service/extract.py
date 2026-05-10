import io, tarfile
from pathlib import Path

class ExtractError(Exception):
    pass

def extract_project(tarball: bytes, dest: Path) -> None:
    """Extract a gzipped tarball into dest. Refuses absolute paths and ..-traversal."""
    with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz") as tf:
        for member in tf.getmembers():
            name = member.name
            if name.startswith("/") or name.startswith("\\") or ".." in Path(name).parts:
                raise ExtractError(f"unsafe path in tarball: {name}")
        tf.extractall(dest, filter="data")
