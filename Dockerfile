# Oil Session Radar — Institutional Desk
# Container image for Hugging Face Spaces (Docker SDK) or any container host.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data

# Hugging Face Spaces (Docker) expects the app on port 7860.
EXPOSE 7860

# NOTE ON SSE + gunicorn workers:
# /stream holds a long-lived Server-Sent-Events connection per client. Such
# connections don't load-balance across workers cleanly, and the in-memory
# snapshot / tick thread live in one process. We therefore run a SINGLE worker
# with a threaded worker class so many concurrent SSE clients share one
# process (and one authoritative snapshot) while normal requests still get
# their own threads. Scale out later with a shared store (Redis) + sticky
# routing if you need multiple workers.
CMD ["gunicorn", "--worker-class", "gthread", "--workers", "1", "--threads", "16", \
     "--timeout", "0", "--bind", "0.0.0.0:7860", "app:app"]
