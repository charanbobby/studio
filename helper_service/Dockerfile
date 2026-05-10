FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

# Existing deps from sri_studio_helper/Dockerfile
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
      ffmpeg fonts-ibm-plex \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --quiet uv

# NEW: service deps via uv (per project rule)
RUN uv pip install --system --no-cache \
      fastapi "uvicorn[standard]" python-multipart aiofiles httpx pydantic

# Ship the existing CLI package + the new service package
COPY sri_studio_helper/ /app/sri_studio_helper/
COPY helper_service/    /app/helper_service/
COPY SKILL.md           /app/SKILL.md

RUN mkdir -p /data/jobs /data/samples

WORKDIR /app
ENV HELPER_SKILL_PATH=/app/SKILL.md
EXPOSE 8000
CMD ["python", "-m", "helper_service"]
