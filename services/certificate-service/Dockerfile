FROM python:3.11-slim AS base

RUN groupadd --system app && \
    useradd --system --gid app --home-dir /home/app --create-home app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
# Templates folder is shipped for the future real PDF generator.
COPY templates/ ./templates/

ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

USER app

EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
