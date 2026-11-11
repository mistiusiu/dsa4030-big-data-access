# syntax=docker/dockerfile:1

# ── STAGE 1: BASE ──────────────────────────────────────────
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app/backend

# ── STAGE 2: BUILDER ────────────────────────────────────────
# Poetry lives here only; it never reaches the runtime image.
FROM base AS builder

# Generous timeouts/retries and fewer parallel downloads: large wheels
# (pyarrow, duckdb) otherwise time out on slow links.
ENV POETRY_VERSION=2.2.1 \
    POETRY_REQUESTS_TIMEOUT=300 \
    POETRY_REQUESTS_MAX_RETRIES=5 \
    POETRY_INSTALLER_MAX_WORKERS=2 \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=5 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=true \
    POETRY_VIRTUALENVS_IN_PROJECT=true

RUN --mount=type=cache,target=/root/.cache/pip pip install "poetry==$POETRY_VERSION"

COPY pyproject.toml poetry.lock* ./

FROM builder AS prod-deps
RUN --mount=type=cache,target=/root/.cache/pypoetry poetry install --only main --no-root

FROM builder AS dev-deps
RUN --mount=type=cache,target=/root/.cache/pypoetry poetry install --no-root

# ── STAGE 3: DEVELOPMENT (tests, linting) ───────────────────
FROM dev-deps AS development
ENV PATH="/app/backend/.venv/bin:$PATH" VIRTUAL_ENV="/app/backend/.venv"
COPY . .
COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ── STAGE 4: PRODUCTION (default) ───────────────────────────
FROM base AS production

RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid 1000 --no-create-home --shell /usr/sbin/nologin app

COPY --from=prod-deps /app/backend/.venv /app/backend/.venv
ENV PATH="/app/backend/.venv/bin:$PATH" VIRTUAL_ENV="/app/backend/.venv"

COPY . .
# Writable state lives on volumes: the lake, the JWT keys and the audit file.
# The code directory stays root-owned so the app user cannot modify itself.
RUN mkdir -p /data/lake /data/keys /data/logs /data/static \
    && chown -R 1000:1000 /data

COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

USER 1000
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "4", "--timeout", "60", "--access-logfile", "-"]
