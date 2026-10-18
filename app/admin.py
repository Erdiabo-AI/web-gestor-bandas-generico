"""Administración (rol ADM): reglamentos, notificaciones, usuarios y copia de seguridad."""
import json
import secrets

from flask import (Blueprint, render_template, redirect, url_for, flash,
                   abort, request, Response)
from psycopg2.extras import Json

from . import db
from .auth import hash_token
from .helpers import admin_required, a_entero, definicion_stats, ahora_es

bp = Blueprint("admin", __name__, url_prefix="/admin")


# ---------------------------------------------------------------------------
#  Reglamentos (tabla reglas): CRUD con ventanas emergentes
# ---------------------------------------------------------------------------
@bp.route("/reglamentos")
@admin_required
def reglamentos():
    filas = db.query(
        """SELECT r.*, (SELECT count(*) FROM campanas c WHERE c.regla_id = r.regla_id) AS n_campanas
           FROM reglas r
           ORDER BY r.regla_descripcion, r.regla_anyo DESC"""
    )
    for r in filas:
        r["stats_ordenados"] = definicion_stats(r["regla_stats_especificos"], r["regla_info"])
    # Datos para rellenar el popup de edición (JSON seguro dentro de <script>)
    datos = {str(r["regla_id"]): {
        "descripcion": r["regla_descripcion"], "anyo": r["regla_anyo"],
        "version": r["regla_version"], "observaciones": r["regla_observaciones"] or "",
        "stats": json.dumps(r["stats_ordenados"] or {},
                            ensure_ascii=False),
    } for r in filas}
    return render_template("admin/reglamentos.html", reglas=filas, datos=datos)


def _stats_desde_form(texto):
    """Valida el JSON de stats: debe ser un objeto {"stat": valor_por_defecto}."""
    texto = (texto or "").strip()
    if not texto:
        return {}
    valor = json.loads(texto)          # ValueError si no es JSON
    if not isinstance(valor, dict):
        raise ValueError("debe ser un objeto {…}")
    return valor


@bp.route("/reglamentos/guardar", methods=["POST"])
@admin_required
def reglamento_guardar():
    f = request.form
    rid = f.get("regla_id") or None
    descripcion = (f.get("descripcion") or "").strip()[:150]
    version = (f.get("version") or "").strip()[:50]
    anyo = a_entero(f.get("anyo"), None)
    if not (descripcion and version and anyo):
        flash("Nombre del juego, año y versión son obligatorios.", "warning")
        return redirect(url_for("admin.reglamentos"))
    try:
        stats = _stats_desde_form(f.get("stats"))
    except ValueError as e:
        flash(f"El JSON de stats no es válido ({e}). Ejemplo: "
              '{"m": 4, "ha": 4, "hp": 3}', "danger")
        return redirect(url_for("admin.reglamentos"))
    # jsonb reordena las claves: el orden escrito se guarda en regla_info
    valores = (anyo, descripcion, version,
               (f.get("observaciones") or "").strip()[:255] or None, Json(stats),
               Json({"orden_stats": list(stats)}))
    if rid:
        db.execute(
            """UPDATE reglas SET regla_anyo=%s, regla_descripcion=%s, regla_version=%s,
                   regla_observaciones=%s, regla_stats_especificos=%s,
                   regla_info = COALESCE(regla_info, '{}'::jsonb) || %s
               WHERE regla_id=%s""", valores + (rid,))
        flash("Reglamento actualizado.", "success")
    else:
        db.execute(
            """INSERT INTO reglas (regla_anyo, regla_descripcion, regla_version,
                   regla_observaciones, regla_stats_especificos, regla_info)
               VALUES (%s, %s, %s, %s, %s, %s)""", valores)
        flash("Reglamento creado.", "success")
    return redirect(url_for("admin.reglamentos"))


@bp.route("/reglamentos/<uuid:rid>/borrar", methods=["POST"])
@admin_required
def reglamento_borrar(rid):
    usado = db.query("SELECT count(*) AS n FROM campanas WHERE regla_id = %s", (str(rid),), one=True)
    if usado and usado["n"]:
        flash("No se puede eliminar: hay campañas que usan este reglamento.", "warning")
    else:
        db.execute("DELETE FROM reglas WHERE regla_id = %s", (str(rid),))
        flash("Reglamento eliminado.", "info")
    return redirect(url_for("admin.reglamentos"))


# ---------------------------------------------------------------------------
#  Notificaciones al administrador (contacto + recuperación de contraseña).
#  Los mensajes a comisarios (campana_id con valor) se ven en Gestión de campañas.
# ---------------------------------------------------------------------------
@bp.route("/notificaciones")
@admin_required
def notificaciones():
    notifs = db.query(
        """SELECT n.*, u.usuario_nombre
           FROM notificaciones n
           LEFT JOIN usuarios u ON u.usuario_id = n.usuario_id
           WHERE n.campana_id IS NULL
           ORDER BY n.leida, n.fecha DESC
           LIMIT 200"""
    )
    return render_template("admin/notificaciones.html", notifs=notifs)


