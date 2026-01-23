# syntax=docker/dockerfile:1
FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/martinhlavacek/bitbucket-mcp"
LABEL org.opencontainers.image.description="MCP server for Bitbucket Cloud API"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Install uv for faster dependency installation
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

# Install dependencies with uv
RUN uv pip install --system .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash mcp
USER mcp

# Default port
ENV BITBUCKET_MCP_PORT=8000
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default: run HTTP server
ENTRYPOINT ["python", "-m", "bitbucket_mcp"]
CMD ["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]
