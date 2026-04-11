# Multi-stage build keeps the final image small and excludes pip cache.
FROM python:3.11-slim AS base

# Non-root runtime user — least privilege at the container level.
RUN groupadd --system app && \
    useradd --system --gid app --home-dir /home/app --create-home app

WORKDIR /app

# Install Python dependencies as root for layer caching, then drop privileges.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source. Tests are intentionally NOT copied — the runtime
# image should not ship test code or fixtures.
COPY app/ ./app/

# Cloud Run injects PORT but defaults to 8080 locally.
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

USER app

EXPOSE 8080

# Cloud Run sets PORT — uvicorn binds to it via shell expansion.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
