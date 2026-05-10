import pytest
from helper_service.disk import bytes_free, refuse_if_low

def test_bytes_free_returns_positive_int(tmp_path):
    assert bytes_free(tmp_path) > 0

def test_refuse_if_low_passes_when_room(tmp_path, monkeypatch):
    monkeypatch.setenv("HELPER_MIN_FREE_BYTES", "1")
    refuse_if_low(tmp_path)  # no raise

def test_refuse_if_low_raises_503_when_low(tmp_path, monkeypatch):
    monkeypatch.setenv("HELPER_MIN_FREE_BYTES", str(10**18))  # impossibly large
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        refuse_if_low(tmp_path)
    assert exc.value.status_code == 503
