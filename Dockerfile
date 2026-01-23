# syntax=docker/dockerfile:1
FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/martinhlavacek/bitbucket-mcp"
LABEL org.opencontainers.image.description="MCP server for Bitbucket Cloud API"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Install uv for faster dependency installation
RUN pip install --no-cache-dir uv

# Copy dependency specification first (for better layer caching)
COPY pyproject.toml ./

# Install dependencies only (will be cached if pyproject.toml unchanged)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system fastmcp httpx

# Copy source code (changes more frequently)
COPY README.md LICENSE ./
COPY src/ ./src/

# Install the package itself (quick, deps already installed)
RUN uv pip install --system --no-deps .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash mcp
USER mcp

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default: run HTTP server
ENTRYPOINT ["python", "-m", "bitbucket_mcp"]
CMD ["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]
