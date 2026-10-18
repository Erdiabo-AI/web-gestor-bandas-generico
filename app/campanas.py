"""Gestión de campañas: alta, estado, suplente, modo comisario y mensajes."""
from datetime import date
from urllib.parse import urlparse

from flask import (Blueprint, render_template, request, redirect, url_for,
                   session, flash, abort)

from . import db
from .helpers import (login_required, es_gestor_campana, activar_com,
                      campanas_com, a_entero, ESTADOS_CAMPANA)

bp = Blueprint("campanas", __name__)


def _campana_gestionable(campana_id):
    """Campaña que el usuario puede gestionar (creador, suplente o ADM), o 403."""
    c = db.query("SELECT * FROM campanas WHERE campana_id = %s", (str(campana_id),), one=True)
    if not c:
        abort(404)
    if not es_gestor_campana(c, session.get("user")):
        abort(403)
    return c


@bp.route("/gestion-campanas")
@login_required
def gestion_campanas():
    user = session["user"]
    es_adm = user["rol"] == "ADM"

    # Bloque 1: reglamentos para el desplegable
    reglas = db.query(
        "SELECT regla_id, regla_descripcion, regla_version, regla_anyo FROM reglas "
        "ORDER BY regla_descripcion, regla_anyo DESC")

    # Bloque 2: campañas que gestiona (ADM: todas)
    mis = db.query(
        """SELECT campana_id, campana_nombre, campana_temporada FROM campanas
           WHERE %s OR usuarios_gestor_id = %s OR usuarios_gestor_suplente_id = %s
           ORDER BY campana_temporada DESC, campana_nombre""",
        (es_adm, user["id"], user["id"]))
    sel_id = request.args.get("campana") or (str(mis[0]["campana_id"]) if mis else None)
    sel = None
    inscritos, mensajes = [], []
    if sel_id and any(str(m["campana_id"]) == sel_id for m in mis):
        sel = db.query(
            """SELECT c.*, u.usuario_nombre AS gestor_nombre
               FROM campanas c JOIN usuarios u ON u.usuario_id = c.usuarios_gestor_id
               WHERE c.campana_id = %s""", (sel_id,), one=True)
        inscritos = db.query(
            """SELECT u.usuario_id, u.usuario_nombre FROM campanas_usuarios cu
               JOIN usuarios u ON u.usuario_id = cu.usuario_id
               WHERE cu.campana_id = %s ORDER BY u.usuario_nombre""", (sel_id,))
        mensajes = db.query(
            """SELECT * FROM notificaciones WHERE campana_id = %s
               ORDER BY leida, fecha DESC LIMIT 100""", (sel_id,))

    # Bloque 3 (ADM): tablas globales
    todas, usuarios = [], []
    if es_adm:
        todas = db.query(
            """SELECT c.campana_id, c.campana_nombre, c.campana_temporada, c.campana_estado,
                      r.regla_descripcion, u.usuario_nombre AS gestor_nombre,
                      (SELECT count(*) FROM bandas b WHERE b.campana_id = c.campana_id) AS n_bandas
               FROM campanas c
               LEFT JOIN reglas r ON r.regla_id = c.regla_id
               LEFT JOIN usuarios u ON u.usuario_id = c.usuarios_gestor_id
               ORDER BY c.campana_temporada DESC, c.campana_nombre""")
        usuarios = db.query(
            """SELECT usuario_id, usuario_nombre, usuario_email, usuario_rol, reset_solicitado
               FROM usuarios ORDER BY reset_solicitado DESC NULLS LAST, usuario_nombre""")

    return render_template(
        "gestion_campanas.html", reglas=reglas, mis=mis, sel=sel, inscritos=inscritos,
        mensajes=mensajes, estados=ESTADOS_CAMPANA, todas=todas, usuarios=usuarios,
        com_activo=bool(sel and str(sel["campana_id"]) in campanas_com()),
        anyo_actual=date.today().year,
        es_creador=bool(sel and (es_adm or str(sel["usuarios_gestor_id"]) == user["id"])),
    )


@bp.route("/gestion-campanas/crear", methods=["POST"])
@login_required
def crear():
    f = request.form
    nombre = (f.get("nombre") or "").strip()[:150]
    temporada = (f.get("temporada") or str(date.today().year)).strip()[:15]
    tesoreria = a_entero(f.get("tesoreria_inicial"), 0)
    regla = db.query("SELECT regla_id FROM reglas WHERE regla_id::text = %s",
                     (f.get("regla_id") or "",), one=True)
    if not nombre or not regla:
        flash("Indica el nombre de la campaña y el reglamento.", "warning")
        return redirect(url_for("campanas.gestion_campanas"))
    if tesoreria < 0:
        flash("La tesorería inicial no puede ser negativa.", "warning")
        return redirect(url_for("campanas.gestion_campanas"))
    row = db.execute(
        """INSERT INTO campanas (regla_id, campana_nombre, campana_temporada,
               campana_tesoreria_inicial, usuarios_gestor_id)
           VALUES (%s, %s, %s, %s, %s) RETURNING campana_id""",
        (str(regla["regla_id"]), nombre, temporada, tesoreria, session["user"]["id"]),
        returning=True)
    flash(f"Campaña «{nombre}» creada en estado Inscripción.", "success")
    return redirect(url_for("campanas.gestion_campanas", campana=row["campana_id"]))


