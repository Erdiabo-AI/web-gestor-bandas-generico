"""Batallas y actas.

Las actas son INFORMATIVAS (decisión H2): registran las bandas implicadas,
sus ganancias, las bajas y el ganador, pero no modifican las bandas.
Estados: 0 Borrador (editable) · 1 Confirmada (solo el comisario la reabre).
"""
from datetime import date

import psycopg2
from flask import (Blueprint, render_template, request, redirect, url_for,
                   session, flash, abort)
from psycopg2.extras import Json

from . import db
from .helpers import login_required, es_comisario, a_entero, ESTADOS_BATALLA

bp = Blueprint("batallas", __name__)


def _banda_activa_usuario(campana_id, uid):
    return db.query(
        """SELECT b.banda_id, b.banda_nombre FROM bandas b
           JOIN campanas_usuarios cu ON cu.campana_usuario_id = b.campana_usuario_id
           WHERE b.campana_id = %s AND cu.usuario_id = %s AND b.banda_estado = 1""",
        (str(campana_id), uid), one=True)


@bp.route("/campana/<uuid:campana_id>/batallas/crear", methods=["POST"])
@login_required
def crear(campana_id):
    user = session["user"]
    c = db.query("SELECT campana_id, campana_estado FROM campanas WHERE campana_id = %s",
                 (str(campana_id),), one=True)
    if not c:
        abort(404)
    com = es_comisario(campana_id, user)
    propia = _banda_activa_usuario(campana_id, user["id"])
    if not (com or propia):
        flash("Necesitas una banda activa en la campaña para crear una batalla.", "warning")
        return redirect(url_for("public.batallas", campana_id=campana_id))
    if c["campana_estado"] == "CERRADA" and not com:
        flash("La campaña está cerrada.", "warning")
        return redirect(url_for("public.batallas", campana_id=campana_id))
    try:
        row = db.execute(
            """INSERT INTO batallas (campana_id, batalla_orden, batalla_escenario, batalla_fecha)
               VALUES (%s, (SELECT COALESCE(MAX(batalla_orden), 0) + 1 FROM batallas WHERE campana_id = %s),
                       'Por definir', %s)
               RETURNING batalla_id""",
            (str(campana_id), str(campana_id), date.today()), returning=True, commit=False)
        if propia:
            db.execute("INSERT INTO batallas_bandas (batalla_id, banda_id) VALUES (%s, %s)",
                       (str(row["batalla_id"]), str(propia["banda_id"])), commit=False)
        db.get_db().commit()
    except psycopg2.IntegrityError:   # dos altas simultáneas con el mismo orden
        db.get_db().rollback()
        flash("No se pudo crear la batalla, inténtalo de nuevo.", "danger")
        return redirect(url_for("public.batallas", campana_id=campana_id))
    return redirect(url_for("batallas.acta", batalla_id=row["batalla_id"]))


def _batalla(batalla_id):
    bt = db.query(
        """SELECT bt.*, c.campana_nombre, c.usuarios_gestor_id, c.usuarios_gestor_suplente_id
           FROM batallas bt JOIN campanas c ON c.campana_id = bt.campana_id
           WHERE bt.batalla_id = %s""", (str(batalla_id),), one=True)
    if not bt:
        abort(404)
    return bt


def _implicadas(batalla_id):
    return db.query(
        """SELECT bb.*, b.banda_nombre, b.banda_tipo, cu.usuario_id, u.usuario_nombre
           FROM batallas_bandas bb
           JOIN bandas b ON b.banda_id = bb.banda_id
           LEFT JOIN campanas_usuarios cu ON cu.campana_usuario_id = b.campana_usuario_id
           LEFT JOIN usuarios u ON u.usuario_id = cu.usuario_id
           WHERE bb.batalla_id = %s ORDER BY b.banda_nombre""", (str(batalla_id),))


def _permisos(bt, implicadas):
    """(es_comisario, puede_editar). Edita el comisario, o un participante cuya
    banda está implicada, siempre que el acta siga en borrador."""
    user = session.get("user")
    com = es_comisario(bt["campana_id"], user)
    participa = bool(user) and any(str(i["usuario_id"]) == user["id"] for i in implicadas)
    return com, bt["batalla_estado"] == 0 and (com or participa)


