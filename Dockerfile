# Multi-stage build: frontend + backend

# Stage 1: Build frontend
FROM node:25-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Stage 2: Python backend
FROM python:3.12-slim AS backend
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
COPY backend/ backend/
RUN pip install --no-cache-dir -e ".[all]" || pip install --no-cache-dir -e .

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist /app/static

# Expose ports
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Start the server
CMD ["uvicorn", "netopshub.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
