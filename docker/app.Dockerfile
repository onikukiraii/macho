# syntax=docker/dockerfile:1

FROM node:22-slim AS frontend

ARG VITE_VAPID_PUBLIC_KEY
ENV VITE_API_BASE_URL=""
ENV VITE_VAPID_PUBLIC_KEY=${VITE_VAPID_PUBLIC_KEY}

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_NO_DEV=1
ENV FRONTEND_DIST_DIR=/app/dist

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-install-project
COPY backend/ ./
RUN uv sync --frozen
COPY --from=frontend /frontend/dist ./dist

EXPOSE 8000

CMD ["uv", "run", "fastapi", "run", "--host", "0.0.0.0", "--port", "8000"]
