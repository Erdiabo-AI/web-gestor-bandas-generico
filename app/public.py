"""Parte 1 · web pública: campañas, clasificación, batallas y estadísticas (sin login)."""
from urllib.parse import urlparse

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, abort, session)

from . import db
from .helpers import es_gestor_campana, es_comisario, ESTADOS_BANDA, ESTADOS_BATALLA

bp = Blueprint("public", __name__)


@bp.route("/")
def index():
    campanas = db.query(
        """
        SELECT c.campana_id, c.campana_nombre, c.campana_temporada, c.campana_estado,
               r.regla_descripcion, r.regla_version
        FROM campanas c
        LEFT JOIN reglas r ON r.regla_id = c.regla_id
        ORDER BY c.campana_temporada DESC, c.campana_nombre
        """
    )
    return render_template("index.html", campanas=campanas)


def _campana_o_404(campana_id):
    campana = db.query(
        """
        SELECT c.*, r.regla_descripcion, r.regla_version
        FROM campanas c
        LEFT JOIN reglas r ON r.regla_id = c.regla_id
        WHERE c.campana_id = %s
        """,
        (str(campana_id),), one=True,
    )
    if not campana:
        abort(404)
    return campana


@bp.route("/campana/<uuid:campana_id>")
def campana(campana_id):
    """Clasificación automática por coste (valor) de la banda; las destruidas al final."""
    c = _campana_o_404(campana_id)
    bandas = db.query(
        """
        SELECT b.banda_id, b.banda_nombre, b.banda_tipo, b.banda_valor_banda, b.banda_estado,
               u.usuario_nombre
        FROM bandas b
        LEFT JOIN campanas_usuarios cu ON cu.campana_usuario_id = b.campana_usuario_id
        LEFT JOIN usuarios u ON u.usuario_id = cu.usuario_id
        WHERE b.campana_id = %s
        ORDER BY (b.banda_estado = 1) DESC, b.banda_valor_banda DESC NULLS LAST, b.banda_nombre
        """,
        (str(campana_id),),
    )
    user = session.get("user")
    return render_template("campana.html", c=c, bandas=bandas, estados_banda=ESTADOS_BANDA,
                           es_gestor=es_gestor_campana(c, user),
                           es_com=es_comisario(campana_id, user))


@bp.route("/campana/<uuid:campana_id>/batallas")
def batallas(campana_id):
    c = _campana_o_404(campana_id)
    filtro = request.args.get("banda") or ""
    filas = db.query(
        """
        SELECT bt.*,
               (SELECT string_agg(b.banda_nombre, ', ' ORDER BY b.banda_nombre)
                  FROM batallas_bandas bb JOIN bandas b ON b.banda_id = bb.banda_id
                 WHERE bb.batalla_id = bt.batalla_id) AS oponentes
        FROM batallas bt
        WHERE bt.campana_id = %s
          AND (%s = '' OR EXISTS (SELECT 1 FROM batallas_bandas bb
                                  WHERE bb.batalla_id = bt.batalla_id AND bb.banda_id::text = %s))
        ORDER BY bt.batalla_fecha, bt.batalla_orden
        """,
        (str(campana_id), filtro, filtro),
    )
    bandas = db.query("SELECT banda_id, banda_nombre FROM bandas WHERE campana_id = %s ORDER BY banda_nombre",
                      (str(campana_id),))
    user = session.get("user")
    puede_crear = bool(user) and (es_comisario(campana_id, user) or db.query(
        """SELECT 1 AS ok FROM bandas b
           JOIN campanas_usuarios cu ON cu.campana_usuario_id = b.campana_usuario_id
           WHERE b.campana_id = %s AND cu.usuario_id = %s AND b.banda_estado = 1""",
        (str(campana_id), user["id"]), one=True) is not None)
    return render_template("batallas.html", c=c, batallas=filas, bandas=bandas, filtro=filtro,
                           puede_crear=puede_crear, estados=ESTADOS_BATALLA)


@bp.route("/campana/<uuid:campana_id>/estadisticas")
def estadisticas(campana_id):
    """Por banda: batallas jugadas y victorias (actas confirmadas), ganancias
    totales y bajas (miembros muertos)."""
    c = _campana_o_404(campana_id)
    filas = db.query(
        """
        SELECT b.banda_id, b.banda_nombre, b.banda_tipo, b.banda_estado,
               count(bt.batalla_id) AS jugadas,
               count(bt.batalla_id) FILTER (WHERE bb.batalla_banda_ganador) AS victorias,
               COALESCE(SUM(bb.batalla_banda_ganancias) FILTER (WHERE bt.batalla_id IS NOT NULL), 0) AS ganancias,
               (SELECT count(*) FROM bandas_lin l WHERE l.banda_id = b.banda_id
                  AND l.banda_lin_estado = 3) AS bajas
        FROM bandas b
        LEFT JOIN batallas_bandas bb ON bb.banda_id = b.banda_id
        LEFT JOIN batallas bt ON bt.batalla_id = bb.batalla_id AND bt.batalla_estado = 1
        WHERE b.campana_id = %s
        GROUP BY b.banda_id
        ORDER BY victorias DESC, ganancias DESC, b.banda_nombre
        """,
        (str(campana_id),),
    )
    return render_template("estadisticas.html", c=c, filas=filas, estados_banda=ESTADOS_BANDA)


@bp.route("/aviso-legal")
def aviso_legal():
    return render_template("legal.html", pagina="aviso", titulo="Aviso legal")


@bp.route("/privacidad")
def privacidad():
    return render_template("legal.html", pagina="privacidad", titulo="Política de privacidad")


@bp.route("/contactar", methods=["POST"])
def contactar():
    """Formulario de contacto (popup del footer): crea una notificación al ADM."""
    nombre = (request.form.get("nombre") or "").strip()[:100]
    email = (request.form.get("email") or "").strip()[:150]
    mensaje = (request.form.get("mensaje") or "").strip()[:2000]
    if not mensaje or not email:
        flash("Escribe tu email y el mensaje para contactar.", "warning")
    else:
        user = session.get("user")
        db.execute(
            """INSERT INTO notificaciones
                   (notificacion_tipo, remitente_nombre, remitente_email, usuario_id, mensaje)
               VALUES ('CONTACTO', %s, %s, %s, %s)""",
            (nombre or None, email, (user or {}).get("id"), mensaje),
        )
        flash("Mensaje enviado al administrador. ¡Gracias!", "success")
    ref = request.referrer
    if ref and urlparse(ref).netloc == request.host:
        return redirect(ref)
    return redirect(url_for("public.index"))
