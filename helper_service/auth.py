import os
from fastapi import Header, HTTPException, status

def require_helper_key(x_helper_key: str | None = Header(default=None)) -> None:
    expected = os.environ.get("HELPER_AUTH_KEY")
    if not expected:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "HELPER_AUTH_KEY not configured")
    if not x_helper_key or x_helper_key != expected:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "missing or invalid X-Helper-Key")
