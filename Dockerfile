FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 AGENT_DEMO_DATA_ROOT=/app
WORKDIR /app
COPY requirements-linux.txt /app/requirements-linux.txt
RUN python -m pip install --no-cache-dir -r requirements-linux.txt
COPY pyproject.toml README.md /app/
COPY src /app/src
RUN python -m pip install --no-cache-dir --no-deps . \
    && useradd --uid 10001 --create-home agent \
    && mkdir -p /app/runtime /app/outputs /app/data/private \
    && chown -R agent:agent /app/runtime /app/outputs /app/data
USER agent
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=15s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=2)"
CMD ["python", "-m", "uvicorn", "agent_demo.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
