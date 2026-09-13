# ============================================================
# Mwalimu AI - Dockerfile
# ============================================================

FROM python:3.12-slim

WORKDIR /app

# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Ensure logs are written directly to stdout/stderr
ENV PYTHONUNBUFFERED=1

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files first to improve Docker layer caching
COPY pyproject.toml uv.lock ./

# Install project dependencies using the lockfile
RUN uv sync --frozen --no-dev

# Copy application source code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Run the application through uv
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]