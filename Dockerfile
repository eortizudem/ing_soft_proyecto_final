FROM python:3.12-slim
# WEB_CONCURRENCY = procesos de gunicorn (una por nucleo; docker-compose.yml la pasa desde el entorno)
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 WEB_CONCURRENCY=4
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ /app/app/
COPY conftest.py pytest.ini /app/
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health', timeout=3)"
CMD ["gunicorn", "-b", "0.0.0.0:8000", "--timeout", "30", "--access-logfile", "-", "app:create_app()"]
