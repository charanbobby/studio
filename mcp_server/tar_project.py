import io, tarfile
from pathlib import Path

class TooLargeError(Exception):
    def __init__(self, size: int, limit: int):
        self.size = size; self.limit = limit
        super().__init__(f"project is {size} bytes; limit is {limit}")

DEFAULT_MAX_BYTES = 25 * 1024 * 1024  # 25 MB matches nginx upload cap

def tar_dir(path: Path, max_bytes: int = DEFAULT_MAX_BYTES) -> bytes:
    """Tar+gzip a directory tree. Raises TooLargeError if total > max_bytes."""
    total = sum(p.stat().st_size for p in path.rglob("*") if p.is_file())
    if total > max_bytes:
        raise TooLargeError(total, max_bytes)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        tf.add(path, arcname=".", filter=lambda ti: ti)
    return buf.getvalue()
