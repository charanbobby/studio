import httpx
from .config import base_url, auth_key

class HelperError(Exception): pass
class BudgetExceeded(HelperError):
    def __init__(self, remaining: float, needed: float):
        self.remaining = remaining; self.needed = needed
        super().__init__(f"would exceed daily cap; need ${needed:.4f}, have ${remaining:.4f}")
class HelperUnreachable(HelperError): pass

class HelperClient:
    def __init__(self):
        self._base = base_url()
        self._headers = {"X-Helper-Key": auth_key()}
        self._client = httpx.Client(timeout=600)

    def post_silent(self, tarball: bytes, auto_approve: bool = False) -> dict:
        try:
            r = self._client.post(
                f"{self._base}/helper/jobs",
                params={"auto_approve": str(auto_approve).lower()},
                files={"project": ("project.tar.gz", tarball, "application/gzip")},
                headers=self._headers,
            )
        except httpx.HTTPError as e:
            raise HelperUnreachable(str(e))
        if r.status_code == 200:
            return r.json()
        raise HelperError(f"helper {r.status_code}: {r.text[:200]}")

    def post_voice(self, job_id: str) -> dict:
        r = self._client.post(f"{self._base}/helper/jobs/{job_id}/voice",
                              headers=self._headers)
        if r.status_code == 402:
            d = r.json()["detail"]
            raise BudgetExceeded(d["remaining"], d["needed"])
        if r.status_code == 200:
            return r.json()
        raise HelperError(f"helper {r.status_code}: {r.text[:200]}")

    def get_skill(self) -> str:
        r = self._client.get(f"{self._base}/helper/skill")
        r.raise_for_status()
        return r.text

    def get_job(self, job_id: str) -> dict:
        r = self._client.get(f"{self._base}/helper/jobs/{job_id}",
                             headers=self._headers)
        r.raise_for_status()
        return r.json()
