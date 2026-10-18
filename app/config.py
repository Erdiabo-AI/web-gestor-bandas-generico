import os
import secrets

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # dotenv es opcional (en Vercel se usan las env vars del panel)
    pass


class Config:
    # Sin SECRET_KEY en el entorno se genera una aleatoria por proceso:
    # las sesiones no sobreviven a un reinicio, pero nunca son falsificables.
    # En producción (Vercel) define SIEMPRE la variable SECRET_KEY.
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    DATABASE_URL = os.environ.get("DATABASE_URL")
    # Título mostrado en la cabecera
    APP_NAME = os.environ.get("APP_NAME", "Gestor de Fichas de control para campañas genérico")