@bp.route("/gestion-campanas/<uuid:campana_id>/estado", methods=["POST"])
@login_required
def cambiar_estado(campana_id):
    _campana_gestionable(campana_id)
    estado = request.form.get("estado")
    if estado not in ESTADOS_CAMPANA:
        abort(400)
    db.execute("UPDATE campanas SET campana_estado = %s WHERE campana_id = %s",
               (estado, str(campana_id)))
    flash("Estado de la campaña actualizado.", "success")
    return redirect(url_for("campanas.gestion_campanas", campana=campana_id))


@bp.route("/gestion-campanas/<uuid:campana_id>/suplente", methods=["POST"])
@login_required
def suplente(campana_id):
    c = _campana_gestionable(campana_id)
    user = session["user"]
    if user["rol"] != "ADM" and str(c["usuarios_gestor_id"]) != user["id"]:
        abort(403)   # solo el creador nombra al suplente
    uid = request.form.get("usuario_id") or None
    if uid:
        inscrito = db.query(
            "SELECT 1 AS ok FROM campanas_usuarios WHERE campana_id = %s AND usuario_id::text = %s",
            (str(campana_id), uid), one=True)
        if not inscrito:
            flash("El suplente debe estar inscrito en la campaña.", "warning")
            return redirect(url_for("campanas.gestion_campanas", campana=campana_id))
    db.execute("UPDATE campanas SET usuarios_gestor_suplente_id = %s WHERE campana_id = %s",
               (uid, str(campana_id)))
    flash("Comisario suplente actualizado.", "success")
    return redirect(url_for("campanas.gestion_campanas", campana=campana_id))


@bp.route("/gestion-campanas/<uuid:campana_id>/comisario", methods=["POST"])
@login_required
def comisario(campana_id):
    """«Acceder como comisario»: activa (o desactiva) el modo COM en esta campaña."""
    c = _campana_gestionable(campana_id)
    activar = request.form.get("activar") == "1"
    activar_com(campana_id, activar)
    if activar:
        flash(f"Modo comisario activado en «{c['campana_nombre']}»: puedes gestionar "
              "las bandas y actas de todos los participantes.", "info")
    else:
        flash("Modo comisario desactivado.", "info")
    return redirect(url_for("campanas.gestion_campanas", campana=campana_id))


@bp.route("/gestion-campanas/mensaje/<uuid:nid>", methods=["POST"])
@login_required
def mensaje(nid):
    """Marcar como leído o borrar un mensaje enviado al comisario."""
    n = db.query("SELECT campana_id FROM notificaciones WHERE notificacion_id = %s",
                 (str(nid),), one=True)
    if not n or not n["campana_id"]:
        abort(404)
    _campana_gestionable(n["campana_id"])
    if request.form.get("accion") == "borrar":
        db.execute("DELETE FROM notificaciones WHERE notificacion_id = %s", (str(nid),))
    else:
        db.execute("UPDATE notificaciones SET leida = TRUE WHERE notificacion_id = %s", (str(nid),))
    return redirect(url_for("campanas.gestion_campanas", campana=n["campana_id"]) + "#mensajes")


@bp.route("/campana/<uuid:campana_id>/contactar", methods=["POST"])
def contactar_comisario(campana_id):
    """Contacto público con el comisario de una campaña (Parte 1)."""
    c = db.query("SELECT campana_id FROM campanas WHERE campana_id = %s", (str(campana_id),), one=True)
    if not c:
        abort(404)
    nombre = (request.form.get("nombre") or "").strip()[:100]
    email = (request.form.get("email") or "").strip()[:150]
    texto = (request.form.get("mensaje") or "").strip()[:2000]
    if not texto or not email:
        flash("Escribe tu email y el mensaje para contactar con el comisario.", "warning")
    else:
        db.execute(
            """INSERT INTO notificaciones
                   (notificacion_tipo, remitente_nombre, remitente_email, usuario_id, mensaje, campana_id)
               VALUES ('COMISARIO', %s, %s, %s, %s, %s)""",
            (nombre or None, email, (session.get("user") or {}).get("id"), texto, str(campana_id)))
        flash("Mensaje enviado al comisario de la campaña.", "success")
    ref = request.referrer
    if ref and urlparse(ref).netloc == request.host:
        return redirect(ref)
    return redirect(url_for("public.campana", campana_id=campana_id))
