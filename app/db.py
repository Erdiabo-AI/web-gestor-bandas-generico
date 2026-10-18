"""Acceso a PostgreSQL con psycopg2.

Diseñado para entornos serverless (Vercel): una conexión por petición, cerrada
al terminar. Si no hay DATABASE_URL configurada, las consultas devuelven vacío en
lugar de fallar, para que el esqueleto pueda arrancar sin base de datos.
"""
from flask import current_app, g

try:
    import psycopg2
    import psycopg2.extras
    _HAS_PG = True
except ImportError:  # permite importar el módulo aunque psycopg2 no esté instalado
    _HAS_PG = False


def get_db():
    if "db" in g:
        return g.db
    url = current_app.config.get("DATABASE_URL")
    if not url or not _HAS_PG:
        g.db = None
        return None
    g.db = psycopg2.connect(url)
    return g.db


def query(sql, params=None, one=False):
    """Ejecuta un SELECT. Devuelve lista de dicts (o un dict si one=True)."""
    conn = get_db()
    if conn is None:
        return None if one else []
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            rows = cur.fetchall() if cur.description else []
        return (rows[0] if rows else None) if one else rows
    except psycopg2.Error:
        conn.rollback()
        return None if one else []


def execute(sql, params=None, returning=False, commit=True):
    """Ejecuta INSERT/UPDATE/DELETE. Con returning=True devuelve la primera fila.

    Con commit=False la sentencia queda en la transacción abierta: varias
    operaciones encadenadas se confirman juntas en la última con commit=True
    (si algo falla antes, close_db cierra la conexión sin confirmar nada)."""
    conn = get_db()
    if conn is None:
        raise RuntimeError("No hay DATABASE_URL configurada")
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params or ())
        row = cur.fetchone() if (returning and cur.description) else None
    if commit:
        conn.commit()
    return row


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
