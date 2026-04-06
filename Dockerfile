# syntax=docker/dockerfile:1

FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

COPY src/ /app/src/

# Default: run CLI (override in compose or with `docker run ... cmd`)
CMD ["python", "-m", "logiclock.cli"]