@bp.route("/notificaciones/<uuid:nid>/leida", methods=["POST"])
@admin_required
def notificacion_leida(nid):
    db.execute("UPDATE notificaciones SET leida = TRUE WHERE notificacion_id = %s", (str(nid),))
    return redirect(url_for("admin.notificaciones"))


@bp.route("/notificaciones/<uuid:nid>/borrar", methods=["POST"])
@admin_required
def notificacion_borrar(nid):
    db.execute("DELETE FROM notificaciones WHERE notificacion_id = %s", (str(nid),))
    flash("Notificación eliminada.", "info")
    return redirect(url_for("admin.notificaciones"))


@bp.route("/notificaciones/leidas", methods=["POST"])
@admin_required
def notificaciones_leidas():
    db.execute("UPDATE notificaciones SET leida = TRUE WHERE leida = FALSE AND campana_id IS NULL")
    flash("Todas las notificaciones marcadas como leídas.", "info")
    return redirect(url_for("admin.notificaciones"))


# ---------------------------------------------------------------------------
#  Usuarios: enlace de recuperación (la tabla está en Gestión de campañas · Bloque 3)
# ---------------------------------------------------------------------------
@bp.route("/usuarios/<uuid:usuario_id>/reset", methods=["POST"])
@admin_required
def generar_reset(usuario_id):
    """Genera un enlace de recuperación de contraseña de un solo uso (24h)."""
    user = db.query("SELECT usuario_nombre FROM usuarios WHERE usuario_id = %s",
                    (str(usuario_id),), one=True)
    if not user:
        abort(404)
    token = secrets.token_urlsafe(32)
    db.execute(
        """UPDATE usuarios SET reset_token_hash = %s,
               reset_expira = now() + interval '24 hours'
           WHERE usuario_id = %s""",
        (hash_token(token), str(usuario_id)),
    )
    enlace = url_for("auth.restablecer", token=token, _external=True)
    flash(f"Enlace de recuperación para {user['usuario_nombre']} (válido 24 h): {enlace}",
          "info")
    return redirect(url_for("campanas.gestion_campanas") + "#bloque-3")


# ---------------------------------------------------------------------------
#  Copia de seguridad
# ---------------------------------------------------------------------------
@bp.route("/backup.sql")
@admin_required
def backup_sql():
    """Copia de seguridad de la BBDD: volcado SQL con INSERT de todas las
    tablas, en orden compatible con las claves ajenas. Se restaura sobre un
    esquema vacío creado con db/schema.sql."""
    import psycopg2.extras as pgx
    import psycopg2.extensions as pgext

    pgx.register_uuid()                      # los UUID se vuelcan como texto
    pgext.register_adapter(dict, pgx.Json)   # los JSONB se vuelcan como json
    pgext.register_adapter(list, pgx.Json)

    conn = db.get_db()
    cur = conn.cursor()  # cursor plano: mogrify() genera los literales SQL

    # Tablas y dependencias (FK) para ordenar el volcado topológicamente
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    tablas = sorted(r[0] for r in cur.fetchall())
    cur.execute(
        """SELECT conrelid::regclass::text, confrelid::regclass::text
           FROM pg_constraint
           WHERE contype = 'f' AND connamespace = 'public'::regnamespace""")
    deps = {}   # tabla -> {tablas de las que depende}
    for hija, madre in cur.fetchall():
        if hija != madre:
            deps.setdefault(hija, set()).add(madre)
    orden = []
    pendientes = set(tablas)
    while pendientes:
        listas = sorted(t for t in pendientes
                        if not (deps.get(t, set()) & pendientes))
        if not listas:           # ciclo entre tablas (no debería darse)
            listas = sorted(pendientes)
        orden.extend(listas)
        pendientes -= set(listas)

    ahora = ahora_es()
    lineas = [
        f"-- Copia de seguridad gestorbandasgenerico · {ahora:%d/%m/%Y %H:%M}",
        "-- Restaurar sobre un esquema VACÍO creado con db/schema.sql:",
        "--   psql \"$DATABASE_URL\" -f db/schema.sql",
        "--   psql \"$DATABASE_URL\" -f esta_copia.sql",
        "BEGIN;",
    ]
    total = 0
    for tabla in orden:
        cur.execute(f'SELECT * FROM "{tabla}"')
        cols = [d.name for d in cur.description]
        filas = cur.fetchall()
        if not filas:
            continue
        lineas.append(f"\n-- {tabla} ({len(filas)} filas)")
        plantilla = "(" + ",".join(["%s"] * len(cols)) + ")"
        for fila in filas:
            lineas.append(
                f'INSERT INTO "{tabla}" ({", ".join(cols)}) VALUES '
                + cur.mogrify(plantilla, list(fila)).decode() + ";")
            total += 1
    lineas.append(f"\nCOMMIT;\n-- {total} filas en total")

    nombre = f"gestorbandas_backup_{ahora:%Y%m%d_%H%M}.sql"
    return Response(
        "\n".join(lineas), mimetype="application/sql",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'})
