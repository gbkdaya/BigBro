FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Agent code, templates, and your custom capabilities
COPY . .

# In the container the dashboard must listen on 0.0.0.0 to be reachable;
# the host-side port mapping (docker-compose) keeps it bound to 127.0.0.1.
ENV BIGBRO_WORKSPACE=/app/workspace \
    BIGBRO_HOST=0.0.0.0 \
    BIGBRO_PORT=8321

EXPOSE 8321

# Projects, transcripts and notes survive container rebuilds
VOLUME ["/app/workspace"]

# / is the login page (no auth needed to reach the gate itself)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8321/', timeout=3)" || exit 1

# Web dashboard by default. For CLI:  docker compose run --rm bigbro python -m bigbro.cli
CMD ["python", "-m", "bigbro.web"]
