"""Zona de usuario logueado: perfil (Mis campañas, Mis bandas, Mis datos)."""
from flask import (Blueprint, render_template, request, redirect, url_for,
                   session, flash)

from . import db
from .helpers import login_required, ESTADOS_BANDA

bp = Blueprint("dashboard", __name__)


@bp.route("/perfil")
@login_required
def perfil():
    uid = session["user"]["id"]

    # Bloque 1: campañas creadas, gestionadas o en las que participa
    campanas = db.query(
        """
        SELECT c.campana_id, c.campana_nombre, c.campana_temporada, c.campana_estado,
               (c.usuarios_gestor_id = %s OR c.usuarios_gestor_suplente_id = %s) AS es_gestor,
               (SELECT count(*) FROM notificaciones n
                 WHERE n.campana_id = c.campana_id AND NOT n.leida) AS n_mensajes
        FROM campanas c
        WHERE c.usuarios_gestor_id = %s OR c.usuarios_gestor_suplente_id = %s
           OR c.campana_id IN (SELECT campana_id FROM campanas_usuarios WHERE usuario_id = %s)
        ORDER BY c.campana_temporada DESC, c.campana_nombre
        """,
        (uid, uid, uid, uid, uid),
    )

    # Bloque 2: bandas del usuario
    bandas = db.query(
        """
        SELECT b.banda_id, b.banda_nombre, b.banda_tipo, b.banda_estado, c.campana_id,
               c.campana_nombre, c.campana_temporada, r.regla_descripcion
        FROM bandas b
        JOIN campanas_usuarios cu ON cu.campana_usuario_id = b.campana_usuario_id
        JOIN campanas c ON c.campana_id = b.campana_id
        LEFT JOIN reglas r ON r.regla_id = c.regla_id
        WHERE cu.usuario_id = %s
        ORDER BY (b.banda_estado = 1) DESC, c.campana_temporada DESC, b.banda_nombre
        """,
        (uid,),
    )

    # Bloque 3: datos del usuario
    datos = db.query(
        "SELECT usuario_nombre, usuario_email FROM usuarios WHERE usuario_id = %s",
        (uid,), one=True,
    )
    # Contador de notificaciones al administrador sin leer (solo ADM)
    n_notif = 0
    if session["user"]["rol"] == "ADM":
        row = db.query("SELECT count(*) AS c FROM notificaciones WHERE NOT leida AND campana_id IS NULL",
                       one=True)
        n_notif = row["c"] if row else 0
    return render_template("perfil.html", bandas=bandas, campanas=campanas,
                           datos=datos, n_notif=n_notif, estados_banda=ESTADOS_BANDA)


@bp.route("/perfil/editar", methods=["POST"])
@login_required
def perfil_editar():
    uid = session["user"]["id"]
    nombre = (request.form.get("nombre") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    if not (nombre and email):
        flash("Nombre y email son obligatorios.", "warning")
        return redirect(url_for("dashboard.perfil"))
    try:
        db.execute(
            "UPDATE usuarios SET usuario_nombre=%s, usuario_email=%s WHERE usuario_id=%s",
            (nombre, email, uid),
        )
        session["user"]["nombre"] = nombre
        session.modified = True
        flash("Datos actualizados.", "success")
    except Exception:
        flash("No se pudo actualizar (¿email ya en uso?).", "danger")
    return redirect(url_for("dashboard.perfil"))
