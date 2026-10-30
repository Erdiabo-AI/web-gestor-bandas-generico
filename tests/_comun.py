"""Utilidades comunes de las pruebas.

ATENCIÓN: las pruebas usan la BBDD de .env (la de Neon del proyecto). Crean datos
temporales con usuarios @e2e.test y campañas/reglamentos con un sufijo propio de
cada prueba, y los borran al terminar (también si la prueba falla).
Uso:  .venv\\Scripts\\python tests\\ejecutar_todo.py
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

import psycopg2  # noqa: E402
from app import create_app  # noqa: E402

DOM = "@e2e.test"
CLAVE = "clave-e2e-123"

app = create_app()
app.testing = True
_cx = psycopg2.connect(app.config["DATABASE_URL"])
_cx.autocommit = True
cur = _cx.cursor()
FALLOS = []


def ok(cond, msg):
    print(("OK  " if cond else "FAIL"), msg)
    if not cond:
        FALLOS.append(msg)


def one(sql, *p):
    cur.execute(sql, p)
    r = cur.fetchone()
    return r[0] if r and len(r) == 1 else r


def txt(r):
    return r.get_data(as_text=True)


def cliente(nombre, adm=False):
    """Registra (si hace falta) e inicia sesión con un usuario de prueba."""
    email = nombre.lower() + DOM
    c = app.test_client()
    c.post("/registro", data={"nombre": nombre, "email": email, "password": CLAVE})
    if adm:
        cur.execute("UPDATE usuarios SET usuario_rol = 'ADM' WHERE usuario_email = %s", (email,))
    c.post("/login", data={"email": email, "password": CLAVE})
    return c


def limpiar(sufijo_campana, patron_reglas):
    """Borra campañas (en cascada), reglamentos y usuarios de prueba."""
    cur.execute("DELETE FROM campanas WHERE campana_nombre LIKE %s", ("%" + sufijo_campana,))
    cur.execute("DELETE FROM reglas WHERE regla_descripcion LIKE %s", (patron_reglas,))
    cur.execute("DELETE FROM notificaciones WHERE remitente_email LIKE %s", ("%" + DOM,))
    cur.execute("DELETE FROM usuarios WHERE usuario_email LIKE %s", ("%" + DOM,))


def resultado():
    print("\nRESULTADO:", "TODO OK" if not FALLOS else f"{len(FALLOS)} FALLOS: {FALLOS}")
    return 0 if not FALLOS else 1
