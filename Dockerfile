# Imagen de la aplicacion web LibriGest (Flask servido con gunicorn). La base de datos corre en otro servicio (docker-compose.yml).
FROM python:3.12-slim
# WEB_CONCURRENCY = procesos de gunicorn (una por nucleo; docker-compose.yml la pasa desde el entorno)
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 WEB_CONCURRENCY=4
# (ENV de arriba: salida sin buffer para logs en tiempo real y sin escribir .pyc)
WORKDIR /app
# requirements primero: la capa de dependencias se reutiliza mientras no cambien
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Codigo de la aplicacion y configuracion de pruebas (permite correr pytest dentro del contenedor)
COPY app/ /app/app/
COPY conftest.py pytest.ini /app/
# Puerto interno de gunicorn (docker-compose lo publica en el host)
EXPOSE 8000
# Salud: GET /api/health debe responder 2xx; compose y levantar.py dependen de ello
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health', timeout=3)"
# Arranque: gunicorn con factory create_app(); --timeout 30 s por peticion, log de accesos a stdout.
# Numero de procesos: variable WEB_CONCURRENCY (la lee gunicorn)
CMD ["gunicorn", "-b", "0.0.0.0:8000", "--timeout", "30", "--access-logfile", "-", "app:create_app()"]
