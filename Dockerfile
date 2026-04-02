# =============================================================================
# Stage 1 — Builder
# Installs all Python dependencies into /build/venv so the runtime stage
# gets a clean, minimal layer without build tooling.
# =============================================================================
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        ca-certificates \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy dependency files first — heavy layer is cached as long as these don't change.
COPY pyproject.toml requirements.txt ./

RUN pip install --upgrade pip \
    && pip install --prefix=/build/venv --no-cache-dir -r requirements.txt

# Copy source and install the package (registers the doctor-assistant console script).
# --no-deps: all transitive deps already installed above.
COPY src/ ./src/
RUN pip install --prefix=/build/venv --no-cache-dir --no-deps -e .


# =============================================================================
# Stage 2 — Runtime
# =============================================================================
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 --no-create-home appuser

WORKDIR /app

# Copy installed packages and scripts from builder
COPY --from=builder /build/venv /usr/local

# Copy source (needed at runtime; editable install .pth points to this path)
COPY --chown=appuser:appuser src/ ./src/

# Copy data dir: pre-built FAISS vectorstores ship with the image
# but are overridden by the ./data bind-mount in docker-compose.yml
COPY --chown=appuser:appuser data/ ./data/

# Pre-create HuggingFace cache dir owned by appuser to avoid permission errors
# when the named volume is mounted on first run
RUN mkdir -p /home/appuser/.cache/huggingface \
    && chown -R appuser:appuser /home/appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    HF_HOME=/home/appuser/.cache/huggingface \
    TRANSFORMERS_CACHE=/home/appuser/.cache/huggingface \
    HF_HUB_DISABLE_PROGRESS_BARS=1

USER appuser

EXPOSE 7860

# start-period is generous: first run may need to download the ~90MB
# all-MiniLM-L6-v2 model if the HF cache volume is empty.
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:7860/ || exit 1

CMD ["doctor-assistant"]
