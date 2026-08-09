FROM python:3.12-slim

# Install curl for the healthcheck
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# WORKDIR must be /workspace so that uvicorn resolves `app.main` relative to /workspace.
# The docker-compose bind-mount ./app:/workspace/app is what enables --reload.
WORKDIR /workspace

COPY pyproject.toml ./

# Install packages directly via pip — bypasses uv_build entirely.
RUN pip install --no-cache-dir \
    "a2a-sdk[http-server]>=1.1.2" \
    "asyncpg>=0.30.0" \
    "fastapi>=0.115.0" \
    "httpx>=0.28.1" \
    "bcrypt>=4.0.0" \
    "PyJWT>=2.8.0" \
    "python-dotenv>=1.0.0" \
    "uvicorn[standard]>=0.52.1"

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
