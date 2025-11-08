FROM python:3.13.2-slim-bullseye
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1

# Copy project files first (pyproject.toml and uv.lock at root)
COPY pyproject.toml uv.lock /app/
COPY backend/ /app/backend/
COPY images/ /app/images/

# Install dependencies and sync the project
# Use --frozen only if uv.lock exists, otherwise just sync
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ -f uv.lock ]; then \
        uv sync --frozen; \
    else \
        uv sync; \
    fi

ENV PYTHONUNBUFFERED=1

# Run the server
CMD ["uv", "run", "sanic", "backend.server:app", "-H", "0.0.0.0", "--port", "8000", "--fast", "--access-logs"]

