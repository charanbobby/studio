import os
import shutil
from pathlib import Path
from fastapi import HTTPException

DEFAULT_MIN_FREE_BYTES = 1 * 1024 * 1024 * 1024  # 1 GB

def bytes_free(path: Path) -> int:
    return shutil.disk_usage(path).free

def refuse_if_low(path: Path) -> None:
    minimum = int(os.environ.get("HELPER_MIN_FREE_BYTES", DEFAULT_MIN_FREE_BYTES))
    free = bytes_free(path)
    if free < minimum:
        raise HTTPException(503, detail={"reason": "low_disk", "free": free, "min": minimum})