@bp.route("/batalla/<uuid:batalla_id>/acta", methods=["GET", "POST"])
def acta(batalla_id):
    bt = _batalla(batalla_id)
    implicadas = _implicadas(batalla_id)
    com, puede_editar = _permisos(bt, implicadas)
    user = session.get("user")

    if request.method == "POST":
        if not user:
            return redirect(url_for("auth.login"))
        accion = request.form.get("accion", "guardar")

        if accion == "reabrir":
            if not com:
                abort(403)
            db.execute("UPDATE batallas SET batalla_estado = 0 WHERE batalla_id = %s", (str(batalla_id),))
            flash("Acta reabierta para edición.", "info")
            return redirect(url_for("batallas.acta", batalla_id=batalla_id))
        if accion == "eliminar":
            if not com or bt["batalla_estado"] != 0:
                abort(403)
            db.execute("DELETE FROM batallas WHERE batalla_id = %s", (str(batalla_id),))
            flash("Batalla eliminada.", "info")
            return redirect(url_for("public.batallas", campana_id=bt["campana_id"]))
        if not puede_editar:
            abort(403)

        _guardar(bt, implicadas, request.form)

        if accion == "anadir":
            bid = request.form.get("banda_id") or ""
            valida = db.query("SELECT 1 AS ok FROM bandas WHERE banda_id::text = %s AND campana_id = %s",
                              (bid, str(bt["campana_id"])), one=True)
            if valida:
                db.execute("""INSERT INTO batallas_bandas (batalla_id, banda_id) VALUES (%s, %s)
                              ON CONFLICT (batalla_id, banda_id) DO NOTHING""", (str(batalla_id), bid))
        elif accion.startswith("quitar:"):
            bb_id = accion.split(":", 1)[1]
            fila = next((i for i in implicadas if str(i["batalla_banda_id"]) == bb_id), None)
            if fila and (com or str(fila["usuario_id"]) != user["id"]):
                db.execute("DELETE FROM batallas_bandas WHERE batalla_banda_id = %s", (bb_id,))
            elif fila:
                flash("No puedes quitar tu propia banda del acta.", "warning")
        elif accion == "confirmar":
            db.execute("UPDATE batallas SET batalla_estado = 1 WHERE batalla_id = %s", (str(batalla_id),))
            flash("Acta confirmada.", "success")
            return redirect(url_for("public.batallas", campana_id=bt["campana_id"]))
        else:
            flash("Acta guardada.", "success")
        return redirect(url_for("batallas.acta", batalla_id=batalla_id))

    disponibles = db.query(
        """SELECT banda_id, banda_nombre FROM bandas
           WHERE campana_id = %s AND banda_id NOT IN (
               SELECT banda_id FROM batallas_bandas WHERE batalla_id = %s)
           ORDER BY banda_nombre""", (str(bt["campana_id"]), str(batalla_id)))
    return render_template("acta.html", bt=bt, implicadas=implicadas, disponibles=disponibles,
                           com=com, puede_editar=puede_editar, estados=ESTADOS_BATALLA)


def _guardar(bt, implicadas, f):
    """Guarda los datos del acta (sin confirmar) en una sola transacción."""
    try:
        fecha = date.fromisoformat(f.get("fecha") or "")
    except ValueError:
        fecha = bt["batalla_fecha"]
    escenario = (f.get("escenario") or "").strip()[:50] or bt["batalla_escenario"]
    ganadores = []
    for i in implicadas:
        k = str(i["batalla_banda_id"])
        ganador = f.get(f"ganador_{k}") == "1"
        if ganador:
            ganadores.append(i["banda_nombre"])
        bajas = (f.get(f"bajas_{k}") or "").strip()[:1000]
        db.execute(
            """UPDATE batallas_bandas SET batalla_banda_ganancias = %s,
                   batalla_banda_ganador = %s, batalla_banda_info = %s
               WHERE batalla_banda_id = %s""",
            (a_entero(f.get(f"ganancias_{k}"), 0), ganador,
             Json({"bajas": bajas}) if bajas else None, k), commit=False)
    db.execute(
        """UPDATE batallas SET batalla_fecha = %s, batalla_escenario = %s,
               batalla_observaciones = %s, batalla_ganador = %s
           WHERE batalla_id = %s""",
        (fecha, escenario, (f.get("observaciones") or "").strip() or None,
         (", ".join(ganadores))[:200] or None, str(bt["batalla_id"])))
