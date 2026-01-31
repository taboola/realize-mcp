FROM python:3.11-slim

WORKDIR /app

# Install dependencies from pyproject.toml (layer caching)
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir .

# Copy source and reinstall (picks up the actual code)
COPY src/ ./src/
RUN pip install --no-cache-dir .

# Run as non-root
RUN useradd -m -u 1001 appuser
USER appuser

EXPOSE 8000

CMD ["realize-mcp-server"]