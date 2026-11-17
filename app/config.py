"""Configuración de la aplicación leida de variables de entorno (BD, sesión, parámetros de negocio)."""
import os


def _bandera(nombre, defecto):
    """Variable de entorno booleana: 1/true/si/yes/on -> True."""
    valor = os.environ.get(nombre)
    return defecto if valor is None else valor.strip().lower() in ("1", "true", "si", "sí", "yes", "on")


# HTTPS=true: la app corre detrás de un proxy con TLS (docs/operacion.md); la cookie de sesión solo viaja cifrada.
_HTTPS = _bandera("HTTPS", False)


class Config:
    """Valores de configuración de Flask; cada uno se puede sobrescribir con su variable de entorno.

    `PERMANENT_SESSION_LIFETIME` está en segundos (12 horas).
    """
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://librigest:librigest@localhost:5432/librigest")
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _HTTPS
    PREFERRED_URL_SCHEME = "https" if _HTTPS else "http"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 12

    # Parámetros de negocio (D-07, D-22, D-19). Se leen con app/core/parametros.py, no directo.
    TIPO_CAMBIO_USD_MXN = os.environ.get("TIPO_CAMBIO_USD_MXN", "18.00")      # simulado Banxico/FIX
    PRESUPUESTO_MENSUAL_USD = os.environ.get("PRESUPUESTO_MENSUAL_USD", "5000")
    ESPERA_DIAS_RESERVA = os.environ.get("ESPERA_DIAS_RESERVA", "2")       # días hábiles

    # Seguridad (PS-S4-03 / PS-NFR-05): en demostración la API devuelve el código de recuperación en la respuesta
    # (no hay servidor de correo). Con DEMO_MOSTRAR_TOKEN=false solo responde ok:true y el código se
    # registra como correo simulado en la lista de avisos.
    DEMO_MOSTRAR_TOKEN = _bandera("DEMO_MOSTRAR_TOKEN", True)

    # Asistente con IA (D-13): LLM pequeño y local servido por Ollama (contenedor `ollama`). Si ASISTENTE_IA es falso o
    # Ollama no responde, el asistente usa sus reglas (app/core/ia.py y modules/asistente/service.py).
    ASISTENTE_IA = _bandera("ASISTENTE_IA", True)
    OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:1.5b")
    OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "20"))     # segundos por respuesta
