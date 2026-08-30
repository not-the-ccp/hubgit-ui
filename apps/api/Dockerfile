FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HUBGIT_ENVIRONMENT=production \
    HUBGIT_DATABASE_URL=sqlite+aiosqlite:////data/hubgit.db \
    HUBGIT_PUBLIC_BASE_URL=https://localhost \
    HUBGIT_CORS_ORIGINS=https://localhost \
    HUBGIT_COOKIE_SECURE=true \
    HUBGIT_SEED_MOCK_USER=false

WORKDIR /app/apps/api
COPY apps/api /app/apps/api
RUN useradd --create-home --uid 10001 hubgit \
    && mkdir /data \
    && chown -R hubgit:hubgit /app /data \
    && pip install --no-cache-dir .

USER hubgit
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/healthz', timeout=2).read()"
CMD ["uvicorn", "hubgit_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
