"""Entrypoint serverless para Vercel (@vercel/python detecta la variable `app`)."""
import os
import sys

# Permite importar el paquete `app` desde la raíz del proyecto.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402

_flask_app = create_app()

# Cabeceras donde el proxy de Vercel puede dejar la ruta ORIGINAL cuando el
# rewrite /(.*) -> /api/index entrega la petición con PATH_INFO=/api/index
# (comportamiento del runtime de Python a partir de 2026-07; antes llegaba la
# ruta original directamente).
_CANDIDATAS = ("HTTP_X_VERCEL_ORIGINAL_PATH", "HTTP_X_ORIGINAL_PATH",
               "HTTP_X_FORWARDED_URI", "HTTP_X_REWRITE_URL")


@_flask_app.route("/api/index")
def _ruta_perdida():
    """Si una petición llega aquí es que el proxy no entregó la ruta original
    (incidencia del runtime de Vercel de 2026-08). Aviso en lugar de 404."""
    return ("<h1>Mantenimiento</h1><p>Estamos restaurando el servicio. "
            "Vuelve a intentarlo en unos minutos.</p>", 503)


def app(environ, start_response):
    """WSGI intermedio: restaura la ruta original antes de entrar en Flask."""
    path = environ.get("PATH_INFO", "")
    if path.startswith("/api/index"):
        nuevo = None
        for cab in _CANDIDATAS:
            valor = environ.get(cab)
            if valor:
                nuevo = valor.split("?", 1)[0]
                break
        if nuevo is None:
            # Formato antiguo x-now-route-matches: "1=<ruta-codificada>"
            m = environ.get("HTTP_X_NOW_ROUTE_MATCHES")
            if m:
                from urllib.parse import parse_qs, unquote
                grupos = parse_qs(m)
                if "1" in grupos:
                    nuevo = "/" + unquote(grupos["1"][0]).lstrip("/")
        if nuevo and not nuevo.startswith("/api/index"):
            environ["PATH_INFO"] = nuevo
    return _flask_app(environ, start_response)
