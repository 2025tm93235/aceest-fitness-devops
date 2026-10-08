# ACEest Fitness & Gym - multi-stage container build
#
#   base     : slim Python image + common environment
#   builder  : installs pinned runtime dependencies into an isolated virtualenv
#   test     : builder + dev tooling + sources; runs lint/pytest in CI & Jenkins
#   runtime  : (default) minimal, non-root production image served by gunicorn
#
# Build production image : docker build -t aceest-fitness .
# Build & run tests      : docker build --target test -t aceest-fitness:test . \
#                          && docker run --rm aceest-fitness:test

ARG PYTHON_IMAGE=python:3.13-slim-trixie

# ------------------------------------------------------------------ base ----
FROM ${PYTHON_IMAGE} AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

# --------------------------------------------------------------- builder ----
FROM base AS builder

RUN python -m venv "${VIRTUAL_ENV}"

# Copy only the dependency manifest first so this layer stays cached
# until requirements.txt changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

# ------------------------------------------------------------------ test ----
FROM builder AS test

COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt

COPY . .

CMD ["python", "-m", "pytest"]

# --------------------------------------------------------------- runtime ----
FROM base AS runtime

LABEL org.opencontainers.image.title="aceest-fitness" \
      org.opencontainers.image.description="ACEest Fitness & Gym Flask application" \
      org.opencontainers.image.licenses="MIT"

# Unprivileged system user; only the data directory is writable by it.
RUN groupadd --system --gid 10001 aceest \
    && useradd --system --uid 10001 --gid aceest --no-create-home \
       --home-dir /nonexistent --shell /usr/sbin/nologin aceest \
    && mkdir -p /app/instance \
    && chown aceest:aceest /app/instance

COPY --from=builder /opt/venv /opt/venv
COPY app.py ./
COPY aceest ./aceest

ENV ACEEST_DB_PATH=/app/instance/aceest.db

USER aceest

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=4).status == 200 else 1)"]

# --no-control-socket: the admin control socket is not needed and would
# otherwise try to write into the (non-existent) home directory.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--preload", \
     "--worker-tmp-dir", "/dev/shm", "--no-control-socket", \
     "--access-logfile", "-", "app:app"]
