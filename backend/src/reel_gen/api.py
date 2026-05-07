"""FastAPI app entry point. Routes get added in Phase 4."""
from fastapi import FastAPI

app = FastAPI(title="Sri Studio API", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "sri-studio-backend"}
