# syntax=docker/dockerfile:1

# --- Builder: install into a venv the runtime image copies wholesale ---
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# No build-essential any more. It was here to compile what torch and
# sentence-transformers needed; embeddings now come from the Hugging Face API
# over httpx, and everything left in requirements.txt ships as a pure-Python or
# manylinux wheel. Adding a compiler back means something in that file changed.
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt

# --- Runtime ---
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# HF_HOME is gone with the local model: nothing downloads weights at runtime,
# so there is no cache directory to own and no first-request stall while a
# model is fetched. EMBEDDING_PROVIDER=local needs both back, along with
# requirements-local-models.txt.

RUN useradd --create-home --uid 1000 app
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=app:app app ./app
COPY --chown=app:app scripts ./scripts

USER app
EXPOSE 8000

# 90s of start period was the local model loading its weights. The API provider
# has nothing to load beyond one short probe request, so the service is ready in
# about as long as the interpreter takes to start.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/v1/health').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
