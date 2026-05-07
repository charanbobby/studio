FROM python:3.12-slim

# ffmpeg for the Stitch node
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# uv: faster than pip per global rules
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/

RUN uv pip install --system --no-cache -e ".[dev]"

EXPOSE 8000

# Liveness check used by docker-compose and nginx
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/healthz', timeout=2).raise_for_status()" || exit 1

CMD ["uvicorn", "reel_gen.api:app", "--host", "0.0.0.0", "--port", "8000"]
